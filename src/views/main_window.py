import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
import time
from threading import Thread
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime, timedelta
import numpy as np
from ..models.data_logger import DataLogger
from ..models.calculations import calculate_real_outflow
import subprocess
import platform

class MainWindow(tk.Frame):
    def __init__(self, parent: tk.Tk, controller: Any, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.settings = settings
        
        # Configure window size and position
        window_width = self.settings.get('width', 1024)
        window_height = self.settings.get('height', 600)
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.parent.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Configure styling with larger fonts
        self.style = ttk.Style()
        self.style.configure('TLabel', font=('Helvetica', 14))
        self.style.configure('TButton', font=('Helvetica', 14), padding=8)
        self.style.configure('TEntry', font=('Helvetica', 14))
        self.style.configure('TLabelframe', font=('Helvetica', 14, 'bold'))
        
        # Configure grid weights
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        
        # Initialize storage
        self.reading_labels: Dict = {}
        self.status_labels: Dict = {}
        self.variables = {
            'C_tot_ppm': tk.DoubleVar(value=2), #Around 2ppm in the air 
            'C1_ppm': tk.DoubleVar(value=0),
            'C2_ppm': tk.DoubleVar(value=5000)
        }
        
        # Flag to track if instrument scanning has been completed
        self.instruments_scanned = False
        
        # Initialize instrument addresses with None to prevent premature readings
        self.instrument_addresses = {
            'gas1': None,
            'gas2': None
        }
        
        # Configure fonts based on platform settings
        self.default_font = (self.settings['font_family'], self.settings['font_size'])

        # Initialize plot data
        self.times = []
        self.flow1_data = {'sp': [], 'pv': []}
        self.flow2_data = {'sp': [], 'pv': []}
        self.conc_data = {'target': [], 'actual': []}  # Add concentration data
        
        # Setup UI components
        self.setup_gui()
        self.setup_plots()
        
        # Add a welcome message prompting to scan for instruments
        self.update_status("Welcome! Please scan for instruments to get started", "blue")
        
        # Now start updates after setting up
        self.start_updates()
        self.pack(fill=tk.BOTH, expand=True)

        self.is_raspberry = platform.system() == 'Linux'
        if self.is_raspberry:
            self.setup_touch_keyboard()

    def update_status(self, message: str, color: str = "black"):
        """Update status message"""
        if 'Status' not in self.status_labels:
            self.status_labels['Status'] = ttk.Label(self)
            self.status_labels['Status'].grid(row=1, column=0, columnspan=2, pady=5)
        self.status_labels['Status'].config(text=message, foreground=color)

    def setup_gui(self):
        # Create main container with padding
        main_container = ttk.Frame(self, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        
        # Create frames with better styling
        self.concentration_frame = ttk.LabelFrame(
            main_container, 
            text="Concentration Control",
            padding="10"
        )
        self.flow_frame = ttk.LabelFrame(
            main_container, 
            text="Direct Flow Control",
            padding="10"
        )
        
        # Position frames
        self.concentration_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        self.flow_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        self.setup_concentration_panel()
        self.setup_flow_panel()
        
    def setup_concentration_panel(self):
        # Concentration inputs
        row = 0
        for key in ['C_tot_ppm', 'C1_ppm', 'C2_ppm']:
            ttk.Label(self.concentration_frame, text=f"{key}:").grid(
                row=row, column=0, padx=5, pady=5)
            ttk.Entry(self.concentration_frame, 
                     textvariable=self.variables[key]).grid(
                row=row, column=1, padx=5, pady=5)
            row += 1
            
        # Calculate button
        ttk.Button(self.concentration_frame, 
                  text="Calculate Flows",
                  command=self.calculate_flows).grid(
            row=row, column=0, columnspan=2, pady=10)
        
    def setup_flow_panel(self):
        # Flow controls for each instrument
        addresses = [self.instrument_addresses['gas1'], self.instrument_addresses['gas2']]
        names = ['Gas 1', 'Gas 2']
        
        # Add scan button
        scan_button = ttk.Button(
            self.flow_frame, 
            text="Scan for Instruments",
            command=self.scan_instruments
        )
        scan_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Add instrument controls
        for i, (addr, name) in enumerate(zip(addresses, names)):
            group = ttk.LabelFrame(self.flow_frame, text=f"{name} Control (Addr: {addr})")
            group.grid(row=1, column=i, padx=5, pady=5)
            
            self.setup_instrument_controls(group, addr)

    def setup_instrument_controls(self, parent: ttk.Frame, addr: int):
        control_frame = ttk.Frame(parent, padding="5")
        control_frame.pack(fill=tk.X, expand=True)
        
        # Flow setter with better layout
        ttk.Label(control_frame, text="Set Flow:", width=10).grid(row=0, column=0, padx=5, pady=2)
        entry = ttk.Entry(control_frame, width=10)
        entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(control_frame, text="ln/min", width=6).grid(row=0, column=2, padx=2, pady=2)
        
        set_button = ttk.Button(
            control_frame,
            text="Set",
            command=lambda: self.set_flow(addr, entry.get())
        )
        set_button.grid(row=0, column=3, padx=5, pady=2)

        # Reading displays with better styling
        self.reading_labels[addr] = {}
        params = [
            ('Flow', 'ln/min'),
            ('Valve', '%'),
            ('Temperature', '°C')
        ]
        
        for i, (param, unit) in enumerate(params):
            frame = ttk.Frame(control_frame)
            frame.grid(row=i+1, column=0, columnspan=4, sticky='ew', pady=2)
            
            ttk.Label(frame, text=f"{param}:", width=10).pack(side=tk.LEFT, padx=5)
            self.reading_labels[addr][param] = ttk.Label(
                frame, 
                text="---",
                width=10,
                background='white',
                relief='sunken',
                anchor='center'
            )
            self.reading_labels[addr][param].pack(side=tk.LEFT, padx=5)
            ttk.Label(frame, text=unit, width=6).pack(side=tk.LEFT, padx=2)
            
    def calculate_flows(self):
        if not self.controller.is_connected():
            self.update_status("Please connect the instruments", "red")
            return
            
        try:
            # Get values with validation
            values = {}
            for key in ['C_tot_ppm', 'C1_ppm', 'C2_ppm']:
                try:
                    value = self.variables[key].get()
                    if value == "":
                        raise ValueError(f"{key} cannot be empty")
                    values[key] = float(value)
                except (ValueError, tk.TclError) as e:
                    self.update_status(f"Invalid input for {key}", "red")
                    return

            # Calculate flows
            flows = self.controller.calculate_flows(
                values['C_tot_ppm'],
                values['C1_ppm'],
                values['C2_ppm']
            )
            self.update_status(
                f"Calculated: Q1={flows['Q1']:.3f}, Q2={flows['Q2']:.3f} ln/min")
        except ValueError as e:
            self.update_status(f"Error: {str(e)}", "red")
        except Exception as e:
            self.update_status(f"Calculation error: {str(e)}", "red")
            
    def start_updates(self):
        """Start periodic updates of instrument readings"""
        def update():
            try:
                self.update_readings()
                self.update_plots()
            except Exception as e:
                print(f"Update error: {e}")
            finally:
                self.after(1000, update)  # Schedule next update in 1 second
        update()

                    
    def set_flow(self, addr: int, flow_str: str):
        """Set flow for specific instrument"""
        try:
            # Handle both '.' and ',' decimal separators
            flow = float(flow_str.replace(',', '.'))
            
            if not 0 <= flow <= self.controller.max_flow:
                raise ValueError(f"Flow must be between 0 and {self.controller.max_flow} ln/min")
            
            if self.controller.set_flow(addr, flow):
                self.update_status(f"Flow set to {flow:.3f} ln/min")
            else:
                self.update_status("Failed to set flow", "red")
                
        except ValueError as e:
            self.update_status(f"Error: {str(e)}", "red")
    
    def update_readings(self):
        """Update all instrument readings"""
        addresses = [self.instrument_addresses['gas1'], self.instrument_addresses['gas2']]
        
        for addr in addresses:
            # Skip if address is None
            if addr is None:
                continue
                
            try:
                readings = self.controller.get_readings(addr)
                
                # Check if we have any valid readings
                has_valid_readings = False
                for param in ['Flow', 'Valve', 'Temperature']:
                    if readings.get(param) is not None:
                        has_valid_readings = True
                        break
                        
                if not has_valid_readings:
                    print(f"Debug - All readings are None for {addr}")
                    continue
                    
                print(f"Debug - Got readings for {addr}: {readings}")  # Debug print
                
                for param in ['Flow', 'Valve', 'Temperature']:
                    label = self.reading_labels.get(addr, {}).get(param)
                    if label is None:
                        print(f"Debug - Missing label for {addr} {param}")
                        continue
                        
                    value = readings.get(param)
                    if value is not None:
                        label.config(text=f"{value:.3f}")
                    else:
                        label.config(text="Error")
            except Exception as e:
                print(f"Debug - Update error for {addr}: {e}")
                
    def setup_plots(self):
        """Set up the plot area"""
        plot_frame = ttk.LabelFrame(self, text="Flow Monitoring", padding="10")
        plot_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        # Larger figure size for full screen
        self.fig = Figure(figsize=(16, 6))
        self.ax1 = self.fig.add_subplot(131)
        self.ax2 = self.fig.add_subplot(132)
        self.ax3 = self.fig.add_subplot(133)
        
        # Style plots
        for ax in [self.ax1, self.ax2, self.ax3]:
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.set_facecolor('#f8f9fa')
        
        self.fig.set_facecolor('#ffffff')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add toolbar (optional)
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(self.canvas, plot_frame)
        toolbar.update()
        
        # Initial empty plots
        self.ax1.set_title('Flow 1')
        self.ax1.set_ylabel('ln/min')
        self.ax1.text(0.5, 0.5, 'Waiting for data...', 
                     horizontalalignment='center',
                     verticalalignment='center',
                     transform=self.ax1.transAxes)
        
        self.ax2.set_title('Flow 2')
        self.ax2.set_ylabel('ln/min')
        self.ax2.text(0.5, 0.5, 'Waiting for data...', 
                     horizontalalignment='center',
                     verticalalignment='center',
                     transform=self.ax2.transAxes)
        
        self.ax3.set_title('Concentration')
        self.ax3.set_ylabel('ppm')
        self.ax3.text(0.5, 0.5, 'Waiting for data...', 
                     horizontalalignment='center',
                     verticalalignment='center',
                     transform=self.ax3.transAxes)
        
        self.canvas.draw()

    def start_updates(self):
        def update():
            self.update_readings()
            self.update_plots()
            self.after(1000, update)  # Schedule next update
        update()  # Start the update loop

    def update_plots(self):
        """Update the plots with current data"""
        # Only proceed if connected to instruments
        if not self.controller.is_connected():
            # Skip plot updates but don't show error repeatedly
            return
        
        try:
            # Get the addresses from the class variables
            address_1 = self.instrument_addresses['gas1']
            address_2 = self.instrument_addresses['gas2']
            
            # If we don't have valid addresses yet, skip plotting
            if address_1 is None or address_2 is None:
                return
            
            # Get current readings and setpoints with error handling
            try:
                readings_1 = self.controller.get_readings(address_1)
                flow1 = readings_1.get('Flow')
                sp1 = self.controller.get_setpoint(address_1)
                
                # Check if we have valid readings
                if flow1 is None:
                    flow1, sp1 = 0, 0
            except Exception as e:
                print(f"Error getting readings for instrument 1: {e}")
                flow1, sp1 = 0, 0
                
            try:
                readings_2 = self.controller.get_readings(address_2)
                flow2 = readings_2.get('Flow')
                sp2 = self.controller.get_setpoint(address_2)
                
                # Check if we have valid readings
                if flow2 is None:
                    flow2, sp2 = 0, 0
            except Exception as e:
                print(f"Error getting readings for instrument 2: {e}")
                flow2, sp2 = 0, 0
            
            # Calculate actual concentration
            C1 = self.variables['C1_ppm'].get()
            C2 = self.variables['C2_ppm'].get()
            
            # Calculate concentration only if both flows are valid
            if flow1 is not None and flow2 is not None and (flow1 > 0 or flow2 > 0):
                actual_conc = calculate_real_outflow(C1, flow1, C2, flow2)
            else:
                actual_conc = 0
                
            target_conc = self.variables['C_tot_ppm'].get()
            
            # Update data lists
            now = datetime.now()
            self.times.append(now)
            self.flow1_data['pv'].append(flow1 if flow1 is not None else 0)
            self.flow2_data['pv'].append(flow2 if flow2 is not None else 0)
            self.flow1_data['sp'].append(sp1 if sp1 is not None else 0)
            self.flow2_data['sp'].append(sp2 if sp2 is not None else 0)
            self.conc_data['target'].append(target_conc)
            self.conc_data['actual'].append(actual_conc)
            
            # Limit data points to avoid memory issues
            max_points = 300  # 5 minutes at 1 second update rate
            if len(self.times) > max_points:
                self.times = self.times[-max_points:]
                self.flow1_data['pv'] = self.flow1_data['pv'][-max_points:]
                self.flow1_data['sp'] = self.flow1_data['sp'][-max_points:]
                self.flow2_data['pv'] = self.flow2_data['pv'][-max_points:]
                self.flow2_data['sp'] = self.flow2_data['sp'][-max_points:]
                self.conc_data['target'] = self.conc_data['target'][-max_points:]
                self.conc_data['actual'] = self.conc_data['actual'][-max_points:]
            
            # Calculate window for last 60 seconds of data
            window_cutoff = now - timedelta(seconds=60)
            
            # Find index for 60-second window
            window_indices = []
            window_times = []
            for i, t in enumerate(self.times):
                if t >= window_cutoff:
                    window_indices.append(i)
                    window_times.append(t)
            
            # If we don't have any data in our window yet, use all available data
            if not window_indices:
                window_indices = list(range(len(self.times)))
                window_times = self.times.copy()
            
            # Extract data for the window
            window_flow1_pv = [self.flow1_data['pv'][i] for i in window_indices]
            window_flow1_sp = [self.flow1_data['sp'][i] for i in window_indices]
            window_flow2_pv = [self.flow2_data['pv'][i] for i in window_indices]
            window_flow2_sp = [self.flow2_data['sp'][i] for i in window_indices]
            window_conc_target = [self.conc_data['target'][i] for i in window_indices]
            window_conc_actual = [self.conc_data['actual'][i] for i in window_indices]
            
            # Format time for x-axis
            times_formatted = [t.strftime('%H:%M:%S') for t in window_times]
            
            # Use indices for plotting (0 to len(window_data))
            plot_indices = list(range(len(window_indices)))
            
            # Clear and redraw plots
            self.ax1.clear()
            self.ax2.clear()
            self.ax3.clear()
            
            # Plot flow 1
            self.ax1.plot(plot_indices, window_flow1_pv, 'b-', label='Actual')
            self.ax1.plot(plot_indices, window_flow1_sp, 'r--', label='Setpoint')
            self.ax1.set_title(f'Flow 1 (Addr: {address_1})')
            self.ax1.set_ylabel('ln/min')
            self.ax1.legend(loc='best')
            self.ax1.grid(True, linestyle='--', alpha=0.7)

            # Only show a few x-axis labels to avoid crowding
            if len(times_formatted) > 6:
                step = max(1, len(times_formatted) // 6)
                visible_indices = list(range(0, len(times_formatted), step))
                visible_labels = [times_formatted[i] for i in visible_indices]
                self.ax1.set_xticks([plot_indices[i] for i in visible_indices])
                self.ax1.set_xticklabels(visible_labels, rotation=45)
            else:
                self.ax1.set_xticks(plot_indices)
                self.ax1.set_xticklabels(times_formatted, rotation=45)

            # Set x-axis label
            self.ax1.set_xlabel('Last 60 seconds')

            # Plot flow 2
            self.ax2.plot(plot_indices, window_flow2_pv, 'g-', label='Actual')
            self.ax2.plot(plot_indices, window_flow2_sp, 'r--', label='Setpoint')
            self.ax2.set_title(f'Flow 2 (Addr: {address_2})')
            self.ax2.set_ylabel('ln/min')
            self.ax2.legend(loc='best')
            self.ax2.grid(True, linestyle='--', alpha=0.7)
            
            # Only show a few x-axis labels to avoid crowding
            if len(times_formatted) > 6:
                self.ax2.set_xticks([plot_indices[i] for i in visible_indices])
                self.ax2.set_xticklabels(visible_labels, rotation=45)
            else:
                self.ax2.set_xticks(plot_indices)
                self.ax2.set_xticklabels(times_formatted, rotation=45)
                
            # Set x-axis label
            self.ax2.set_xlabel('Last 60 seconds')

            # Plot concentration
            self.ax3.plot(plot_indices, window_conc_actual, 'b-', label='Actual')
            self.ax3.plot(plot_indices, window_conc_target, 'r--', label='Target')
            self.ax3.set_title('Concentration')
            self.ax3.set_ylabel('ppm')
            self.ax3.legend(loc='best')
            self.ax3.grid(True, linestyle='--', alpha=0.7)
            
            # Only show a few x-axis labels to avoid crowding
            if len(times_formatted) > 6:
                self.ax3.set_xticks([plot_indices[i] for i in visible_indices])
                self.ax3.set_xticklabels(visible_labels, rotation=45)
            else:
                self.ax3.set_xticks(plot_indices)
                self.ax3.set_xticklabels(times_formatted, rotation=45)
                
            # Set x-axis label
            self.ax3.set_xlabel('Last 60 seconds')
                
            # Adjust layout and draw
            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating plots: {e}")
            import traceback
            traceback.print_exc()
            # Continue execution to avoid breaking the update loop

    def setup_touch_keyboard(self):
        def show_keyboard(event):
            subprocess.Popen(['onboard'])
            
        def hide_keyboard(event):
            subprocess.Popen(['pkill', 'onboard'])
            
        # Bind to entry focus events
        for entry in self.winfo_children():
            if isinstance(entry, tk.Entry):
                entry.bind('<FocusIn>', show_keyboard)
                entry.bind('<FocusOut>', hide_keyboard)

    def scan_instruments(self):
        """Scan for available instruments and update addresses"""
        if not self.controller.is_connected():
            try:
                # Try to connect to the serial port first
                self.update_status("Attempting to connect and scan for instruments...", "blue")
                
                # Use the controller's scan method
                found_instruments = self.controller.scan_for_instruments(start_addr=1, end_addr=24)
                
                if not found_instruments:
                    self.update_status("No instruments found. Check connections.", "red")
                    return False
                    
                if len(found_instruments) < 2:
                    self.update_status(f"Found only {len(found_instruments)} instrument at address {found_instruments[0]}. Need at least 2.", "orange")
                    # Set the first instrument address at least
                    self.instrument_addresses['gas1'] = found_instruments[0]
                    self.instrument_addresses['gas2'] = None  # Keep second instrument as None
                    return False
                            
                # Update instrument addresses with found devices
                self.instrument_addresses['gas1'] = found_instruments[0]
                self.instrument_addresses['gas2'] = found_instruments[1]
                
                # Update labels in the UI to reflect the new addresses
                self.update_flow_panel_labels()
                
                self.update_status(f"Found instruments at addresses {found_instruments}", "green")
                return True
                
            except Exception as e:
                self.update_status(f"Error scanning for instruments: {str(e)}", "red")
                return False
        else:
            # If already connected, just do a scan
            try:
                found_instruments = self.controller.scan_for_instruments(start_addr=1, end_addr=24)
                
                if not found_instruments:
                    self.update_status("No instruments found. Check connections.", "red")
                    return False
                    
                if len(found_instruments) < 2:
                    self.update_status(f"Found only {len(found_instruments)} instrument at address {found_instruments[0]}. Need at least 2.", "orange")
                    # Set the first instrument address at least
                    self.instrument_addresses['gas1'] = found_instruments[0]
                    self.instrument_addresses['gas2'] = None  # Keep second instrument as None
                    return False
                            
                # Update instrument addresses with found devices
                self.instrument_addresses['gas1'] = found_instruments[0]
                self.instrument_addresses['gas2'] = found_instruments[1]
                
                # Update labels in the UI to reflect the new addresses
                self.update_flow_panel_labels()
                
                self.update_status(f"Found instruments at addresses {found_instruments}", "green")
                return True
            except Exception as e:
                self.update_status(f"Error scanning for instruments: {str(e)}", "red")
                return False
        
    def update_flow_panel_labels(self):
        """Update the labels in the flow panel to reflect current addresses"""
        # Clear existing controls
        for widget in self.flow_frame.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and widget.winfo_children():
                widget.destroy()
        
        # Add instrument controls with updated addresses
        addresses = [self.instrument_addresses['gas1'], self.instrument_addresses['gas2']]
        names = ['Gas 1', 'Gas 2']
        
        for i, (addr, name) in enumerate(zip(addresses, names)):
            group = ttk.LabelFrame(self.flow_frame, text=f"{name} Control (Addr: {addr})")
            group.grid(row=1, column=i, padx=5, pady=5)
            
            self.setup_instrument_controls(group, addr)
        
        # Make sure the scan button remains at the top
        scan_button = ttk.Button(
            self.flow_frame, 
            text="Scan for Instruments",
            command=self.scan_instruments
        )
        scan_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
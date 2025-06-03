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
from tkinter import simpledialog, messagebox

KNOWN_FLOW_RANGES = {
    8: (0.13604, 10, "mln/min"),
    3: (0.012023, 1.5, "ln/min"),
    5: (1.233, 150, "mln/min"),
}

class MainWindow(tk.Frame):
    def __init__(self, parent: tk.Tk, controller: Any, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.settings = settings
        
        # Add this line early in __init__ before calling setup_gui
        self.is_raspberry = platform.system() == 'Linux'
        
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
        
        # Initialize a dict to hold the flow entry widgets for each instrument
        self.flow_entries = {}
        
        # Setup UI components - make sure this is called after is_raspberry is set
        self.setup_gui()
        
        # Only setup plots on non-Raspberry Pi systems (will show on demand on Raspberry Pi)
        if not self.is_raspberry:
            self.setup_plots()
        
        # Add a welcome message prompting to scan for instruments
        self.update_status("Welcome! Please scan for instruments to get started", "blue")
        
        # Now start updates after setting up
        self.start_updates()
        self.pack(fill=tk.BOTH, expand=True)

        # Add a command output window (Text widget) at the bottom, spanning both columns
        # ...existing code...
        self.command_output = tk.Text(
            self.main_container, height=8, width=80, state='disabled',
            bg='#f4f4f4', font=('Consolas', 11)
        )
        self.command_output.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self.main_container.grid_rowconfigure(1, weight=0)

    def update_status(self, message: str, color: str = "black"):
        """Update status message"""
        if 'Status' not in self.status_labels:
            self.status_labels['Status'] = ttk.Label(self)
            self.status_labels['Status'].grid(row=1, column=0, columnspan=2, pady=5)
        self.status_labels['Status'].config(text=message, foreground=color)

    def setup_gui(self):
        # Use a regular frame as the main container
        self.main_container = ttk.Frame(self, padding="10")
        self.main_container.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Create frames with better styling
        self.concentration_frame = ttk.LabelFrame(
            self.main_container, 
            text="Concentration Control",
            padding="10"
        )
        self.flow_frame = ttk.LabelFrame(
            self.main_container, 
            text="Direct Flow Control",
            padding="10"
        )
        
        # Position frames
        self.concentration_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        self.flow_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        self.setup_concentration_panel()
        self.setup_flow_panel()

        # For Raspberry Pi, don't add the plot area to the main window
        # Instead, add a button to show the graphs in a separate window
        if self.is_raspberry:
            show_graph_btn = ttk.Button(
                self.main_container,
                text="Show Graphs",
                command=self.open_graph_window
            )
            show_graph_btn.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        else:
            # For Windows, include the plots in the main window as before
            self.setup_plots()
        
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

        # Max flow input
        ttk.Label(self.concentration_frame, text="Max Flow (ln/min):").grid(
            row=row, column=0, padx=5, pady=5)
        self.variables['max_flow'] = tk.DoubleVar(value=1.5)  # Default max flow
        ttk.Entry(self.concentration_frame, 
                textvariable=self.variables['max_flow']).grid(
            row=row, column=1, padx=5, pady=5)
        row += 1

        # Calculate button
        ttk.Button(self.concentration_frame, 
                text="Calculate Flows",
                command=self.calculate_flows).grid(
            row=row, column=0, columnspan=2, pady=10)
    def setup_flow_panel(self):
        # Flow controls for each instrument remain defined by their address and name
        addresses = [self.instrument_addresses['gas1'], self.instrument_addresses['gas2']]
        names = ['Gas 1', 'Gas 2']
        
        # Add scan button at the top
        scan_button = ttk.Button(
            self.flow_frame, 
            text="Scan for Instruments",
            command=self.scan_instruments
        )
        scan_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Add instrument controls panels for each instrument
        for i, (addr, name) in enumerate(zip(addresses, names)):
            group = ttk.LabelFrame(self.flow_frame, text=f"{name} Control (Addr: {addr})")
            group.grid(row=1, column=i, padx=5, pady=5)
            self.setup_instrument_controls(group, addr)
        
        # Add global Start and Stop buttons below the instrument panels (span both columns)
        start_button = ttk.Button(
            self.flow_frame,
            text="Start",
            command=self.start_all_flows
        )
        start_button.grid(row=2, column=0, padx=5, pady=10, sticky="ew")
        
        stop_button = ttk.Button(
            self.flow_frame,
            text="Stop",
            command=self.stop_all_flows
        )
        stop_button.grid(row=2, column=1, padx=5, pady=10, sticky="ew")

    def setup_instrument_controls(self, parent: ttk.Frame, addr: int):
        control_frame = ttk.Frame(parent, padding="5")
        control_frame.pack(fill=tk.X, expand=True)
        
        # Flow setter label and entry
        ttk.Label(control_frame, text="Set Flow:", width=10).grid(row=0, column=0, padx=5, pady=2)
        entry = ttk.Entry(control_frame, width=10)
        entry.grid(row=0, column=1, padx=5, pady=2)
        unit_label = ttk.Label(control_frame, text="ln/min", width=6)  # Default unit
        unit_label.grid(row=0, column=2, padx=2, pady=2)
        
        # Save the entry and unit label for later use
        self.flow_entries[addr] = entry
        if addr not in self.reading_labels:
            self.reading_labels[addr] = {}
        self.reading_labels[addr]['Unit'] = unit_label

        # Reading displays
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
            self.print_to_command_output("Please connect the instruments")
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
                    msg = f"Invalid input for {key}"
                    self.update_status(msg, "red")
                    self.print_to_command_output(msg)
                    return

            # Get max flow value from the GUI
            try:
                max_flow = float(self.variables['max_flow'].get())
            except Exception:
                max_flow = 1.5  # fallback

            # Calculate flows, now passing max_flow
            # Try to get values from controller first
            Q1, Q2 = self.controller.calculate_flows(
                values['C_tot_ppm'],
                values['C1_ppm'],
                values['C2_ppm'],
                max_flow
            )
            
            # Debug the returned values to understand what we're getting
            self.print_to_command_output(f"Debug - Returned flow values: Q1={Q1}, Q2={Q2}")
            
            # Check if we got actual flow values or addresses
            if not isinstance(Q1, (float, int)) or not isinstance(Q2, (float, int)):
                # If controller returned non-numeric values, calculate flows locally
                self.print_to_command_output("Controller didn't return numeric flows. Calculating locally...")
                from ..models.calculations import calculate_flows_variable
                Q1, Q2 = calculate_flows_variable(
                    values['C_tot_ppm'],
                    values['C1_ppm'], 
                    values['C2_ppm'],
                    max_flow
                )
                self.print_to_command_output(f"Locally calculated flows: Q1={Q1:.3f}, Q2={Q2:.3f}")
            
            # Map to instrument addresses
            addr1 = self.instrument_addresses['gas1']
            addr2 = self.instrument_addresses['gas2']
            
            flows = {addr1: Q1, addr2: Q2}
            
            # Display calculated flows with units
            flow_messages = []
            for addr, flow in flows.items():
                # Get the unit from controller
                unit = self.controller.read_unit(addr)
                
                # Convert flow value based on unit if needed
                converted_flow = flow
                if isinstance(flow, (float, int)):
                    # If unit is ml/min, convert from ln/min
                    if unit == "ml/min":
                        converted_flow = flow * 1000  # Convert ln/min to ml/min
                    flow_messages.append(f"Q{addr}={converted_flow:.3f} {unit}")
                else:
                    flow_messages.append(f"Q{addr}={str(flow)} {unit}")

            result_msg = "Calculated: " + ", ".join(flow_messages)
            self.print_to_command_output(result_msg)
        except ValueError as e:
            self.update_status(f"Error: {str(e)}", "red")
            self.print_to_command_output(f"Error: {str(e)}")
        except Exception as e:
            self.update_status(f"Calculation error: {str(e)}", "red")
            self.print_to_command_output(f"Calculation error: {str(e)}")

    def start_updates(self):
        """Start periodic updates of instrument readings and plots"""
        def update():
            try:
                # Always update readings
                self.update_readings()
                
                # Collect data for plots
                self.collect_plot_data()
                
                # Update main window plots if on Windows
                if not self.is_raspberry:
                    self.update_plots()
                    
                # Update popup graphs if window is open
                if hasattr(self, 'graph_window_open') and self.graph_window_open:
                    self.update_popup_graphs()
                    
            except Exception as e:
                print(f"Update error: {e}")
            finally:
                self.after(1000, update)  # Schedule next update in 1 second
                
        update()  # Start the update loop
    def collect_plot_data(self):
        """Collect data for plotting without actually updating any plots"""
        if not self.controller.is_connected():
            print("Skipping data collection: Controller not connected")
            return
            
        try:
            address_1 = self.instrument_addresses['gas1']
            address_2 = self.instrument_addresses['gas2']

            if address_1 is None or address_2 is None:
                print(f"Skipping data collection: Missing addresses (gas1={address_1}, gas2={address_2})")
                return

            # Get readings for both instruments
            readings_1 = self.controller.get_readings(address_1)
            readings_2 = self.controller.get_readings(address_2)
            
            # Debug readings
            print(f"Readings from addr {address_1}: {readings_1}")
            print(f"Readings from addr {address_2}: {readings_2}")

            # Ensure 'Flow' exists in readings
            if 'Flow' not in readings_1 or 'Flow' not in readings_2:
                print("Missing Flow readings in controller response")
                return
                
            flow1 = readings_1.get('Flow', 0)
            flow2 = readings_2.get('Flow', 0)
            unit1 = readings_1.get('Unit', 'ln/min')
            unit2 = readings_2.get('Unit', 'ln/min')

            # Debug flow values
            print(f"Flow values: flow1={flow1} {unit1}, flow2={flow2} {unit2}")

            # Convert to ln/min if needed
            if unit1 in ("ml/min", "mln/min"):
                flow1 /= 1000
            if unit2 in ("ml/min", "mln/min"):
                flow2 /= 1000

            # Store flow data for plotting
            now = datetime.now()
            self.times.append(now)
            self.flow1_data['pv'].append(flow1)
            self.flow2_data['pv'].append(flow2)

            # Calculate actual concentration
            C1 = self.variables['C1_ppm'].get()
            C2 = self.variables['C2_ppm'].get()
            if flow1 > 0 or flow2 > 0:
                actual_conc = calculate_real_outflow(C1, flow1, C2, flow2)
            else:
                actual_conc = 0

            target_conc = self.variables['C_tot_ppm'].get()
            self.conc_data['target'].append(target_conc)
            self.conc_data['actual'].append(actual_conc)

            # Print debug info
            print(f"Added data point: time={now}, flow1={flow1}, flow2={flow2}, conc={actual_conc}")

            # Verify data arrays have content
            print(f"Data arrays: times={len(self.times)}, flow1={len(self.flow1_data['pv'])}, flow2={len(self.flow2_data['pv'])}")

            # Limit data points
            max_points = 300
            if len(self.times) > max_points:
                self.times = self.times[-max_points:]
                self.flow1_data['pv'] = self.flow1_data['pv'][-max_points:]
                self.flow2_data['pv'] = self.flow2_data['pv'][-max_points:]
                self.conc_data['target'] = self.conc_data['target'][-max_points:]
                self.conc_data['actual'] = self.conc_data['actual'][-max_points:]

        except Exception as e:
            print(f"Error collecting plot data: {e}")
            import traceback
            traceback.print_exc()

    def update_plots(self):
        """Update the main window plots with current data"""
        if not self.controller.is_connected() or not hasattr(self, 'ax1'):
            return  # Skip plot updates if not connected or plots not initialized

        try:
            # --- Plot Flow 1 ---
            self.ax1.clear()
            self.ax1.set_title('Flow 1')
            self.ax1.set_ylabel('ln/min')
            self.ax1.grid(True, linestyle='--', alpha=0.7)
            if self.flow1_data['pv']:
                self.ax1.plot(self.times, self.flow1_data['pv'], 'b-', label='Measured')
                self.ax1.legend(loc='best')
            else:
                self.ax1.text(0.5, 0.5, 'Waiting for data...', horizontalalignment='center',
                            verticalalignment='center', transform=self.ax1.transAxes)

            # --- Plot Flow 2 ---
            self.ax2.clear()
            self.ax2.set_title('Flow 2')
            self.ax2.set_ylabel('ln/min')
            self.ax2.grid(True, linestyle='--', alpha=0.7)
            if self.flow2_data['pv']:
                self.ax2.plot(self.times, self.flow2_data['pv'], 'g-', label='Measured')
                self.ax2.legend(loc='best')
            else:
                self.ax2.text(0.5, 0.5, 'Waiting for data...', horizontalalignment='center',
                            verticalalignment='center', transform=self.ax2.transAxes)

            # --- Plot Concentration ---
            self.ax3.clear()
            self.ax3.plot(self.times, self.conc_data['actual'], 'b-', label='Actual')
            self.ax3.plot(self.times, self.conc_data['target'], 'r--', label='Target')
            self.ax3.set_title('Concentration')
            self.ax3.set_ylabel('ppm')
            self.ax3.legend(loc='best')
            self.ax3.grid(True, linestyle='--', alpha=0.7)
            self.ax3.set_xlabel('Time')

            self.canvas.draw()
        except Exception as e:
            print(f"Error updating main plots: {e}")
        


    def ask_flow_range(self, addr):
        """Demande à l'utilisateur de sélectionner la plage de flow si l'adresse est inconnue."""
        options = [
            ("0.136...10 mln/min", (0.13604, 10, "mln/min")),
            ("0.012...1.5 ln/min", (0.012023, 1.5, "ln/min")),
            ("1.23...150 mln/min", (1.233, 150, "mln/min")),
        ]
        choice = simpledialog.askstring(
            "Sélection du modèle",
            f"Adresse {addr} inconnue. Sélectionnez le modèle (plage de flow) :\n"
            + "\n".join(f"{i+1}. {opt[0]}" for i, opt in enumerate(options))
        )
        if not choice:
            messagebox.showwarning("Avertissement", "Aucune plage sélectionnée, valeur par défaut 1.5 ln/min utilisée.")
            return (0, 1.5, "ln/min")
        try:
            idx = int(choice.strip()) - 1
            return options[idx][1]
        except Exception:
            messagebox.showwarning("Avertissement", "Sélection invalide, valeur par défaut 1.5 ln/min utilisée.")
            return (0, 1.5, "ln/min")

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

                # SET max_flows and units BEFORE updating the panel!
                for addr in found_instruments:
                    if addr in KNOWN_FLOW_RANGES:
                        self.controller.max_flows[addr] = KNOWN_FLOW_RANGES[addr][1]
                        self.controller.units[addr] = KNOWN_FLOW_RANGES[addr][2]
                    else:
                        minf, maxf, unit = self.ask_flow_range(addr)
                        self.controller.max_flows[addr] = maxf
                        self.controller.units[addr] = unit

                # Now update labels in the UI to reflect the new addresses and correct min/max/unit
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
        
    def print_to_command_output(self, message: str):
        """Display a message in the command output window."""
        self.command_output.config(state='normal')
        self.command_output.insert(tk.END, message + '\n')
        self.command_output.see(tk.END)
        self.command_output.config(state='disabled')

    def update_flow_panel_labels(self):
        """Update the labels in the flow panel to reflect current addresses"""
        # Clear existing controls
        for widget in self.flow_frame.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and widget.winfo_children():
                widget.destroy()

        # Clear the flow_entries dictionary to remove references to old widgets
        self.flow_entries.clear()

        # Add instrument controls with updated addresses
        addresses = [self.instrument_addresses['gas1'], self.instrument_addresses['gas2']]
        names = ['Gas 1', 'Gas 2']

        for i, (addr, name) in enumerate(zip(addresses, names)):
            if addr is None:
                continue
            # Get min/max/unit for this instrument
            minf = 0
            maxf = self.controller.max_flows.get(addr, 1.5)
            unit = self.controller.units.get(addr, "ln/min")
            group = ttk.LabelFrame(self.flow_frame, text=f"{name} Control (Addr: {addr})")
            group.grid(row=1, column=i, padx=5, pady=5)

            # Add min/max display at the top of each instrument panel
            minmax_label = ttk.Label(group, text=f"Min: {minf:.3f} {unit}   Max: {maxf:.3f} {unit}", foreground="blue")
            minmax_label.pack(anchor='w', padx=5, pady=(5, 0))

            self.setup_instrument_controls(group, addr)

        # Make sure the scan button remains at the top
        scan_button = ttk.Button(
            self.flow_frame, 
            text="Scan for Instruments",
            command=self.scan_instruments
        )
        scan_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

    def start_all_flows(self):
        """Start all flows based on the setpoints in the GUI"""
        try:
            for addr, entry in self.flow_entries.items():
                try:
                    flow_str = entry.get().replace(',', '.')
                    if flow_str.strip() == "":
                        continue  # Skip empty entries
                    flow_val = float(flow_str)
                    max_flow = self.controller.max_flows.get(addr, 1.5)  # Default to 1.5 if not set

                    # Validate the flow value against the max flow for the instrument
                    if not 0 <= flow_val <= max_flow:
                        raise ValueError(f"Flow must be between 0 and {max_flow} for address {addr}")

                    # Set the flow for the instrument
                    if self.controller.set_flow(addr, flow_val):
                        self.print_to_command_output(f"Flow set for address {addr}: {flow_val} (Max Flow: {max_flow})")
                    else:
                        self.print_to_command_output(f"Failed to set flow for address {addr}")
                except ValueError as e:
                    self.print_to_command_output(f"Invalid flow value for address {addr}: {e}")
                except Exception as e:
                    self.print_to_command_output(f"Error setting flow for address {addr}: {e}")
        except Exception as e:
            self.print_to_command_output(f"Error in start_all_flows: {e}")

            
    def stop_all_flows(self):
        """Set all instrument flows to zero."""
        for addr in self.flow_entries.keys():
            if self.controller.set_flow(addr, 0):
                self.update_status(f"Flow at address {addr} set to 0 ln/min", "green")
            else:
                self.update_status(f"Failed to set flow at address {addr} to 0", "red")

    def create_plot_canvas(self, parent):
        """Create and return a matplotlib FigureCanvasTkAgg in the given parent."""
        fig = Figure(figsize=(16, 6))
        ax1 = fig.add_subplot(131)
        ax2 = fig.add_subplot(132)
        ax3 = fig.add_subplot(133)
        for ax in [ax1, ax2, ax3]:
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.set_facecolor('#f8f9fa')
        fig.set_facecolor('#ffffff')
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        return fig, ax1, ax2, ax3, canvas

    def open_graph_window(self):
        """Open the graph in a new window."""
        graph_win = tk.Toplevel(self)
        graph_win.title("Flow Monitoring Graphs")
        graph_win.geometry("1200x500")
        self.graph_window_open = True
        
        # Store window-specific plot objects
        self.popup_fig, self.popup_ax1, self.popup_ax2, self.popup_ax3, self.popup_canvas = self.create_plot_canvas(graph_win)
        
        # Initial data population
        if self.times:
            self.update_popup_graphs()
        else:
            for ax in [self.popup_ax1, self.popup_ax2, self.popup_ax3]:
                ax.text(0.5, 0.5, 'Waiting for data...', 
                       horizontalalignment='center',
                       verticalalignment='center', 
                       transform=ax.transAxes)
            self.popup_canvas.draw()
        
        # When window is closed, reset the graph_window_open flag
        graph_win.protocol("WM_DELETE_WINDOW", 
                          lambda: [graph_win.destroy(), 
                                   setattr(self, 'graph_window_open', False),
                                   self.cleanup_popup_graphs()])

    def cleanup_popup_graphs(self):
        """Clean up references to popup graph objects"""
        if hasattr(self, 'popup_fig'):
            del self.popup_fig
        if hasattr(self, 'popup_ax1'):
            del self.popup_ax1
        if hasattr(self, 'popup_ax2'):
            del self.popup_ax2
        if hasattr(self, 'popup_ax3'):
            del self.popup_ax3
        if hasattr(self, 'popup_canvas'):
            del self.popup_canvas

    def update_popup_graphs(self):
        """Update only the popup window graphs"""
        if not hasattr(self, 'popup_ax1') or not self.graph_window_open:
            return
            
        # Clear previous plots
        self.popup_ax1.clear()
        self.popup_ax2.clear()
        self.popup_ax3.clear()
        
        # Plot Flow 1
        self.popup_ax1.plot(self.times, self.flow1_data['pv'], 'b-', label='Measured')
        self.popup_ax1.set_title('Flow 1')
        self.popup_ax1.set_ylabel('ln/min')
        self.popup_ax1.legend(loc='best')
        self.popup_ax1.grid(True, linestyle='--', alpha=0.7)

        # Plot Flow 2
        self.popup_ax2.plot(self.times, self.flow2_data['pv'], 'g-', label='Measured')
        self.popup_ax2.set_title('Flow 2')
        self.popup_ax2.set_ylabel('ln/min')
        self.popup_ax2.legend(loc='best')
        self.popup_ax2.grid(True, linestyle='--', alpha=0.7)

        # Plot Concentration
        self.popup_ax3.plot(self.times, self.conc_data['actual'], 'b-', label='Actual')
        self.popup_ax3.plot(self.times, self.conc_data['target'], 'r--', label='Target')
        self.popup_ax3.set_title('Concentration')
        self.popup_ax3.set_ylabel('ppm')
        self.popup_ax3.set_xlabel('Time')
        self.popup_ax3.legend(loc='best')
        self.popup_ax3.grid(True, linestyle='--', alpha=0.7)
        
        # Draw the updated figure
        self.popup_canvas.draw()

    def update_readings(self):
        """Update instrument readings in the UI"""
        if not self.controller.is_connected():
            return
            
        # Get addresses of instruments
        address_1 = self.instrument_addresses.get('gas1')
        address_2 = self.instrument_addresses.get('gas2')
        
        # Skip if no addresses are set
        if address_1 is None and address_2 is None:
            return
            
        # Update readings for each valid address
        for addr in [address_1, address_2]:
            if addr is not None and addr in self.reading_labels:
                try:
                    # Get readings from controller
                    readings = self.controller.get_readings(addr)
                    
                    # Debug readings to command output
                    self.print_to_command_output(f"Debug - Readings for addr {addr}: {readings}")
                    
                    # Update each parameter label
                    for param in ['Flow', 'Valve', 'Temperature']:
                        if param in readings and param in self.reading_labels[addr]:
                            value = readings[param]
                            
                            # Format value based on parameter type
                            if param == 'Flow':
                                formatted = f"{value:.3f}"
                            elif param == 'Valve':
                                formatted = f"{value:.1f}"
                            elif param == 'Temperature':
                                formatted = f"{value:.1f}"
                            else:
                                formatted = str(value)
                                
                            self.reading_labels[addr][param].config(text=formatted)
                    
                    # Update unit label if available
                    if 'Unit' in readings and 'Unit' in self.reading_labels[addr]:
                        self.reading_labels[addr]['Unit'].config(text=readings['Unit'])
                        
                except Exception as e:
                    print(f"Error updating readings for address {addr}: {e}")
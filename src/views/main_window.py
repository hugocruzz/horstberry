import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
from threading import Thread
from datetime import datetime
from ..models.data_logger import DataLogger
from ..models.calculations import calculate_real_outflow
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

KNOWN_FLOW_RANGES = {
    8: (0.13604, 10, "mln/min"),
    3: (0.012023, 1.5, "ln/min"),
    5: (1.233, 150, "mln/min"),
    10: (0.012023, 1.5, "ln/min"),
    20: (0.012023, 1.5, "ln/min"),
}

class MainWindow(tk.Frame):
    def __init__(self, parent: tk.Tk, controller: Any, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.settings = settings
        
        # The application will only run on Windows, so is_raspberry can be set to False
        self.is_raspberry = False
        
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
        
        # Add a command output window (Text widget) at the bottom, spanning all columns
        self.command_output = tk.Text(
            self.main_container, height=8, width=80, state='disabled',
            bg='#f4f4f4', font=('Consolas', 11)
        )
        self.command_output.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        
        # Add a welcome message prompting to scan for instruments
        self.update_status("Welcome! Please scan for instruments to get started", "blue")
        
        # Now start updates after setting up
        self.start_updates()
        self.pack(fill=tk.BOTH, expand=True)

    def update_status(self, message: str, color: str = "black"):
        """Update status message"""
        if 'Status' not in self.status_labels:
            self.status_labels['Status'] = ttk.Label(self)
            self.status_labels['Status'].grid(row=1, column=0, columnspan=2, pady=5)
        self.status_labels['Status'].config(text=message, foreground=color)

    def print_to_command_output(self, message: str):
        """Prints a message to the command output text widget."""
        now = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{now}] {message}\n"
        
        if hasattr(self, 'command_output'):
            self.command_output.config(state='normal')
            self.command_output.insert(tk.END, full_message)
            self.command_output.config(state='disabled')
            self.command_output.see(tk.END) # Scroll to the end
        else:
            print(full_message) # Fallback to console if text widget not ready

    def setup_gui(self):
        # Use a regular frame as the main container
        self.main_container = ttk.Frame(self, padding="10")
        self.main_container.grid(row=0, column=0, sticky="nsew")

        # Configure main frame grid weights
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Configure main container grid weights for proper resizing
        self.main_container.grid_columnconfigure(0, weight=0)  # Left panel (fixed width)
        self.main_container.grid_columnconfigure(1, weight=1)  # Center panel (instruments)
        self.main_container.grid_columnconfigure(2, weight=2)  # Right panel (plots)
        self.main_container.grid_rowconfigure(0, weight=1)     # Main content area
        self.main_container.grid_rowconfigure(1, weight=0)     # Command output (fixed height)

        # --- Left Panel for Connection and Concentration ---
        left_panel = ttk.Frame(self.main_container)
        left_panel.grid(row=0, column=0, padx=10, pady=5, sticky="ns")
        
        self.setup_connection_panel(left_panel)
        self.setup_concentration_panel(left_panel)

        # --- Center Panel for Direct Flow Control ---
        self.flow_frame = ttk.LabelFrame(
            self.main_container, 
            text="Direct Flow Control",
            padding="10"
        )
        self.flow_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        self.setup_flow_panel() # This now just sets up the scrollable container

        # --- Right Panel for Plots ---
        plot_frame = ttk.Frame(self.main_container)
        plot_frame.grid(row=0, column=2, padx=10, pady=5, sticky="nsew")
        
        # Create plots in the right panel
        if not self.is_raspberry:
            self.fig, self.ax1, self.ax2, self.ax3, self.canvas = self.create_plot_canvas(plot_frame)

    def setup_connection_panel(self, parent):
        """Sets up the panel for COM port selection and scanning. This is now static."""
        connection_frame = ttk.LabelFrame(parent, text="Connection")
        connection_frame.pack(padx=0, pady=5, fill="x", side=tk.TOP)

        com_port_label = ttk.Label(connection_frame, text="COM Port:")
        com_port_label.pack(side=tk.LEFT, padx=(10, 5), pady=5)

        self.com_port_var = tk.StringVar()
        ports = [f"COM{i}" for i in range(1, 15)]
        self.com_port_dropdown = ttk.Combobox(
            connection_frame,
            textvariable=self.com_port_var,
            values=ports,
            state="readonly",
            width=10
        )
        self.com_port_dropdown.pack(side=tk.LEFT, padx=5, pady=5)
        self.com_port_dropdown.bind("<<ComboboxSelected>>", self.on_com_port_selected)

        # Set default port from settings or controller, defaulting to COM13
        default_port = self.controller.get_port() or self.settings.get('port', 'COM13')
        self.com_port_var.set(default_port)
        # Configure controller with the default port if not already set
        if not self.controller.get_port():
            self.controller.set_port(default_port)
            self.print_to_command_output(f"COM Port set to {default_port}")

        self.scan_button = ttk.Button(
            connection_frame, text="Scan Instruments", command=self.scan_instruments
        )
        self.scan_button.pack(side=tk.RIGHT, padx=10, pady=5)

    def setup_concentration_panel(self, parent):
        """Sets up the concentration control panel. This is now static."""
        self.concentration_frame = ttk.LabelFrame(
            parent, 
            text="Concentration Control",
            padding="10"
        )
        self.concentration_frame.pack(padx=0, pady=5, fill="x", side=tk.TOP)
        
        row = 0
        
        # Gas 1 (low concentration) instrument selection
        ttk.Label(self.concentration_frame, text="Gas 1 Address:").grid(
            row=row, column=0, padx=5, pady=5, sticky="w")
        self.gas1_address_var = tk.StringVar(value="Not assigned")
        self.gas1_dropdown = ttk.Combobox(
            self.concentration_frame,
            textvariable=self.gas1_address_var,
            values=["Not assigned"],
            state="readonly",
            width=12
        )
        self.gas1_dropdown.grid(row=row, column=1, padx=5, pady=5, sticky="e")
        self.gas1_dropdown.bind("<<ComboboxSelected>>", self.on_gas1_selected)
        row += 1
        
        # Gas 2 (high concentration) instrument selection
        ttk.Label(self.concentration_frame, text="Gas 2 Address:").grid(
            row=row, column=0, padx=5, pady=5, sticky="w")
        self.gas2_address_var = tk.StringVar(value="Not assigned")
        self.gas2_dropdown = ttk.Combobox(
            self.concentration_frame,
            textvariable=self.gas2_address_var,
            values=["Not assigned"],
            state="readonly",
            width=12
        )
        self.gas2_dropdown.grid(row=row, column=1, padx=5, pady=5, sticky="e")
        self.gas2_dropdown.bind("<<ComboboxSelected>>", self.on_gas2_selected)
        row += 1
        
        # Separator
        ttk.Separator(self.concentration_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        
        for key in ['C_tot_ppm', 'C1_ppm', 'C2_ppm']:
            ttk.Label(self.concentration_frame, text=f"{key}:").grid(
                row=row, column=0, padx=5, pady=5, sticky="w")
            ttk.Entry(self.concentration_frame, 
                    textvariable=self.variables[key], width=10).grid(
                row=row, column=1, padx=5, pady=5, sticky="e")
            row += 1

        ttk.Label(self.concentration_frame, text="Max Flow (ln/min):").grid(
            row=row, column=0, padx=5, pady=5, sticky="w")
        self.variables['max_flow'] = tk.DoubleVar(value=1.5)
        ttk.Entry(self.concentration_frame, 
                textvariable=self.variables['max_flow'], width=10).grid(
            row=row, column=1, padx=5, pady=5, sticky="e")
        row += 1

        ttk.Button(self.concentration_frame, 
                text="Calculate Flows",
                command=self.calculate_flows).grid(
            row=row, column=0, columnspan=2, pady=10)

    def on_gas1_selected(self, event):
        """Handle Gas 1 instrument selection."""
        selected = self.gas1_address_var.get()
        if selected != "Not assigned":
            try:
                addr = int(selected)
                self.instrument_addresses['gas1'] = addr
                self.print_to_command_output(f"Gas 1 (low conc.) assigned to address {addr}")
                self.update_status(f"Gas 1 assigned to address {addr}", "green")
            except ValueError:
                pass
    
    def on_gas2_selected(self, event):
        """Handle Gas 2 instrument selection."""
        selected = self.gas2_address_var.get()
        if selected != "Not assigned":
            try:
                addr = int(selected)
                self.instrument_addresses['gas2'] = addr
                self.print_to_command_output(f"Gas 2 (high conc.) assigned to address {addr}")
                self.update_status(f"Gas 2 assigned to address {addr}", "green")
            except ValueError:
                pass

    def on_com_port_selected(self, event):
        """Handle COM port selection from the dropdown."""
        selected_port = self.com_port_var.get()
        self.controller.set_port(selected_port)
        self.print_to_command_output(f"COM Port set to {selected_port}")
        self.update_status(f"Port set to {selected_port}. Ready to scan.", "blue")

    def scan_instruments(self):
        """Scan for connected instruments and update the UI."""
        self.print_to_command_output("Scanning for instruments...")
        self.scan_button.config(state="disabled")
        
        def scan_thread():
            try:
                found_instruments = self.controller.scan_for_instruments()
                self.after(0, lambda: self.print_to_command_output(f"Found instruments at addresses: {found_instruments}"))
                self.after(0, self.update_ui_with_scan_results, found_instruments)
            except Exception as e:
                self.after(0, lambda: self.print_to_command_output(f"Scan failed: {e}"))
            finally:
                self.after(0, lambda: self.scan_button.config(state="normal"))

        Thread(target=scan_thread, daemon=True).start()

    def update_ui_with_scan_results(self, found_instruments):
        """Update UI after scanning is complete. ONLY updates the scrollable frame."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.controller.is_connected() or not found_instruments:
            self.print_to_command_output("No instruments found or connection failed.")
            self.update_status("Scan complete. No instruments found.", "orange")
            ttk.Label(self.scrollable_frame, text="No instruments found.").pack(pady=20)
            return

        instruments_metadata = self.controller.get_instrument_metadata()
        self.print_to_command_output(f"Connected to {len(instruments_metadata)} instruments at addresses: {list(instruments_metadata.keys())}")
        
        # Update Gas1 and Gas2 dropdowns with available addresses
        address_list = [str(addr) for addr in sorted(instruments_metadata.keys())]
        self.gas1_dropdown['values'] = address_list
        self.gas2_dropdown['values'] = address_list
        
        # Auto-assign first two instruments if available
        if len(address_list) >= 2:
            self.gas1_address_var.set(address_list[0])
            self.gas2_address_var.set(address_list[1])
            self.instrument_addresses['gas1'] = int(address_list[0])
            self.instrument_addresses['gas2'] = int(address_list[1])
            self.print_to_command_output(f"Auto-assigned: Gas1={address_list[0]}, Gas2={address_list[1]}")
        elif len(address_list) == 1:
            self.gas1_address_var.set(address_list[0])
            self.instrument_addresses['gas1'] = int(address_list[0])
            self.print_to_command_output(f"Auto-assigned: Gas1={address_list[0]}")
        
        for addr, metadata in instruments_metadata.items():
            self.setup_instrument_controls(self.scrollable_frame, addr, metadata)
            
        self.update_status(f"Scan complete. Found {len(instruments_metadata)} instruments.", "green")
        self.instruments_scanned = True

    def start_all_flows(self):
        """Start flow on all connected instruments."""
        if not self.controller.is_connected():
            self.update_status("Please connect and scan for instruments first.", "orange")
            return
        self.print_to_command_output("Starting all flows...")
        self.controller.start_all()

    def stop_all_flows(self):
        """Stop flow on all connected instruments."""
        if not self.controller.is_connected():
            self.update_status("Please connect and scan for instruments first.", "orange")
            return
        self.print_to_command_output("Stopping all flows...")
        self.controller.stop_all()

    def setup_flow_panel(self):
        """Sets up the panel that contains the scrollable list of instruments."""
        canvas = tk.Canvas(self.flow_frame, borderwidth=0)
        self.scrollable_frame = ttk.Frame(canvas)
        scrollbar = ttk.Scrollbar(self.flow_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            # When canvas is resized, update the width of the scrollable frame
            canvas.itemconfig(canvas_window, width=event.width)

        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

    def setup_instrument_controls(self, parent: ttk.Frame, addr: int, metadata: Dict[str, Any] = None):
        """Setup controls for a single instrument with metadata display."""
        if metadata is None:
            metadata = self.controller.get_instrument_metadata(addr)
        
        # Create a labeled frame for this instrument
        instrument_frame = ttk.LabelFrame(
            parent, 
            text=f"Instrument Address {addr}",
            padding="10"
        )
        instrument_frame.pack(fill=tk.X, expand=True, pady=5)
        
        control_frame = ttk.Frame(instrument_frame)
        control_frame.pack(fill=tk.X, expand=True)
        
        # Display min/max flow range
        min_flow = metadata.get('min_flow', 0.0)
        max_flow = metadata.get('max_flow', 0.0)
        unit = metadata.get('unit', 'ln/min')
        
        range_label = ttk.Label(
            control_frame, 
            text=f"Range: {min_flow:.4f} - {max_flow:.2f} {unit}",
            font=('Helvetica', 11, 'italic'),
            foreground='blue'
        )
        range_label.grid(row=0, column=0, columnspan=5, padx=5, pady=(0, 5), sticky='w')
        
        # Flow setter label and entry
        ttk.Label(control_frame, text="Set Flow:", width=10).grid(row=1, column=0, padx=5, pady=2)
        entry = ttk.Entry(control_frame, width=10)
        entry.grid(row=1, column=1, padx=5, pady=2)
        unit_label = ttk.Label(control_frame, text=unit, width=8)
        unit_label.grid(row=1, column=2, padx=2, pady=2)
        
        # Save the entry and unit label for later use
        self.flow_entries[addr] = entry
        if addr not in self.reading_labels:
            self.reading_labels[addr] = {}
        self.reading_labels[addr]['Unit'] = unit_label

        # Add a "Set" button next to the entry
        set_button = ttk.Button(
            control_frame,
            text="Set",
            command=lambda a=addr: self.set_manual_flow(a)
        )
        set_button.grid(row=1, column=4, padx=5, pady=2)

        # Reading displays
        params = [
            ('Flow', unit),
            ('Valve', '%'),
            ('Temperature', '°C')
        ]
        
        for i, (param, param_unit) in enumerate(params):
            frame = ttk.Frame(control_frame)
            frame.grid(row=i+2, column=0, columnspan=5, sticky='ew', pady=2)
            
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
            ttk.Label(frame, text=param_unit, width=8).pack(side=tk.LEFT, padx=2)

    def set_manual_flow(self, address: int):
        """Set the flow for an instrument from its manual entry field."""
        try:
            flow_str = self.flow_entries[address].get()
            flow = float(flow_str)
            self.controller.set_flow(address, flow)
            self.print_to_command_output(f"Manually set flow for address {address} to {flow:.3f}")
        except ValueError:
            self.print_to_command_output(f"Invalid flow value entered for address {address}: '{flow_str}'")
        except Exception as e:
            self.print_to_command_output(f"Error setting flow for address {address}: {e}")

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
            addr1 = self.instrument_addresses.get('gas1')
            addr2 = self.instrument_addresses.get('gas2')
            
            # Check if roles have been assigned
            if addr1 is None or addr2 is None:
                self.update_status("Please assign instrument roles first (Gas1 and Gas2).", "orange")
                self.print_to_command_output("Please assign instrument roles using 'Assign Roles' button.")
                return
            
            flows = {addr1: Q1, addr2: Q2}
            
            # Pre-fill the flow entry fields with calculated values
            for addr, flow in flows.items():
                if addr in self.flow_entries:
                    # Get the unit from controller
                    unit = self.controller.read_unit(addr)
                    
                    # Convert flow value based on unit if needed
                    converted_flow = flow
                    if isinstance(flow, (float, int)):
                        # If unit is ml/min, convert from ln/min
                        if unit == "ml/min":
                            converted_flow = flow * 1000  # Convert ln/min to ml/min
                        
                        # Pre-fill the entry field
                        self.flow_entries[addr].delete(0, tk.END)
                        self.flow_entries[addr].insert(0, f"{converted_flow:.3f}")
            
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
            self.update_status("Flows calculated and pre-filled. Click 'Set' to apply.", "green")
        except ValueError as e:
            self.update_status(f"Error: {str(e)}", "red")
            self.print_to_command_output(f"Error: {str(e)}")
        except Exception as e:
            self.update_status(f"Calculation error: {str(e)}", "red")
            self.print_to_command_output(f"Calculation error: {str(e)}")

    def start_updates(self):
        """Start periodic updates of instrument readings and plots"""
        self.update_counter = 0  # Add a counter for controlling plot update frequency
        
        def update():
            try:
                self.update_counter += 1
                
                # Always update readings (every second)
                self.update_readings()
                
                # Collect data for plots (every second)
                self.collect_plot_data()
                
                # Update plots less frequently to improve performance (every 2 seconds)
                if not self.is_raspberry and self.update_counter % 2 == 0:
                    self.update_plots()
                    
                # Update popup graphs if window is open (every 2 seconds)
                if hasattr(self, 'graph_window_open') and self.graph_window_open and self.update_counter % 2 == 0:
                    self.update_popup_graphs()
                    
            except Exception as e:
                print(f"Update error: {e}")
            finally:
                self.after(1000, update)  # Schedule next update in 1 second
                
        update()  # Start the update loop
    def collect_plot_data(self):
        """Collect data for plotting without actually updating any plots"""
        if not self.controller.is_connected():
            return
            
        try:
            address_1 = self.instrument_addresses.get('gas1')
            address_2 = self.instrument_addresses.get('gas2')

            if address_1 is None or address_2 is None:
                # Skip data collection if roles haven't been assigned yet
                return

            # Get readings for both instruments
            readings_1 = self.controller.get_readings(address_1)
            readings_2 = self.controller.get_readings(address_2)
            
            # Remove debug readings
            # print(f"Readings from addr {address_1}: {readings_1}")
            # print(f"Readings from addr {address_2}: {readings_2}")

            # Ensure 'Flow' exists in readings
            if 'Flow' not in readings_1 or 'Flow' not in readings_2:
                # Keep this message as it's important
                print("Missing Flow readings in controller response")
                return
                
            flow1 = readings_1.get('Flow', 0)
            flow2 = readings_2.get('Flow', 0)
            unit1 = readings_1.get('Unit', 'ln/min')
            unit2 = readings_2.get('Unit', 'ln/min')

            # Remove debug flow values
            # print(f"Flow values: flow1={flow1} {unit1}, flow2={flow2} {unit2}")

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

            # Remove print debug info
            # print(f"Added data point: time={now}, flow1={flow1}, flow2={flow2}, conc={actual_conc}")
            # print(f"Data arrays: times={len(self.times)}, flow1={len(self.flow1_data['pv'])}, flow2={len(self.flow2_data['pv'])}")

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

    def create_plot_canvas(self, parent):
        """Create a canvas with three subplots for flow and concentration monitoring."""
        fig = Figure(figsize=(12, 5), dpi=100)
        fig.patch.set_facecolor('#f0f0f0')
        
        # Create three subplots
        ax1 = fig.add_subplot(131)
        ax2 = fig.add_subplot(132)
        ax3 = fig.add_subplot(133)
        
        # Style the plots
        for ax in [ax1, ax2, ax3]:
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.tick_params(axis='x', rotation=45)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        fig.tight_layout(pad=3.0)
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        return fig, ax1, ax2, ax3, canvas

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

            # Use draw_idle() instead of draw() for better performance
            # draw_idle() defers the actual drawing until the GUI is idle
            self.canvas.draw_idle()
        except Exception as e:
            print(f"Error updating main plots: {e}")
        
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
        
        # Use draw_idle() for better performance
        self.popup_canvas.draw_idle()

    def update_readings(self):
        """Update instrument readings in the UI"""
        if not self.controller.is_connected():
            return
            
        # Update readings for all connected instruments
        for addr in self.controller.instruments.keys():
            if addr in self.reading_labels:
                try:
                    # Get readings from controller
                    readings = self.controller.get_readings(addr)
                    
                    # Update each parameter label
                    for param in ['Flow', 'Valve', 'Temperature']:
                        if param in readings and param in self.reading_labels[addr]:
                            value = readings[param]
                            
                            # Format value based on parameter type
                            if param == 'Flow':
                                formatted = f"{value:.3f}" if value is not None else "---"
                            elif param == 'Valve':
                                formatted = f"{value:.1f}" if value is not None else "---"
                            elif param == 'Temperature':
                                formatted = f"{value:.1f}" if value is not None else "---"
                            else:
                                formatted = str(value) if value is not None else "---"
                                
                            self.reading_labels[addr][param].config(text=formatted)
                    
                    # Update unit label if available
                    if 'Unit' in readings and 'Unit' in self.reading_labels[addr]:
                        self.reading_labels[addr]['Unit'].config(text=readings['Unit'])
                        
                except Exception as e:
                    print(f"Error updating readings for address {addr}: {e}")
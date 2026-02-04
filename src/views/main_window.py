import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
from threading import Thread
from datetime import datetime
from ..models.data_logger import DataLogger
from ..models.calculations import calculate_real_outflow
from ..models.uncertainty import (
    propagate_concentration_uncertainty, 
    calculate_flow_uncertainty,
    convert_flow_to_mln_min,
    format_uncertainty_string
)
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from .calibration_window import CalibrationWindow

KNOWN_FLOW_RANGES = {
    8: (0.13604, 10, "mln/min"),
    3: (0.012023, 1.5, "ln/min"),
    5: (1.233, 150, "mln/min"),
    10: (0.000856, 2.5, "ln/min"),  # Helium: 0.856-2500 mL/min = 0.000856-2.5 L/min
    20: (0.012023, 1.5, "ln/min"),
}

# MFC Uncertainty specifications (based on ±0.5%Rd + ±0.1%FS)
MFC_UNCERTAINTIES = {
    8: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 10.0, 'unit': 'mln/min'},      # Low flow: 10 mL/min max
    3: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 1500.0, 'unit': 'mln/min'},    # High flow: 1500 mL/min max
    5: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 150.0, 'unit': 'mln/min'},     # Medium flow: 150 mL/min max
    10: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 2500.0, 'unit': 'mln/min'},   # Helium: 2500 mL/min max
    20: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 1500.0, 'unit': 'mln/min'},   # Base gas (air): 1500 mL/min max
}

# Instrument naming and display order configuration
INSTRUMENT_NAMES = {
    20: "Base gas (air)",
    3: "High flow",
    5: "Medium flow",
    8: "Low flow",
    10: "Helium"
}

# Display order from top to bottom
INSTRUMENT_DISPLAY_ORDER = [20, 3, 5, 8, 10]

# Safety warning shown when stopping one or more MFCs or setting flow to 0.
STOP_MFCS_WARNING_MESSAGE = (
    "Are you sure you want to stop the MFCs ? "
    "Water from the tank may go back into the tube and damage the MFCs"
)

class MainWindow(tk.Frame):
    def __init__(self, parent: tk.Tk, controller: Any, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.settings = settings
        
        # The application will only run on Windows, so is_raspberry can be set to False
        self.is_raspberry = False
        
        # Calibration mode tracking
        self.in_calibration_mode = False
        self.calibration_status_var = tk.StringVar(value="")
        
        # Initialize current_gas2_address for automatic mode
        self.current_gas2_address = None
        
        # Configure window size and position
        window_width = self.settings.get('width', 1024)
        window_height = self.settings.get('height', 600)
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.parent.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Modern color scheme
        self.colors = {
            'primary': '#2C3E50',      # Dark blue-gray
            'secondary': '#3498DB',    # Bright blue
            'accent': '#E74C3C',       # Red accent
            'success': '#27AE60',      # Green
            'warning': '#F39C12',      # Orange
            'background': '#ECF0F1',   # Light gray
            'card': '#FFFFFF',         # White
            'text': '#2C3E50',         # Dark text
            'border': '#BDC3C7',       # Light border
            'hover': '#D5DBDB'         # Hover state
        }
        
        # Configure modern styling with better fonts and spacing
        self.style = ttk.Style()
        self.style.theme_use('clam')  # More modern base theme
        
        # Main background
        self.configure(bg=self.colors['background'])
        
        # Labels - modern sans-serif font
        self.style.configure('TLabel', 
                           font=('Segoe UI', 11),
                           background=self.colors['background'],
                           foreground=self.colors['text'])
        
        # Buttons - modern flat design with rounded appearance
        self.style.configure('TButton', 
                           font=('Segoe UI', 11, 'bold'),
                           padding=(12, 8),
                           borderwidth=0,
                           focuscolor='none',
                           background=self.colors['secondary'])
        self.style.map('TButton',
                      background=[('active', self.colors['primary']),
                                ('pressed', '#2980B9')])
        
        # Primary action button style
        self.style.configure('Primary.TButton',
                           font=('Segoe UI', 11, 'bold'),
                           padding=(15, 10),
                           background=self.colors['secondary'])
        
        # Success button style (for start/apply actions)
        self.style.configure('Success.TButton',
                           font=('Segoe UI', 11, 'bold'),
                           padding=(12, 8),
                           background=self.colors['success'])
        
        # Warning button style (for stop actions)
        self.style.configure('Warning.TButton',
                           font=('Segoe UI', 11, 'bold'),
                           padding=(12, 8),
                           background=self.colors['accent'])
        
        # Entry fields - clean modern look
        self.style.configure('TEntry', 
                           font=('Segoe UI', 11),
                           fieldbackground=self.colors['card'],
                           borderwidth=2,
                           relief='flat')
        
        # LabelFrame - modern card-like appearance
        self.style.configure('TLabelframe', 
                           font=('Segoe UI', 12, 'bold'),
                           background=self.colors['background'],
                           foreground=self.colors['primary'],
                           borderwidth=2,
                           relief='groove')
        self.style.configure('TLabelframe.Label',
                           font=('Segoe UI', 12, 'bold'),
                           background=self.colors['background'],
                           foreground=self.colors['primary'])
        
        # Card-style frame for instruments
        self.style.configure('Card.TFrame',
                           background=self.colors['card'],
                           relief='raised',
                           borderwidth=1)
        
        # Regular frame style (white background for scrollable areas)
        self.style.configure('TFrame',
                           background=self.colors['card'])
        
        # Combobox styling
        self.style.configure('TCombobox',
                           font=('Segoe UI', 11),
                           fieldbackground=self.colors['card'],
                           background=self.colors['card'],
                           borderwidth=2)
        
        # Separator
        self.style.configure('TSeparator',
                           background=self.colors['border'])
        
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
        
        # Initialize instrument addresses
        # Gas1 is always Base gas (air) at address 20
        # Gas2 is the variable gas, assigned after scanning
        self.instrument_addresses = {
            'gas1': 20,  # Base gas (air) - fixed
            'gas2': None  # Variable gas - assigned during scan
        }
        
        # Track the actual address being used for gas2 (for plotting when in auto mode)
        self.current_gas2_address = None
        
        # Configure fonts based on platform settings
        self.default_font = (self.settings['font_family'], self.settings['font_size'])

        # Initialize plot data
        self.times = []
        self.flow1_data = {'sp': [], 'pv': []}
        self.flow2_data = {'sp': [], 'pv': []}
        self.conc_data = {'target': [], 'actual': []}  # Add concentration data
        self.uncertainty_data = []  # Store uncertainty values for plotting
        
        # Uncertainty tracking
        self.current_uncertainty = {
            'u_C': 0.0,
            'u_F1': 0.0,
            'u_F2': 0.0,
            'C_expected': 0.0
        }
        
        # Initialize a dict to hold the flow entry widgets for each instrument
        self.flow_entries = {}
        
        # Setup UI components - make sure this is called after is_raspberry is set
        self.setup_gui()
        
        # Add a modern command output window with enhanced styling
        output_frame = ttk.Frame(self.main_container, style='Card.TFrame')
        output_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 10))
        output_frame.grid_columnconfigure(0, weight=1)
        
        # Add a header for the command output
        output_header = ttk.Label(
            output_frame, 
            text="📋 System Log",
            font=('Segoe UI', 11, 'bold'),
            foreground=self.colors['primary'],
            background=self.colors['card']
        )
        output_header.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))
        
        self.command_output = tk.Text(
            output_frame, 
            height=8, 
            width=80, 
            state='disabled',
            bg='#FAFAFA',  # Very light gray background
            fg=self.colors['text'],
            font=('Consolas', 10),
            relief='flat',
            borderwidth=0,
            padx=10,
            pady=8,
            wrap='word'
        )
        self.command_output.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        # Configure text tags for colored output
        self.command_output.tag_config('info', foreground='#3498DB')      # Blue
        self.command_output.tag_config('success', foreground='#27AE60')   # Green
        self.command_output.tag_config('warning', foreground='#F39C12')   # Orange
        self.command_output.tag_config('error', foreground='#E74C3C')     # Red
        self.command_output.tag_config('timestamp', foreground='#7F8C8D') # Gray
        
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

    def print_to_command_output(self, message: str, msg_type: str = 'info'):
        """Prints a message to the command output text widget with color coding.
        
        Args:
            message: The message to display
            msg_type: Type of message ('info', 'success', 'warning', 'error')
        """
        now = datetime.now().strftime("%H:%M:%S")
        
        # Choose icon based on message type
        icons = {
            'info': 'ℹ️',
            'success': '✓',
            'warning': '⚠️',
            'error': '✗'
        }
        icon = icons.get(msg_type, 'ℹ️')
        
        if hasattr(self, 'command_output'):
            self.command_output.config(state='normal')
            
            # Insert timestamp with gray color
            self.command_output.insert(tk.END, f"[{now}] ", 'timestamp')
            
            # Insert icon and message with appropriate color
            self.command_output.insert(tk.END, f"{icon} {message}\n", msg_type)
            
            self.command_output.config(state='disabled')
            self.command_output.see(tk.END) # Scroll to the end
        else:
            print(f"[{now}] {icon} {message}") # Fallback to console if text widget not ready

    def setup_gui(self):
        # Use a modern frame as the main container with background color
        self.main_container = ttk.Frame(self, padding="15")
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.configure(style='TFrame')

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
        left_panel = ttk.Frame(self.main_container, style='Card.TFrame', padding="10")
        left_panel.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ns")
        
        self.setup_connection_panel(left_panel)
        self.setup_concentration_panel(left_panel)

        # --- Center Panel for Direct Flow Control ---
        center_container = ttk.Frame(self.main_container)
        center_container.grid(row=0, column=1, padx=10, pady=0, sticky="nsew")
        center_container.grid_rowconfigure(1, weight=1)
        center_container.grid_columnconfigure(0, weight=1)
        
        # Header frame for title and Stop All button
        header_frame = ttk.Frame(center_container)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title and calibration status
        title_frame = ttk.Frame(header_frame)
        title_frame.grid(row=0, column=0, sticky="w", padx=15)
        
        ttk.Label(
            title_frame,
            text="🔧 Direct Flow Control",
            font=('Segoe UI', 12, 'bold'),
            foreground=self.colors['primary']
        ).pack(side=tk.LEFT)
        
        # Calibration mode indicator
        self.calibration_indicator = ttk.Label(
            title_frame,
            textvariable=self.calibration_status_var,
            font=('Segoe UI', 10, 'bold'),
            foreground='#E74C3C',
            background='#FFE5E5',
            padding=(10, 2)
        )
        self.calibration_indicator.pack(side=tk.LEFT, padx=(15, 0))
        
        # Update indicator visibility based on status
        def update_indicator_visibility(*args):
            if self.calibration_status_var.get():
                self.calibration_indicator.pack(side=tk.LEFT, padx=(15, 0))
            else:
                self.calibration_indicator.pack_forget()
        
        self.calibration_status_var.trace('w', update_indicator_visibility)
        update_indicator_visibility()  # Initial update
        
        # Stop All button
        stop_all_button = ttk.Button(
            header_frame,
            text="⏹ Stop All Flows",
            command=self.stop_all_flows,
            style='Warning.TButton'
        )
        stop_all_button.grid(row=0, column=1, sticky="e", padx=15)
        
        # The flow frame (LabelFrame)
        self.flow_frame = ttk.LabelFrame(
            center_container,
            text="",
            padding="15",
            style='TLabelframe'
        )
        self.flow_frame.grid(row=1, column=0, sticky="nsew")
        self.setup_flow_panel() # This now just sets up the scrollable container

        # --- Right Panel for Plots ---
        plot_outer_frame = ttk.LabelFrame(
            self.main_container,
            text=" 📊 Real-time Monitoring",
            padding="10",
            style='TLabelframe'
        )
        plot_outer_frame.grid(row=0, column=2, padx=(10, 0), pady=0, sticky="nsew")
        
        # Button frame for plot controls
        plot_button_frame = ttk.Frame(plot_outer_frame)
        plot_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            plot_button_frame,
            text="🔄 Reset Graphs",
            command=self.reset_graphs,
            style='TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        plot_frame = ttk.Frame(plot_outer_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create plots in the right panel
        if not self.is_raspberry:
            self.fig, self.ax1, self.ax2, self.ax3, self.canvas = self.create_plot_canvas(plot_frame)

    def setup_connection_panel(self, parent):
        """Sets up the panel for COM port selection and scanning with modern styling."""
        connection_frame = ttk.LabelFrame(
            parent, 
            text=" 🔌 Connection",
            padding="12",
            style='TLabelframe'
        )
        connection_frame.pack(padx=0, pady=(0, 12), fill="x", side=tk.TOP)

        # COM Port selection row
        port_frame = ttk.Frame(connection_frame)
        port_frame.pack(fill="x", pady=(0, 10))
        
        com_port_label = ttk.Label(port_frame, text="COM Port:", font=('Segoe UI', 10))
        com_port_label.pack(side=tk.LEFT, padx=(0, 8))

        self.com_port_var = tk.StringVar()
        ports = [f"COM{i}" for i in range(1, 25)]
        self.com_port_dropdown = ttk.Combobox(
            port_frame,
            textvariable=self.com_port_var,
            values=ports,
            state="readonly",
            width=12,
            font=('Segoe UI', 10)
        )
        self.com_port_dropdown.pack(side=tk.LEFT, padx=0)
        self.com_port_dropdown.bind("<<ComboboxSelected>>", self.on_com_port_selected)

        # Set default port from settings or controller, defaulting to COM13
        default_port = self.controller.get_port() or self.settings.get('port', 'COM13')
        self.com_port_var.set(default_port)
        # Configure controller with the default port if not already set
        if not self.controller.get_port():
            self.controller.set_port(default_port)
            self.print_to_command_output(f"COM Port set to {default_port}", 'info')

        # Scan button with modern primary styling
        self.scan_button = ttk.Button(
            connection_frame, 
            text="🔍 Scan Instruments", 
            command=self.scan_instruments,
            style='Primary.TButton'
        )
        self.scan_button.pack(fill="x", pady=(0, 8))
        
        # Calibration routine button
        self.calibration_button = ttk.Button(
            connection_frame,
            text="⚙️ Calibration Routine",
            command=self.open_calibration_window,
            style='TButton'
        )
        self.calibration_button.pack(fill="x", pady=(0, 0))

    def setup_concentration_panel(self, parent):
        """Sets up the concentration control panel with modern styling."""
        self.concentration_frame = ttk.LabelFrame(
            parent, 
            text=" ⚗️ Concentration Control",
            padding="12",
            style='TLabelframe'
        )
        self.concentration_frame.pack(padx=0, pady=(0, 0), fill="x", side=tk.TOP)
        
        row = 0
        
        # Base gas (air) - always address 20
        ttk.Label(
            self.concentration_frame, 
            text="Base gas (air):",
            font=('Segoe UI', 10)
        ).grid(row=row, column=0, padx=5, pady=8, sticky="w")
        
        self.gas1_address_var = tk.StringVar(value="20")
        address_label = ttk.Label(
            self.concentration_frame, 
            text="Address 20", 
            foreground=self.colors['secondary'],
            font=('Segoe UI', 10, 'bold')
        )
        address_label.grid(row=row, column=1, padx=5, pady=8, sticky="e")
        # Gas1 is always address 20
        self.instrument_addresses['gas1'] = 20
        row += 1
        
        # Gas 2 (variable concentration) instrument selection
        ttk.Label(
            self.concentration_frame, 
            text="Variable gas:",
            font=('Segoe UI', 10)
        ).grid(row=row, column=0, padx=5, pady=8, sticky="w")
        
        self.gas2_address_var = tk.StringVar(value="Not assigned")
        # Create list of addresses 1-24 plus "Not assigned"
        address_options = ["Not assigned"] + [str(i) for i in range(1, 25)]
        self.gas2_dropdown = ttk.Combobox(
            self.concentration_frame,
            textvariable=self.gas2_address_var,
            values=address_options,
            state="readonly",
            width=14,
            font=('Segoe UI', 10)
        )
        self.gas2_dropdown.grid(row=row, column=1, padx=5, pady=8, sticky="e")
        self.gas2_dropdown.bind("<<ComboboxSelected>>", self.on_gas2_selected)
        row += 1
        
        # Modern separator
        ttk.Separator(self.concentration_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=12)
        row += 1
        
        # Concentration parameters with descriptive labels
        concentration_labels = {
            'C_tot_ppm': 'Outflow desired\nconcentration (ppm)',
            'C1_ppm': 'Base gas\nconcentration (ppm)',
            'C2_ppm': 'Gas concentration (ppm)'
        }
        
        for key in ['C_tot_ppm', 'C1_ppm', 'C2_ppm']:
            label = ttk.Label(
                self.concentration_frame, 
                text=concentration_labels[key], 
                justify=tk.LEFT,
                font=('Segoe UI', 9)
            )
            label.grid(row=row, column=0, padx=5, pady=6, sticky="w")
            
            entry = ttk.Entry(
                self.concentration_frame, 
                textvariable=self.variables[key], 
                width=12,
                font=('Segoe UI', 10)
            )
            entry.grid(row=row, column=1, padx=5, pady=6, sticky="e")
            row += 1

        ttk.Label(
            self.concentration_frame, 
            text="Max Flow (ln/min):",
            font=('Segoe UI', 9)
        ).grid(row=row, column=0, padx=5, pady=6, sticky="w")
        
        self.variables['max_flow'] = tk.DoubleVar(value=1.5)
        ttk.Entry(
            self.concentration_frame, 
            textvariable=self.variables['max_flow'], 
            width=12,
            font=('Segoe UI', 10)
        ).grid(row=row, column=1, padx=5, pady=6, sticky="e")
        row += 1

        # Modern calculate button
        ttk.Button(
            self.concentration_frame, 
            text="⚡ Calculate Flows",
            command=self.calculate_flows,
            style='Success.TButton'
        ).grid(row=row, column=0, columnspan=2, pady=(12, 5), sticky="ew", padx=5)
        row += 1
        
        # Uncertainty display section
        ttk.Separator(self.concentration_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=8)
        row += 1
        
        # Uncertainty header
        ttk.Label(
            self.concentration_frame, 
            text="📊 Measurement Uncertainty",
            font=('Segoe UI', 10, 'bold'),
            foreground=self.colors['primary']
        ).grid(row=row, column=0, columnspan=2, padx=5, pady=(5, 8), sticky="w")
        row += 1
        
        # Concentration uncertainty display
        ttk.Label(
            self.concentration_frame, 
            text="Concentration:",
            font=('Segoe UI', 9)
        ).grid(row=row, column=0, padx=5, pady=3, sticky="w")
        
        self.uncertainty_conc_label = ttk.Label(
            self.concentration_frame, 
            text="—",
            font=('Segoe UI', 9),
            foreground=self.colors['secondary']
        )
        self.uncertainty_conc_label.grid(row=row, column=1, padx=5, pady=3, sticky="e")
        row += 1
        
        # Flow uncertainties
        ttk.Label(
            self.concentration_frame, 
            text="Base gas flow:",
            font=('Segoe UI', 9)
        ).grid(row=row, column=0, padx=5, pady=3, sticky="w")
        
        self.uncertainty_f1_label = ttk.Label(
            self.concentration_frame, 
            text="—",
            font=('Segoe UI', 9),
            foreground=self.colors['secondary']
        )
        self.uncertainty_f1_label.grid(row=row, column=1, padx=5, pady=3, sticky="e")
        row += 1
        
        ttk.Label(
            self.concentration_frame, 
            text="Variable gas flow:",
            font=('Segoe UI', 9)
        ).grid(row=row, column=0, padx=5, pady=3, sticky="w")
        
        self.uncertainty_f2_label = ttk.Label(
            self.concentration_frame, 
            text="—",
            font=('Segoe UI', 9),
            foreground=self.colors['secondary']
        )
        self.uncertainty_f2_label.grid(row=row, column=1, padx=5, pady=3, sticky="e")

    def on_gas1_selected(self, event):
        """Gas1 is always address 20 (Base gas), so this is not used anymore."""
        pass
    
    def on_gas2_selected(self, event):
        """Handle Gas 2 (variable gas) instrument selection."""
        selected = self.gas2_address_var.get()
        if selected == "Automatic":
            self.instrument_addresses['gas2'] = 'auto'
            self.print_to_command_output(f"Variable gas set to Automatic mode", 'success')
            self.update_status(f"Variable gas: Automatic selection enabled", "green")
        elif selected != "Not assigned":
            try:
                addr = int(selected.split()[0])  # Extract just the number from "3 (High flow)"
                self.instrument_addresses['gas2'] = addr
                instrument_name = INSTRUMENT_NAMES.get(addr, f"Address {addr}")
                self.print_to_command_output(f"Variable gas assigned to {instrument_name} (address {addr})", 'success')
                self.update_status(f"Variable gas: {instrument_name}", "green")
            except (ValueError, IndexError):
                pass

    def on_com_port_selected(self, event):
        """Handle COM port selection from the dropdown."""
        selected_port = self.com_port_var.get()
        self.controller.set_port(selected_port)
        self.print_to_command_output(f"COM Port set to {selected_port}", 'info')
        self.update_status(f"Port set to {selected_port}. Ready to scan.", "blue")

    def scan_instruments(self):
        """Scan for connected instruments and update the UI."""
        self.print_to_command_output("Scanning for instruments...", 'info')
        self.scan_button.config(state="disabled")
        
        def scan_thread():
            try:
                found_instruments = self.controller.scan_for_instruments()
                self.after(0, lambda: self.print_to_command_output(f"Found instruments at addresses: {found_instruments}", 'success'))
                self.after(0, self.update_ui_with_scan_results, found_instruments)
            except Exception as e:
                self.after(0, lambda: self.print_to_command_output(f"Scan failed: {e}", 'error'))
            finally:
                self.after(0, lambda: self.scan_button.config(state="normal"))

        Thread(target=scan_thread, daemon=True).start()

    def open_calibration_window(self):
        """Open the calibration routine window"""
        try:
            calibration_win = CalibrationWindow(self, self.controller)
            # Don't use grab_set() to allow navigation in main window
        except Exception as e:
            self.print_to_command_output(f"Error opening calibration window: {e}", 'error')

    def update_ui_with_scan_results(self, found_instruments):
        """Update UI after scanning is complete. ONLY updates the scrollable frame."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.controller.is_connected() or not found_instruments:
            self.print_to_command_output("No instruments found or connection failed.", 'warning')
            self.update_status("Scan complete. No instruments found.", "orange")
            ttk.Label(self.scrollable_frame, text="No instruments found.").pack(pady=20)
            return

        instruments_metadata = self.controller.get_instrument_metadata()
        self.print_to_command_output(f"Connected to {len(instruments_metadata)} instruments at addresses: {list(instruments_metadata.keys())}", 'success')
        
        # Auto-assign base gas (address 20) to gas1 if found
        if 20 in instruments_metadata:
            self.instrument_addresses['gas1'] = 20
            self.print_to_command_output(f"Base gas (air) auto-assigned to address 20", 'info')
        
        # Update Gas2 dropdown with available addresses (excluding base gas at 20)
        # Format: "address (name)" for found instruments, just "address" for others
        # Add "Automatic" as the first option
        address_options = ["Automatic"]
        
        # Add all addresses 1-24 (excluding 20 which is base gas)
        for addr in range(1, 25):
            if addr == 20:  # Skip base gas address
                continue
            if addr in instruments_metadata:
                # Found instrument - show with name
                name = INSTRUMENT_NAMES.get(addr, f"Unknown")
                address_options.append(f"{addr} ({name})")
            else:
                # Not found - just show address number
                address_options.append(str(addr))
        
        self.gas2_dropdown['values'] = address_options
        
        # Set "Automatic" as the default selection
        if len(address_options) > 1:
            self.gas2_address_var.set("Automatic")
            self.instrument_addresses['gas2'] = 'auto'
            # Set initial current_gas2_address to first available mix gas for monitoring
            for addr in [3, 5, 8]:  # Try high, medium, low flow in order
                if addr in instruments_metadata:
                    self.current_gas2_address = addr
                    break
            self.print_to_command_output(f"Variable gas set to Automatic mode (will select best instrument based on flow)", 'info')
        
        # Display instruments in the specified order
        for addr in INSTRUMENT_DISPLAY_ORDER:
            if addr in instruments_metadata:
                metadata = instruments_metadata[addr]
                self.setup_instrument_controls(self.scrollable_frame, addr, metadata)
        
        # Display any additional instruments not in the predefined order
        for addr in sorted(instruments_metadata.keys()):
            if addr not in INSTRUMENT_DISPLAY_ORDER:
                metadata = instruments_metadata[addr]
                self.setup_instrument_controls(self.scrollable_frame, addr, metadata)
            
        self.update_status(f"Scan complete. Found {len(instruments_metadata)} instruments.", "green")
        self.instruments_scanned = True

    def start_all_flows(self):
        """Start flow on all connected instruments."""
        if not self.controller.is_connected():
            self.update_status("Please connect and scan for instruments first.", "orange")
            return
        self.print_to_command_output("Starting all flows...", 'info')
        self.controller.start_all()

    def stop_all_flows(self):
        """Stop flow on all connected instruments."""
        if not self.controller.is_connected():
            self.update_status("Please connect and scan for instruments first.", "orange")
            return
        if not messagebox.askyesno("Warning", STOP_MFCS_WARNING_MESSAGE):
            self.print_to_command_output("Stop all flows cancelled.", 'info')
            return
        self.print_to_command_output("Stopping all flows...", 'warning')
        self.controller.stop_all()
    
    def stop_single_flow(self, address: int):
        """Stop flow for a single instrument by setting it to 0."""
        try:
            if not messagebox.askyesno("Warning", STOP_MFCS_WARNING_MESSAGE):
                instrument_name = INSTRUMENT_NAMES.get(address, f"Address {address}")
                self.print_to_command_output(f"Stop cancelled for {instrument_name}.", 'info')
                return
            self.controller.set_flow(address, 0)
            # Also clear the entry field
            if address in self.flow_entries:
                self.flow_entries[address].delete(0, tk.END)
                self.flow_entries[address].insert(0, "0.0")
            instrument_name = INSTRUMENT_NAMES.get(address, f"Address {address}")
            self.print_to_command_output(f"Stopped flow for {instrument_name}", 'warning')
        except Exception as e:
            self.print_to_command_output(f"Error stopping flow for address {address}: {e}", 'error')

    def setup_flow_panel(self):
        """Sets up the panel that contains the scrollable list of instruments with modern styling."""
        # Create a container frame with a better background color
        container = ttk.Frame(self.flow_frame)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, borderwidth=0, background='#FFFFFF', highlightthickness=0)
        self.scrollable_frame = ttk.Frame(canvas, style='TFrame')
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
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
        """Setup controls for a single instrument with modern card-style design."""
        if metadata is None:
            metadata = self.controller.get_instrument_metadata(addr)
        
        # Get instrument name from configuration
        instrument_name = INSTRUMENT_NAMES.get(addr, "Unknown")
        
        # Create a modern card-style frame for this instrument
        instrument_outer = ttk.Frame(parent, style='Card.TFrame')
        instrument_outer.pack(fill=tk.X, expand=True, pady=8, padx=5)
        
        # Header with instrument name and address
        header_frame = ttk.Frame(instrument_outer)
        header_frame.pack(fill=tk.X, padx=12, pady=(10, 5))
        
        name_label = ttk.Label(
            header_frame,
            text=instrument_name,
            font=('Segoe UI', 12, 'bold'),
            foreground=self.colors['primary']
        )
        name_label.pack(side=tk.LEFT)
        
        addr_label = ttk.Label(
            header_frame,
            text=f"[{addr}]",
            font=('Segoe UI', 10),
            foreground=self.colors['secondary']
        )
        addr_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # Separator line
        ttk.Separator(instrument_outer, orient='horizontal').pack(fill=tk.X, padx=12, pady=5)
        
        # Main content frame
        content_frame = ttk.Frame(instrument_outer)
        content_frame.pack(fill=tk.X, expand=True, padx=12, pady=(0, 10))
        
        # Display min/max flow range with modern badge style
        min_flow = metadata.get('min_flow', 0.0)
        max_flow = metadata.get('max_flow', 0.0)
        unit = metadata.get('unit', 'ln/min')
        
        range_frame = ttk.Frame(content_frame)
        range_frame.grid(row=0, column=0, columnspan=5, pady=(0, 10), sticky='w')
        
        ttk.Label(
            range_frame,
            text="📊 Range:",
            font=('Segoe UI', 9, 'bold'),
            foreground=self.colors['text']
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(
            range_frame, 
            text=f"{min_flow:.4f} - {max_flow:.2f} {unit}",
            font=('Segoe UI', 9),
            foreground=self.colors['secondary']
        ).pack(side=tk.LEFT)
        
        # Flow setter with modern layout
        setter_frame = ttk.Frame(content_frame)
        setter_frame.grid(row=1, column=0, columnspan=5, pady=(0, 12), sticky='ew')
        
        ttk.Label(
            setter_frame, 
            text="🎯 Set Flow:",
            font=('Segoe UI', 10, 'bold')
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        entry = ttk.Entry(setter_frame, width=12, font=('Segoe UI', 10))
        entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(
            setter_frame, 
            text=unit,
            font=('Segoe UI', 9),
            foreground=self.colors['text']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Save the entry and unit label for later use
        self.flow_entries[addr] = entry
        if addr not in self.reading_labels:
            self.reading_labels[addr] = {}

        # Modern Apply button
        set_button = ttk.Button(
            setter_frame,
            text="✓ Apply",
            command=lambda a=addr: self.set_manual_flow(a),
            style='Success.TButton'
        )
        set_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Modern Stop button (sets flow to 0 for this instrument)
        stop_button = ttk.Button(
            setter_frame,
            text="⏹ Stop",
            command=lambda a=addr: self.stop_single_flow(a),
            style='Warning.TButton'
        )
        stop_button.pack(side=tk.LEFT)

        # Reading displays with modern card-like badges
        readings_frame = ttk.Frame(content_frame)
        readings_frame.grid(row=2, column=0, columnspan=5, sticky='ew')
        
        params = [
            ('Flow', unit, '💨'),
            ('Valve', '%', '🔧'),
            ('Temperature', '°C', '🌡️')
        ]
        
        for i, (param, param_unit, icon) in enumerate(params):
            param_frame = ttk.Frame(readings_frame)
            param_frame.pack(fill=tk.X, pady=4)
            
            # Icon and label
            label_frame = ttk.Frame(param_frame)
            label_frame.pack(side=tk.LEFT, fill=tk.X, expand=False)
            
            ttk.Label(
                label_frame, 
                text=f"{icon} {param}:",
                font=('Segoe UI', 9),
                width=14
            ).pack(side=tk.LEFT)
            
            # Value display with modern styling
            value_label = tk.Label(
                param_frame,
                text="---",
                width=12,
                font=('Segoe UI', 10, 'bold'),
                background='#F8F9FA',
                foreground=self.colors['primary'],
                relief='flat',
                borderwidth=1,
                anchor='center',
                padx=8,
                pady=4
            )
            value_label.pack(side=tk.LEFT, padx=(5, 5))
            
            # Unit label
            ttk.Label(
                param_frame, 
                text=param_unit,
                font=('Segoe UI', 9),
                foreground=self.colors['text'],
                width=8
            ).pack(side=tk.LEFT)
            
            self.reading_labels[addr][param] = value_label

    def set_manual_flow(self, address: int):
        """Set the flow for an instrument from its manual entry field."""
        try:
            flow_str = self.flow_entries[address].get()
            flow_entered = float(flow_str)

            metadata = self.controller.get_instrument_metadata(address)
            unit = str(metadata.get('unit', 'ln/min')).strip()
            unit_lc = unit.lower()
            max_flow_native = float(metadata.get('max_flow', 0.0) or 0.0)

            # The entry is displayed in the instrument's native unit.
            # FlowController.set_flow() expects L/min and converts to native units internally.
            if 'ml' in unit_lc or 'mln' in unit_lc:
                flow_native = flow_entered  # mL/min
                flow_lmin = flow_entered / 1000.0
            else:
                flow_native = flow_entered  # L/min
                flow_lmin = flow_entered

            if abs(flow_native) < 1e-12 and not messagebox.askyesno("Warning", STOP_MFCS_WARNING_MESSAGE):
                instrument_name = INSTRUMENT_NAMES.get(address, f"Address {address}")
                self.print_to_command_output(f"Set-to-zero cancelled for {instrument_name}.", 'info')
                return

            # Sanity check: prevent obvious unit mixups (e.g., entering 100 thinking mL/min but treated as L/min)
            if max_flow_native > 0 and flow_native > max_flow_native * 1.05:
                instrument_name = INSTRUMENT_NAMES.get(address, f"Address {address}")
                self.print_to_command_output(
                    f"Refusing to set {instrument_name} (addr {address}) to {flow_native:.3f} {unit}: exceeds max {max_flow_native:.3f} {unit}",
                    'error'
                )
                return

            ok = self.controller.set_flow(address, flow_lmin)
            instrument_name = INSTRUMENT_NAMES.get(address, f"Address {address}")
            if ok:
                if 'ml' in unit_lc or 'mln' in unit_lc:
                    self.print_to_command_output(
                        f"Manually set {instrument_name} (addr {address}) to {flow_native:.3f} {unit} ({flow_lmin:.6f} L/min)",
                        'success'
                    )
                else:
                    self.print_to_command_output(
                        f"Manually set {instrument_name} (addr {address}) to {flow_lmin:.6f} L/min",
                        'success'
                    )
            else:
                self.print_to_command_output(
                    f"Failed to set {instrument_name} (addr {address}) to {flow_native:.3f} {unit}",
                    'error'
                )
        except ValueError:
            self.print_to_command_output(f"Invalid flow value entered for address {address}: '{flow_str}'", 'error')
        except Exception as e:
            self.print_to_command_output(f"Error setting flow for address {address}: {e}", 'error')
    
    def select_best_instrument_for_flow(self, required_flow: float) -> int:
        """
        Select the best instrument for the required flow based on available instruments.
        The instrument should be able to handle the flow at its maximum capacity.
        
        Args:
            required_flow: The required flow in ln/min
            
        Returns:
            The address of the best instrument, or None if no suitable instrument found
        """
        if not self.controller.is_connected():
            return None
        
        # Get all available instruments (excluding base gas at address 20)
        instruments_metadata = self.controller.get_instrument_metadata()
        
        self.print_to_command_output(
            f"[DEBUG] Selecting instrument for flow {required_flow:.6f} L/min", 'info'
        )
        
        # Build a list of candidate instruments with their ranges
        candidates = []
        for addr, metadata in instruments_metadata.items():
            if addr == 20:  # Skip base gas
                continue
            
            max_flow = metadata.get('max_flow', 0)
            min_flow = metadata.get('min_flow', 0)
            unit = metadata.get('unit', 'ln/min')
            
            self.print_to_command_output(
                f"[DEBUG]   Addr {addr}: range {min_flow:.4f}-{max_flow:.4f} {unit}", 'info'
            )
            
            # Convert flow ranges to L/min for consistent comparison
            # Units can be: 'ml/min', 'mln/min', 'ln/min', 'l/min'
            if 'ml' in unit.lower() or 'mln' in unit.lower():
                max_flow_lmin = max_flow / 1000  # Convert ml/min to L/min
                min_flow_lmin = min_flow / 1000
                self.print_to_command_output(
                    f"[DEBUG]     → Converted: {min_flow_lmin:.6f}-{max_flow_lmin:.6f} L/min", 'info'
                )
            else:
                max_flow_lmin = max_flow  # Already in L/min
                min_flow_lmin = min_flow
                self.print_to_command_output(
                    f"[DEBUG]     → Already in L/min: {min_flow_lmin:.6f}-{max_flow_lmin:.6f} L/min", 'info'
                )
            
            # Check if the instrument can handle this flow (using converted values)
            if min_flow_lmin <= required_flow <= max_flow_lmin:
                # Calculate utilization percentage
                utilization = (required_flow / max_flow_lmin) * 100 if max_flow_lmin > 0 else 0
                self.print_to_command_output(
                    f"[DEBUG]     ✓ Can handle flow (utilization: {utilization:.1f}%)", 'info'
                )
                candidates.append({
                    'address': addr,
                    'max_flow': max_flow_lmin,  # Store converted value for sorting
                    'min_flow': min_flow_lmin,
                    'utilization': utilization,
                    'name': INSTRUMENT_NAMES.get(addr, f"Address {addr}")
                })
            else:
                self.print_to_command_output(
                    f"[DEBUG]     ✗ Cannot handle flow (required={required_flow:.6f}, range={min_flow_lmin:.6f}-{max_flow_lmin:.6f} L/min)", 'info'
                )
        
        if not candidates:
            self.print_to_command_output(
                f"[DEBUG]   No suitable instrument found!", 'warning'
            )
            return None
        
        # Sort by utilization percentage (descending) - highest utilization = best accuracy
        # The instrument running closest to its max capacity will have best precision
        candidates.sort(key=lambda x: x['utilization'], reverse=True)
        
        # Select the best candidate (highest utilization)
        best = candidates[0]
        
        self.print_to_command_output(
            f"[DEBUG]   Selected: {best['name']} (addr {best['address']}, utilization: {best['utilization']:.1f}%)", 'success'
        )
        self.print_to_command_output(
            f"Flow {required_flow:.3f} ln/min → {best['name']} "
            f"(range: {best['min_flow']:.4f}-{best['max_flow']:.2f} ln/min, "
            f"utilization: {best['utilization']:.1f}%)", 
            'info'
        )
        
        return best['address']

    def calculate_flows(self):
        if not self.controller.is_connected():
            self.update_status("Please connect the instruments", "red")
            self.print_to_command_output("Please connect the instruments", 'warning')
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
                    self.print_to_command_output(msg, 'error')
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
            addr1 = self.instrument_addresses.get('gas1')  # Base gas (air) - always 20
            addr2_raw = self.instrument_addresses.get('gas2')  # Variable gas (could be 'auto' or address)
            
            # Check if roles have been assigned
            if addr1 is None or addr2_raw is None:
                self.update_status("Please assign variable gas instrument.", "orange")
                self.print_to_command_output("Please select a variable gas from the dropdown.", 'warning')
                return
            
            # Automatic instrument selection based on required flow
            if addr2_raw == 'auto':
                addr2 = self.select_best_instrument_for_flow(Q2)
                if addr2 is None:
                    self.update_status("No suitable instrument found for the required flow.", "red")
                    self.print_to_command_output("Automatic selection failed: no suitable instrument found.", 'error')
                    return
                instrument_name = INSTRUMENT_NAMES.get(addr2, f"Address {addr2}")
                self.print_to_command_output(f"Automatic mode: Selected {instrument_name} (address {addr2}) for flow {Q2:.3f} ln/min", 'success')
                # Store the selected address temporarily for plotting (will be reset to 'auto' on next calculate)
                self.current_gas2_address = addr2
            else:
                addr2 = addr2_raw
                self.current_gas2_address = addr2
            
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
                # Get instrument name and unit
                instrument_name = INSTRUMENT_NAMES.get(addr, f"Address {addr}")
                unit = self.controller.read_unit(addr)
                
                # Convert flow value based on unit if needed
                converted_flow = flow
                if isinstance(flow, (float, int)):
                    # If unit is ml/min, convert from ln/min
                    if unit == "ml/min":
                        converted_flow = flow * 1000  # Convert ln/min to ml/min
                    flow_messages.append(f"{instrument_name}: {converted_flow:.3f} {unit}")
                else:
                    flow_messages.append(f"{instrument_name}: {str(flow)} {unit}")

            result_msg = "Calculated: " + ", ".join(flow_messages)
            self.print_to_command_output(result_msg, 'success')
            
            # Calculate and display expected uncertainty
            try:
                from ..models.uncertainty import calculate_required_flow_with_uncertainty
                
                # Convert flows to mln/min
                Q1_mln = Q1 * 1000  # ln/min to mln/min
                Q2_mln = Q2 * 1000
                
                u_details = calculate_required_flow_with_uncertainty(
                    values['C_tot_ppm'],
                    values['C1_ppm'],
                    Q1_mln,
                    values['C2_ppm'],
                    addr1,
                    addr2
                )
                
                self.print_to_command_output(
                    f"Expected uncertainty: ±{u_details['u_C']:.2f} ppm "
                    f"({u_details['relative_error']:.2f}% of target)", 
                    'info'
                )
                self.print_to_command_output(
                    f"Flow uncertainties: Base gas ±{u_details['u_F1']:.3f} mln/min, "
                    f"Variable gas ±{u_details['u_F2']:.3f} mln/min", 
                    'info'
                )
            except Exception as ue:
                print(f"Uncertainty calculation error: {ue}")
            
            self.update_status("Flows calculated and pre-filled. Click 'Apply' to set.", "green")
        except ValueError as e:
            self.update_status(f"Error: {str(e)}", "red")
            self.print_to_command_output(f"Error: {str(e)}", 'error')
        except Exception as e:
            self.update_status(f"Calculation error: {str(e)}", "red")
            self.print_to_command_output(f"Calculation error: {str(e)}", 'error')

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
            address_2_raw = self.instrument_addresses.get('gas2')

            # For plotting, use the current selected address (in case of auto mode)
            if address_2_raw == 'auto':
                address_2 = self.current_gas2_address
            else:
                address_2 = address_2_raw

            # Skip if addresses not assigned
            if address_1 is None or address_2 is None:
                # Skip data collection if roles haven't been assigned yet
                return

            # Get readings for both instruments
            readings_1 = self.controller.get_readings(address_1)
            readings_2 = self.controller.get_readings(address_2)
            
            # Ensure 'Flow' exists in readings
            if 'Flow' not in readings_1 or 'Flow' not in readings_2:
                # Keep this message as it's important
                print("Missing Flow readings in controller response")
                return
                
            flow1 = readings_1.get('Flow')
            flow2 = readings_2.get('Flow')
            
            # Check if flows are None (reading error) - do this BEFORE unit conversion
            if flow1 is None or flow2 is None:
                # Skip this data point if readings failed
                return
            
            unit1 = readings_1.get('Unit', 'ln/min')
            unit2 = readings_2.get('Unit', 'ln/min')

            # Convert to ln/min if needed (flow values are guaranteed non-None here)
            if unit1 in ("ml/min", "mln/min") and flow1 != 0:
                flow1 = flow1 / 1000
            if unit2 in ("ml/min", "mln/min") and flow2 != 0:
                flow2 = flow2 / 1000

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
                
                # Calculate uncertainty
                # Convert flows to mln/min for uncertainty calculations
                flow1_mln = convert_flow_to_mln_min(flow1, 'ln/min')
                flow2_mln = convert_flow_to_mln_min(flow2, 'ln/min')
                
                u_C, details = propagate_concentration_uncertainty(
                    C1, flow1_mln, C2, flow2_mln, 
                    address_1, address_2
                )
                
                # Store current uncertainty
                self.current_uncertainty = {
                    'u_C': u_C,
                    'u_F1': details['u_F1'],
                    'u_F2': details['u_F2'],
                    'C_expected': details['C_expected']
                }
                
                # Update uncertainty display labels
                if hasattr(self, 'uncertainty_conc_label'):
                    self.uncertainty_conc_label.config(
                        text=f"±{u_C:.2f} ppm ({(u_C/actual_conc*100):.1f}%)" if actual_conc > 0 else "—"
                    )
                if hasattr(self, 'uncertainty_f1_label'):
                    self.uncertainty_f1_label.config(
                        text=f"±{details['u_F1']:.3f} mln/min"
                    )
                if hasattr(self, 'uncertainty_f2_label'):
                    self.uncertainty_f2_label.config(
                        text=f"±{details['u_F2']:.3f} mln/min"
                    )
            else:
                actual_conc = 0
                u_C = 0
                # Reset uncertainty display
                if hasattr(self, 'uncertainty_conc_label'):
                    self.uncertainty_conc_label.config(text="—")
                if hasattr(self, 'uncertainty_f1_label'):
                    self.uncertainty_f1_label.config(text="—")
                if hasattr(self, 'uncertainty_f2_label'):
                    self.uncertainty_f2_label.config(text="—")

            target_conc = self.variables['C_tot_ppm'].get()
            self.conc_data['target'].append(target_conc)
            self.conc_data['actual'].append(actual_conc)
            self.uncertainty_data.append(u_C)

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
                self.uncertainty_data = self.uncertainty_data[-max_points:]

        except Exception as e:
            print(f"Error collecting plot data: {e}")
            import traceback
            traceback.print_exc()

    def create_plot_canvas(self, parent):
        """Create a canvas with three subplots stacked vertically for flow and concentration monitoring with modern styling."""
        fig = Figure(figsize=(8, 10), dpi=100)
        fig.patch.set_facecolor('#FFFFFF')
        
        # Create three subplots stacked vertically (3 rows, 1 column)
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)
        
        # Modern color palette
        plot_colors = {
            'primary': '#3498DB',
            'secondary': '#2ECC71',
            'accent': '#E74C3C',
            'grid': '#ECF0F1'
        }
        
        # Style the plots with modern aesthetics
        for ax in [ax1, ax2, ax3]:
            ax.set_facecolor('#FAFAFA')
            ax.grid(True, linestyle='--', alpha=0.3, color=plot_colors['grid'], linewidth=0.8)
            ax.tick_params(axis='x', rotation=45, labelsize=9, colors=self.colors['text'])
            ax.tick_params(axis='y', labelsize=9, colors=self.colors['text'])
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')
            ax.spines['left'].set_linewidth(1.5)
            ax.spines['bottom'].set_linewidth(1.5)

        fig.tight_layout(pad=2.5)
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        return fig, ax1, ax2, ax3, canvas

    def update_plots(self):
        """Update the main window plots with current data using modern styling"""
        if not self.controller.is_connected() or not hasattr(self, 'ax1'):
            return  # Skip plot updates if not connected or plots not initialized

        try:
            # Modern colors for plots
            color_flow1 = '#3498DB'  # Blue
            color_flow2 = '#2ECC71'  # Green
            color_actual = '#3498DB'  # Blue
            color_target = '#E74C3C'  # Red
            
            # --- Plot Flow 1 ---
            self.ax1.clear()
            self.ax1.set_title('Base Gas Flow', fontsize=11, fontweight='bold', color=self.colors['primary'], pad=10)
            self.ax1.set_ylabel('ln/min', fontsize=9, color=self.colors['text'])
            self.ax1.set_facecolor('#FAFAFA')
            self.ax1.grid(True, linestyle='--', alpha=0.3, color='#ECF0F1', linewidth=0.8)
            self.ax1.spines['top'].set_visible(False)
            self.ax1.spines['right'].set_visible(False)
            self.ax1.spines['left'].set_color('#BDC3C7')
            self.ax1.spines['bottom'].set_color('#BDC3C7')
            
            if self.flow1_data['pv']:
                self.ax1.plot(self.times, self.flow1_data['pv'], color=color_flow1, 
                            linewidth=2.5, label='Measured', alpha=0.9)
                self.ax1.fill_between(self.times, self.flow1_data['pv'], alpha=0.1, color=color_flow1)
                
                # Add setpoint line if available
                address_1 = self.instrument_addresses.get('gas1')
                if address_1 and address_1 in self.controller.setpoints:
                    setpoint = self.controller.setpoints[address_1]
                    self.ax1.axhline(y=setpoint, color='#E74C3C', linestyle='--', 
                                   linewidth=1.5, label=f'Setpoint: {setpoint:.3f}', alpha=0.7)
                
                self.ax1.legend(loc='upper right', fontsize=8, framealpha=0.9)
            else:
                self.ax1.text(0.5, 0.5, 'Waiting for data...', 
                            horizontalalignment='center',
                            verticalalignment='center', 
                            transform=self.ax1.transAxes,
                            fontsize=10,
                            color='#95A5A6')

            # --- Plot Flow 2 ---
            self.ax2.clear()
            self.ax2.set_title('Variable Gas Flow', fontsize=11, fontweight='bold', color=self.colors['primary'], pad=10)
            self.ax2.set_ylabel('ln/min', fontsize=9, color=self.colors['text'])
            self.ax2.set_facecolor('#FAFAFA')
            self.ax2.grid(True, linestyle='--', alpha=0.3, color='#ECF0F1', linewidth=0.8)
            self.ax2.spines['top'].set_visible(False)
            self.ax2.spines['right'].set_visible(False)
            self.ax2.spines['left'].set_color('#BDC3C7')
            self.ax2.spines['bottom'].set_color('#BDC3C7')
            
            if self.flow2_data['pv']:
                self.ax2.plot(self.times, self.flow2_data['pv'], color=color_flow2, 
                            linewidth=2.5, label='Measured', alpha=0.9)
                self.ax2.fill_between(self.times, self.flow2_data['pv'], alpha=0.1, color=color_flow2)
                
                # Add setpoint line if available
                address_2_raw = self.instrument_addresses.get('gas2')
                address_2 = self.current_gas2_address if address_2_raw == 'auto' else address_2_raw
                if address_2 and address_2 in self.controller.setpoints:
                    setpoint = self.controller.setpoints[address_2]
                    self.ax2.axhline(y=setpoint, color='#E74C3C', linestyle='--', 
                                   linewidth=1.5, label=f'Setpoint: {setpoint:.3f}', alpha=0.7)
                
                self.ax2.legend(loc='upper right', fontsize=8, framealpha=0.9)
            else:
                self.ax2.text(0.5, 0.5, 'Waiting for data...', 
                            horizontalalignment='center',
                            verticalalignment='center', 
                            transform=self.ax2.transAxes,
                            fontsize=10,
                            color='#95A5A6')

            # --- Plot Concentration ---
            self.ax3.clear()
            self.ax3.set_title('Concentration with Uncertainty', fontsize=11, fontweight='bold', color=self.colors['primary'], pad=10)
            self.ax3.set_ylabel('ppm', fontsize=9, color=self.colors['text'])
            self.ax3.set_xlabel('Time', fontsize=9, color=self.colors['text'])
            self.ax3.set_facecolor('#FAFAFA')
            self.ax3.grid(True, linestyle='--', alpha=0.3, color='#ECF0F1', linewidth=0.8)
            self.ax3.spines['top'].set_visible(False)
            self.ax3.spines['right'].set_visible(False)
            self.ax3.spines['left'].set_color('#BDC3C7')
            self.ax3.spines['bottom'].set_color('#BDC3C7')
            
            if self.conc_data['actual'] and len(self.uncertainty_data) > 0:
                actual_conc = np.array(self.conc_data['actual'])
                uncertainty = np.array(self.uncertainty_data)
                
                # Main line for actual concentration
                self.ax3.plot(self.times, actual_conc, color=color_actual, 
                            linewidth=2.5, label='Actual', alpha=0.9, zorder=3)
                
                # Target line
                self.ax3.plot(self.times, self.conc_data['target'], color=color_target, 
                            linewidth=2, linestyle='--', label='Target', alpha=0.8, zorder=2)
                
                # Error band (±1 sigma uncertainty)
                self.ax3.fill_between(self.times, 
                                     actual_conc - uncertainty, 
                                     actual_conc + uncertainty,
                                     alpha=0.2, color=color_actual, 
                                     label='±1σ uncertainty',
                                     zorder=1)
                
                self.ax3.legend(loc='upper right', fontsize=8, framealpha=0.9)
            elif self.conc_data['actual']:
                # Fallback if uncertainty data not available
                self.ax3.plot(self.times, self.conc_data['actual'], color=color_actual, 
                            linewidth=2.5, label='Actual', alpha=0.9)
                self.ax3.plot(self.times, self.conc_data['target'], color=color_target, 
                            linewidth=2, linestyle='--', label='Target', alpha=0.8)
                self.ax3.fill_between(self.times, self.conc_data['actual'], alpha=0.1, color=color_actual)
                self.ax3.legend(loc='upper right', fontsize=8, framealpha=0.9)

            # Use draw_idle() instead of draw() for better performance
            # draw_idle() defers the actual drawing until the GUI is idle
            self.canvas.draw_idle()
        except Exception as e:
            print(f"Error updating main plots: {e}")
    
    def reset_graphs(self):
        """Reset all graph axes and clear data"""
        try:
            # Clear all data arrays
            self.times = []
            self.flow1_data = {'pv': []}
            self.flow2_data = {'pv': []}
            self.conc_data = {'target': [], 'actual': []}
            self.uncertainty_data = []
            
            # Clear all three axes
            if hasattr(self, 'ax1'):
                self.ax1.clear()
                self.ax1.set_facecolor('#FAFAFA')
                self.ax1.grid(True, linestyle='--', alpha=0.3, color='#ECF0F1', linewidth=0.8)
                self.ax1.set_ylabel('Flow (ln/min)', fontsize=10, fontweight='bold', color=self.colors['text'])
                self.ax1.set_title('Base Gas Flow', fontsize=11, fontweight='bold', color=self.colors['primary'], pad=10)
                self.ax1.tick_params(axis='x', rotation=45, labelsize=9, colors=self.colors['text'])
                self.ax1.tick_params(axis='y', labelsize=9, colors=self.colors['text'])
                self.ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                self.ax1.spines['top'].set_visible(False)
                self.ax1.spines['right'].set_visible(False)
                self.ax1.spines['left'].set_color('#BDC3C7')
                self.ax1.spines['bottom'].set_color('#BDC3C7')
                self.ax1.spines['left'].set_linewidth(1.5)
                self.ax1.spines['bottom'].set_linewidth(1.5)
            
            if hasattr(self, 'ax2'):
                self.ax2.clear()
                self.ax2.set_facecolor('#FAFAFA')
                self.ax2.grid(True, linestyle='--', alpha=0.3, color='#ECF0F1', linewidth=0.8)
                self.ax2.set_ylabel('Flow (ln/min)', fontsize=10, fontweight='bold', color=self.colors['text'])
                self.ax2.set_title('Variable Gas Flow', fontsize=11, fontweight='bold', color=self.colors['primary'], pad=10)
                self.ax2.tick_params(axis='x', rotation=45, labelsize=9, colors=self.colors['text'])
                self.ax2.tick_params(axis='y', labelsize=9, colors=self.colors['text'])
                self.ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                self.ax2.spines['top'].set_visible(False)
                self.ax2.spines['right'].set_visible(False)
                self.ax2.spines['left'].set_color('#BDC3C7')
                self.ax2.spines['bottom'].set_color('#BDC3C7')
                self.ax2.spines['left'].set_linewidth(1.5)
                self.ax2.spines['bottom'].set_linewidth(1.5)
            
            if hasattr(self, 'ax3'):
                self.ax3.clear()
                self.ax3.set_facecolor('#FAFAFA')
                self.ax3.grid(True, linestyle='--', alpha=0.3, color='#ECF0F1', linewidth=0.8)
                self.ax3.set_xlabel('Time', fontsize=10, fontweight='bold', color=self.colors['text'])
                self.ax3.set_ylabel('Concentration (ppm)', fontsize=10, fontweight='bold', color=self.colors['text'])
                self.ax3.set_title('Concentration with Uncertainty', fontsize=11, fontweight='bold', color=self.colors['primary'], pad=10)
                self.ax3.tick_params(axis='x', rotation=45, labelsize=9, colors=self.colors['text'])
                self.ax3.tick_params(axis='y', labelsize=9, colors=self.colors['text'])
                self.ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                self.ax3.spines['top'].set_visible(False)
                self.ax3.spines['right'].set_visible(False)
                self.ax3.spines['left'].set_color('#BDC3C7')
                self.ax3.spines['bottom'].set_color('#BDC3C7')
                self.ax3.spines['left'].set_linewidth(1.5)
                self.ax3.spines['bottom'].set_linewidth(1.5)
            
            # Redraw the canvas
            if hasattr(self, 'canvas'):
                self.fig.tight_layout(pad=2.5)
                self.canvas.draw_idle()
            
            self.print_to_command_output("Graphs reset successfully", 'success')
            
        except Exception as e:
            self.print_to_command_output(f"Error resetting graphs: {e}", 'error')
        
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
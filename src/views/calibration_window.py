import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List
import os
import json
import time
from threading import Thread
from datetime import datetime


class CalibrationWindow(tk.Toplevel):
    """Window for concentration calibration routine mode"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.parent_window = parent
        self.title("Concentration Calibration Routine Mode")
        self.geometry("1100x750")  # Bigger window
        self.resizable(True, True)
        
        # Settings file path
        self.settings_file = os.path.join(os.getcwd(), "calibration_settings.json")
        
        # Default calibration directory
        self.default_calib_dir = os.path.join(os.getcwd(), "calibration_file")
        os.makedirs(self.default_calib_dir, exist_ok=True)
        
        # Load saved settings or use defaults
        saved_settings = self.load_settings()
        
        # Variables with saved/default values
        self.directory_var = tk.StringVar(value=saved_settings.get('directory', self.default_calib_dir))
        self.input_concentration_var = tk.StringVar(value=saved_settings.get('input_concentration', '5000'))
        self.total_flow_var = tk.StringVar(value=saved_settings.get('total_flow', '1.0'))
        self.flow_unit_var = tk.StringVar(value=saved_settings.get('flow_unit', 'L/min'))
        self.step_number_var = tk.StringVar(value=saved_settings.get('step_number', '11'))
        self.step_mode_var = tk.StringVar(value=saved_settings.get('step_mode', 'automatic'))
        self.initial_conc_var = tk.StringVar(value=saved_settings.get('initial_conc', '0'))
        self.final_conc_var = tk.StringVar(value=saved_settings.get('final_conc', '100'))
        self.step_duration_var = tk.StringVar(value=saved_settings.get('step_duration', '60'))
        self.duration_unit_var = tk.StringVar(value=saved_settings.get('duration_unit', 'seconds'))
        self.back_forth_var = tk.BooleanVar(value=saved_settings.get('back_forth', False))
        
        # Store computed steps
        self.computed_steps = []
        
        # Calibration state
        self.is_running = False
        self.current_step = 0
        self.calibration_thread = None
        
        # Gas address configuration
        self.addr_neutral = tk.IntVar(value=saved_settings.get('addr_neutral', 20))  # Default: air at 20
        self.addr_mix_high = tk.IntVar(value=saved_settings.get('addr_mix_high', 3))  # Default: high flow at 3
        self.addr_mix_med = tk.IntVar(value=saved_settings.get('addr_mix_med', 5))  # Default: medium flow at 5
        self.addr_mix_low = tk.IntVar(value=saved_settings.get('addr_mix_low', 8))  # Default: low flow at 8
        self.addr_helium = tk.IntVar(value=saved_settings.get('addr_helium', 10))  # Default: helium at 10
        
        self.setup_gui()
        self.update_step_preview()
        
        # Save settings on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_gui(self):
        """Setup the GUI layout"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # === LEFT PANEL: Configuration ===
        left_frame = ttk.LabelFrame(main_frame, text="Calibration Configuration", padding="15")
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        row = 0
        
        # Directory selection
        ttk.Label(left_frame, text="Data Directory:", font=('Segoe UI', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        row += 1
        
        dir_frame = ttk.Frame(left_frame)
        dir_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        dir_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(dir_frame, textvariable=self.directory_var, state='readonly', 
                 width=40).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(dir_frame, text="...", width=3, 
                  command=self.select_directory).grid(row=0, column=1)
        row += 1
        
        # Input gas concentration
        ttk.Label(left_frame, text="Input Gas Concentration (ppm):", 
                 font=('Segoe UI', 10)).grid(row=row, column=0, sticky=tk.W, pady=(5, 5))
        ttk.Entry(left_frame, textvariable=self.input_concentration_var, 
                 width=20).grid(row=row, column=1, sticky=tk.W, pady=(5, 5))
        row += 1
        
        # Total flow
        ttk.Label(left_frame, text="Total Flow:", 
                 font=('Segoe UI', 10)).grid(row=row, column=0, sticky=tk.W, pady=(5, 5))
        flow_frame = ttk.Frame(left_frame)
        flow_frame.grid(row=row, column=1, sticky=tk.W, pady=(5, 5))
        ttk.Entry(flow_frame, textvariable=self.total_flow_var, 
                 width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(flow_frame, textvariable=self.flow_unit_var, 
                    values=["L/min", "mL/min (sccm)"], state='readonly', 
                    width=15).pack(side=tk.LEFT)
        row += 1
        
        # Separator
        ttk.Separator(left_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Gas address configuration
        ttk.Label(left_frame, text="Gas Address Configuration:", 
                 font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, 
                                                     sticky=tk.W, pady=(0, 5))
        row += 1
        
        # Create a compact grid for gas addresses
        addr_grid_frame = ttk.Frame(left_frame)
        addr_grid_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        addr_configs = [
            ("Neutral (Air):", self.addr_neutral, 20),
            ("Mix-High:", self.addr_mix_high, 3),
            ("Mix-Med:", self.addr_mix_med, 5),
            ("Mix-Low:", self.addr_mix_low, 8),
            ("Helium:", self.addr_helium, 10)
        ]
        
        for i, (label_text, var, default) in enumerate(addr_configs):
            ttk.Label(addr_grid_frame, text=label_text, font=('Segoe UI', 9)).grid(
                row=i, column=0, sticky=tk.W, padx=(0, 5), pady=1)
            ttk.Spinbox(addr_grid_frame, textvariable=var, from_=1, to=24, width=4).grid(
                row=i, column=1, sticky=tk.W, pady=1)
            ttk.Label(addr_grid_frame, text=f"(def: {default})", 
                     font=('Segoe UI', 8, 'italic'), foreground='#7F8C8D').grid(
                row=i, column=2, sticky=tk.W, padx=(3, 0), pady=1)
        
        row += 1
        
        # Separator
        ttk.Separator(left_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Step configuration header
        ttk.Label(left_frame, text="Step Configuration:", 
                 font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, columnspan=2, 
                                                     sticky=tk.W, pady=(0, 10))
        row += 1
        
        # Step number
        ttk.Label(left_frame, text="Number of Steps:", 
                 font=('Segoe UI', 10)).grid(row=row, column=0, sticky=tk.W, pady=(5, 5))
        ttk.Entry(left_frame, textvariable=self.step_number_var, 
                 width=20).grid(row=row, column=1, sticky=tk.W, pady=(5, 5))
        row += 1
        
        # Step mode selection
        mode_frame = ttk.LabelFrame(left_frame, text="Step Generation Mode", padding="10")
        mode_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 10))
        row += 1
        
        # Manual mode
        ttk.Radiobutton(mode_frame, text="Manual Step Entry", 
                       variable=self.step_mode_var, value="manual",
                       command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.manual_button = ttk.Button(mode_frame, text="Enter Steps Manually", 
                                       command=self.open_manual_entry, state='disabled')
        self.manual_button.grid(row=0, column=1, padx=(10, 0))
        # Force button to use normal foreground color even when disabled
        self.style = ttk.Style()
        self.style.map('TButton', foreground=[('disabled', '#000000')])
        
        # Automatic mode
        ttk.Radiobutton(mode_frame, text="Automatic Computation", 
                       variable=self.step_mode_var, value="automatic",
                       command=self.on_mode_change).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        auto_frame = ttk.Frame(mode_frame)
        auto_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(auto_frame, text="Initial Conc (ppm):").grid(row=0, column=0, sticky=tk.W, padx=(20, 5))
        self.initial_entry = ttk.Entry(auto_frame, textvariable=self.initial_conc_var, width=10)
        self.initial_entry.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(auto_frame, text="Final Conc (ppm):").grid(row=1, column=0, sticky=tk.W, padx=(20, 5), pady=(5, 0))
        self.final_entry = ttk.Entry(auto_frame, textvariable=self.final_conc_var, width=10)
        self.final_entry.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Step duration
        ttk.Label(left_frame, text="Step Duration:", 
                 font=('Segoe UI', 10)).grid(row=row, column=0, sticky=tk.W, pady=(10, 5))
        duration_frame = ttk.Frame(left_frame)
        duration_frame.grid(row=row, column=1, sticky=tk.W, pady=(10, 5))
        ttk.Entry(duration_frame, textvariable=self.step_duration_var, 
                 width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(duration_frame, textvariable=self.duration_unit_var, 
                    values=["seconds", "minutes", "hours"], state='readonly', 
                    width=10).pack(side=tk.LEFT)
        row += 1
        
        # Back and forth option
        ttk.Checkbutton(left_frame, text="Back and Forth Mode", 
                       variable=self.back_forth_var,
                       command=self.update_step_preview).grid(row=row, column=0, columnspan=2, 
                                                              sticky=tk.W, pady=(10, 0))
        row += 1
        
        # Update button (recalculates steps based on current configuration)
        ttk.Button(left_frame, text="🔄 Update Step Preview", 
                  command=self.update_step_preview).grid(row=row, column=0, columnspan=2, 
                                                         pady=(20, 10))
        ttk.Label(left_frame, text="(Recalculates steps based on current settings)", 
                 font=('Segoe UI', 8, 'italic'), foreground='#7F8C8D').grid(
                     row=row+1, column=0, columnspan=2, pady=(0, 10))
        row += 2
        
        # === RIGHT PANEL: Step Preview ===
        right_frame = ttk.LabelFrame(main_frame, text="Step Preview", padding="15")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        # Info label
        info_label = ttk.Label(right_frame, 
                              text="Computed steps will appear below:",
                              font=('Segoe UI', 9, 'italic'))
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Step list with scrollbar
        list_frame = ttk.Frame(right_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.step_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                       font=('Consolas', 10), height=20)
        self.step_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.step_listbox.yview)
        
        # Summary label
        self.summary_label = ttk.Label(right_frame, text="", 
                                       font=('Segoe UI', 9, 'bold'),
                                       foreground='#2E86AB')
        self.summary_label.grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
        # Progress bar
        self.progress_label = ttk.Label(right_frame, text="Progress: 0%", 
                                       font=('Segoe UI', 9, 'bold'))
        self.progress_label.grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        
        self.progress_bar = ttk.Progressbar(right_frame, mode='determinate', 
                                           length=300, maximum=100)
        self.progress_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.progress_bar['value'] = 0
        
        # === BOTTOM: Action Buttons ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=(20, 0))
        
        self.start_button = ttk.Button(button_frame, text="Start Calibration Routine", 
                  command=self.start_routine,
                  style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Calibration", 
                  command=self.stop_routine,
                  style='Warning.TButton',
                  state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Export Configuration", 
                  command=self.export_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", 
                  command=self.on_close).pack(side=tk.LEFT, padx=5)
        
        # Bind variables to auto-update
        self.initial_conc_var.trace('w', lambda *args: self.update_step_preview())
        self.final_conc_var.trace('w', lambda *args: self.update_step_preview())
        self.step_number_var.trace('w', lambda *args: self.update_step_preview())
        
    def select_directory(self):
        """Open directory selection dialog"""
        directory = filedialog.askdirectory(
            title="Select Directory for Data Logging",
            initialdir=os.path.expanduser("~")
        )
        if directory:
            self.directory_var.set(directory)
            
    def on_mode_change(self):
        """Handle step mode change"""
        mode = self.step_mode_var.get()
        if mode == "manual":
            self.manual_button.config(state='normal')
            self.initial_entry.config(state='disabled')
            self.final_entry.config(state='disabled')
        else:
            self.manual_button.config(state='disabled')
            self.initial_entry.config(state='normal')
            self.final_entry.config(state='normal')
        self.update_step_preview()
        
    def open_manual_entry(self):
        """Open dialog for manual step entry"""
        dialog = ManualStepDialog(self, self.computed_steps)
        self.wait_window(dialog)
        if dialog.result:
            self.computed_steps = dialog.result
            self.update_step_display()
            
    def update_step_preview(self):
        """Update the step preview based on current settings"""
        mode = self.step_mode_var.get()
        
        if mode == "automatic":
            try:
                initial = float(self.initial_conc_var.get())
                final = float(self.final_conc_var.get())
                num_steps = int(self.step_number_var.get())
                
                if num_steps < 2:
                    self.computed_steps = [initial]
                else:
                    # Generate linear steps
                    step_size = (final - initial) / (num_steps - 1)
                    self.computed_steps = [initial + i * step_size for i in range(num_steps)]
                
                # Add back and forth if enabled
                if self.back_forth_var.get() and len(self.computed_steps) > 1:
                    # Add reverse order (excluding the last point to avoid duplication)
                    self.computed_steps.extend(reversed(self.computed_steps[:-1]))
                    
            except ValueError:
                self.computed_steps = []
        
        self.update_step_display()
        
    def update_step_display(self):
        """Update the listbox with computed steps"""
        self.step_listbox.delete(0, tk.END)
        
        for i, step in enumerate(self.computed_steps, 1):
            self.step_listbox.insert(tk.END, f"Step {i:3d}: {step:8.2f} ppm")
        
        # Update summary
        if self.computed_steps:
            total_steps = len(self.computed_steps)
            try:
                duration = float(self.step_duration_var.get())
                unit = self.duration_unit_var.get()
                total_time = total_steps * duration
                
                # Convert to appropriate unit
                if unit == "seconds":
                    if total_time >= 3600:
                        time_str = f"{total_time/3600:.1f} hours"
                    elif total_time >= 60:
                        time_str = f"{total_time/60:.1f} minutes"
                    else:
                        time_str = f"{total_time:.0f} seconds"
                elif unit == "minutes":
                    if total_time >= 60:
                        time_str = f"{total_time/60:.1f} hours"
                    else:
                        time_str = f"{total_time:.0f} minutes"
                else:  # hours
                    time_str = f"{total_time:.1f} hours"
                
                self.summary_label.config(
                    text=f"Total: {total_steps} steps | Estimated time: {time_str}"
                )
            except ValueError:
                self.summary_label.config(text=f"Total: {total_steps} steps")
        else:
            self.summary_label.config(text="No steps configured")
            
    def start_routine(self):
        """Start the calibration routine"""
        # Validate configuration
        if self.directory_var.get() == "No directory selected" or not os.path.exists(self.directory_var.get()):
            messagebox.showerror("Error", "Please select a valid directory for data logging.")
            return
            
        if not self.computed_steps:
            messagebox.showerror("Error", "No calibration steps configured.")
            return
            
        if not self.controller.is_connected():
            messagebox.showerror("Error", "Please connect instruments before starting calibration.")
            return
            
        try:
            input_conc = float(self.input_concentration_var.get())
            total_flow = float(self.total_flow_var.get())
            step_duration = float(self.step_duration_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values in configuration.")
            return
        
        # Convert flow unit to L/min if needed
        flow_unit = self.flow_unit_var.get()
        if "mL/min" in flow_unit or "sccm" in flow_unit:
            total_flow = total_flow / 1000  # Convert mL/min to L/min
        
        # Confirm before starting
        response = messagebox.askyesno(
            "Start Calibration",
            f"Start calibration routine with {len(self.computed_steps)} steps?\n\n"
            f"This will take approximately {self.summary_label.cget('text').split('Estimated time: ')[1]}",
            icon='question'
        )
        
        if response:
            # Save settings before starting
            self.save_settings()
            
            # Reset and update UI
            self.progress_bar['value'] = 0
            self.progress_label.config(text="Progress: 0%")
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            
            # Start calibration in separate thread
            self.is_running = True
            self.calibration_thread = Thread(target=self._run_calibration, 
                                            args=(input_conc, total_flow, step_duration), 
                                            daemon=True)
            self.calibration_thread.start()
            
            # Notify parent window
            if hasattr(self.parent_window, 'print_to_command_output'):
                self.parent_window.print_to_command_output(
                    f"Calibration routine started: {len(self.computed_steps)} steps", 'success'
                )
                # Set calibration mode flag
                self.parent_window.in_calibration_mode = True
                self.parent_window.calibration_status_var.set("CALIBRATION MODE ACTIVE")
    
    def stop_routine(self):
        """Stop the calibration routine"""
        if self.is_running:
            response = messagebox.askyesno(
                "Stop Calibration",
                "Are you sure you want to stop the calibration routine?",
                icon='warning'
            )
            if response:
                self.is_running = False
                self.start_button.config(state='normal')
                self.stop_button.config(state='disabled')
                if hasattr(self.parent_window, 'print_to_command_output'):
                    self.parent_window.print_to_command_output(
                        "Calibration routine stopped by user", 'warning'
                    )
                    self.parent_window.in_calibration_mode = False
                    self.parent_window.calibration_status_var.set("")
    
    def _run_calibration(self, input_conc: float, total_flow: float, step_duration: float):
        """Run the calibration routine in a separate thread"""
        try:
            # Create log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.directory_var.get(), f"calibration_{timestamp}.csv")
            
            with open(log_file, 'w') as f:
                f.write("Step,Target_Conc_ppm,Actual_Conc_ppm,Base_Flow_Lmin,Variable_Flow_Lmin,Variable_Instrument,Timestamp\n")
            
            duration_seconds = self._convert_duration_to_seconds(step_duration, self.duration_unit_var.get())
            
            for step_num, target_conc in enumerate(self.computed_steps, 1):
                if not self.is_running:
                    break
                
                self.current_step = step_num
                
                # Update progress bar
                progress = (step_num / len(self.computed_steps)) * 100
                self.after(0, lambda p=progress, s=step_num: self._update_progress(p, s))
                
                # Update status in parent window
                if hasattr(self.parent_window, 'print_to_command_output'):
                    self.parent_window.print_to_command_output(
                        f"Calibration Step {step_num}/{len(self.computed_steps)}: {target_conc:.2f} ppm", 'info'
                    )
                
                # Calculate required flows
                try:
                    # Special handling for 0 ppm - use only neutral gas
                    if target_conc <= 0.1:  # Near zero concentration
                        Q_air = total_flow  # All neutral gas (air)
                        Q_methane = 0  # No variable gas (methane)
                        addr_neutral = self.addr_neutral.get()
                        addr_mix = None
                        
                        # Set only neutral gas flow
                        self.controller.set_flow(addr_neutral, Q_air)
                        # Stop all mix gas instruments
                        for addr in [self.addr_mix_high.get(), self.addr_mix_med.get(), self.addr_mix_low.get()]:
                            self.controller.set_flow(addr, 0)
                        
                        # Store for data logging
                        addr_base = addr_neutral
                        addr_variable = None
                        Q1 = Q_air
                        Q2 = 0
                        
                        if hasattr(self.parent_window, 'print_to_command_output'):
                            self.parent_window.print_to_command_output(
                                f"  Flows set: Air (addr {addr_neutral})={Q_air:.3f} L/min, Methane=0 L/min", 'info'
                            )
                    else:
                        # Normal calculation for non-zero concentrations
                        from ..models.calculations import calculate_flows_variable
                        
                        # Q1 is for C1 (input gas = methane at 5000ppm)
                        # Q2 is for C2 (air = 0ppm)
                        Q_methane, Q_air = calculate_flows_variable(
                            target_conc,
                            input_conc,  # C1 = methane concentration
                            0,  # C2 = air (0 ppm)
                            total_flow
                        )
                        
                        if hasattr(self.parent_window, 'print_to_command_output'):
                            self.parent_window.print_to_command_output(
                                f"  Calculated flows: Methane={Q_methane:.6f} L/min, Air={Q_air:.6f} L/min", 'info'
                            )
                        
                        # Get neutral gas (air) address
                        addr_neutral = self.addr_neutral.get()
                        
                        # Use automatic selection for mix gas (methane) from configured addresses
                        available_addrs = [self.addr_mix_high.get(), self.addr_mix_med.get(), self.addr_mix_low.get()]
                        
                        if hasattr(self.parent_window, 'print_to_command_output'):
                            self.parent_window.print_to_command_output(
                                f"  Selecting instrument for methane flow {Q_methane:.6f} L/min from addresses {available_addrs}", 'info'
                            )
                        
                        if hasattr(self.parent_window, 'select_best_instrument_for_flow'):
                            # Call the selection method
                            addr_mix = self.parent_window.select_best_instrument_for_flow(Q_methane)
                            
                            if hasattr(self.parent_window, 'print_to_command_output'):
                                self.parent_window.print_to_command_output(
                                    f"  Selection returned: address {addr_mix}", 'info'
                                )
                            
                            # Verify the selected address is in the configured mix addresses
                            if addr_mix is None:
                                if hasattr(self.parent_window, 'print_to_command_output'):
                                    self.parent_window.print_to_command_output(
                                        f"Warning: No suitable instrument found for {Q_methane:.6f} L/min, skipping step", 'warning'
                                    )
                                continue
                            elif addr_mix not in available_addrs:
                                if hasattr(self.parent_window, 'print_to_command_output'):
                                    self.parent_window.print_to_command_output(
                                        f"Warning: Selected address {addr_mix} not in configured mix addresses {available_addrs}, using fallback", 'warning'
                                    )
                                # Use the first available address as fallback
                                addr_mix = available_addrs[0]
                        else:
                            # Fallback to high flow if selection method not available
                            addr_mix = self.addr_mix_high.get()
                            if hasattr(self.parent_window, 'print_to_command_output'):
                                self.parent_window.print_to_command_output(
                                    f"  Using fallback: address {addr_mix}", 'info'
                                )
                        
                        # Set flows: neutral gas (air) and mix gas (methane)
                        self.controller.set_flow(addr_neutral, Q_air)
                        self.controller.set_flow(addr_mix, Q_methane)
                        
                        # Stop other mix gas instruments
                        for addr in available_addrs:
                            if addr != addr_mix:
                                self.controller.set_flow(addr, 0)
                        
                        # Store for data logging
                        addr_base = addr_neutral
                        addr_variable = addr_mix
                        Q1 = Q_air  # Neutral gas flow
                        Q2 = Q_methane  # Mix gas flow
                        
                        if hasattr(self.parent_window, 'print_to_command_output'):
                            self.parent_window.print_to_command_output(
                                f"  Flows set: Air (addr {addr_neutral})={Q_air:.3f} L/min, Methane (addr {addr_mix})={Q_methane:.3f} L/min", 'info'
                            )
                    
                    # Wait for stabilization and log data
                    time.sleep(duration_seconds)
                    
                    # Read actual values
                    actual_flow1 = self.controller.read_flow(addr_base) or 0
                    actual_flow2 = 0
                    if addr_variable is not None:
                        actual_flow2 = self.controller.read_flow(addr_variable) or 0
                    
                    # Calculate actual concentration
                    if (actual_flow1 + actual_flow2) > 0:
                        actual_conc = (input_conc * actual_flow2) / (actual_flow1 + actual_flow2)
                    else:
                        actual_conc = 0
                    
                    # Log to file
                    with open(log_file, 'a') as f:
                        f.write(f"{step_num},{target_conc:.2f},{actual_conc:.2f},{actual_flow1:.4f},{actual_flow2:.4f},{addr_variable or 0},{datetime.now().isoformat()}\n")
                    
                except Exception as e:
                    if hasattr(self.parent_window, 'print_to_command_output'):
                        self.parent_window.print_to_command_output(
                            f"Error in step {step_num}: {e}", 'error'
                        )
            
            # Calibration complete
            self.is_running = False
            self.after(0, lambda: self.start_button.config(state='normal'))
            self.after(0, lambda: self.stop_button.config(state='disabled'))
            self.after(0, lambda: self._update_progress(100, len(self.computed_steps)))
            
            if hasattr(self.parent_window, 'print_to_command_output'):
                self.parent_window.print_to_command_output(
                    f"Calibration routine completed. Data saved to: {log_file}", 'success'
                )
                self.parent_window.in_calibration_mode = False
                self.parent_window.calibration_status_var.set("")
            
            # Stop all flows
            self.controller.stop_all()
            
            messagebox.showinfo("Calibration Complete", 
                              f"Calibration routine finished.\n\nData saved to:\n{log_file}")
            
        except Exception as e:
            self.is_running = False
            if hasattr(self.parent_window, 'print_to_command_output'):
                self.parent_window.print_to_command_output(f"Calibration error: {e}", 'error')
                self.parent_window.in_calibration_mode = False
                self.parent_window.calibration_status_var.set("")
            messagebox.showerror("Calibration Error", f"An error occurred:\n{str(e)}")
    
    def _convert_duration_to_seconds(self, duration: float, unit: str) -> float:
        """Convert duration to seconds"""
        if unit == "minutes":
            return duration * 60
        elif unit == "hours":
            return duration * 3600
        return duration  # already in seconds
    
    def _update_progress(self, progress: float, step: int):
        """Update progress bar and label (must be called from main thread)"""
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"Progress: {progress:.0f}% (Step {step}/{len(self.computed_steps)})")
    
    def load_settings(self) -> dict:
        """Load saved settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def save_settings(self):
        """Save current settings to file"""
        settings = {
            'directory': self.directory_var.get(),
            'input_concentration': self.input_concentration_var.get(),
            'total_flow': self.total_flow_var.get(),
            'flow_unit': self.flow_unit_var.get(),
            'step_number': self.step_number_var.get(),
            'step_mode': self.step_mode_var.get(),
            'initial_conc': self.initial_conc_var.get(),
            'final_conc': self.final_conc_var.get(),
            'step_duration': self.step_duration_var.get(),
            'duration_unit': self.duration_unit_var.get(),
            'back_forth': self.back_forth_var.get(),
            'addr_neutral': self.addr_neutral.get(),
            'addr_mix_high': self.addr_mix_high.get(),
            'addr_mix_med': self.addr_mix_med.get(),
            'addr_mix_low': self.addr_mix_low.get(),
            'addr_helium': self.addr_helium.get()
        }
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def on_close(self):
        """Handle window close event"""
        # Stop calibration if running
        if self.is_running:
            response = messagebox.askyesno(
                "Calibration Running",
                "Calibration is currently running. Stop and close?",
                icon='warning'
            )
            if not response:
                return
            self.is_running = False
            if self.calibration_thread:
                self.calibration_thread.join(timeout=2)
        
        # Save settings
        self.save_settings()
        
        # Reset calibration mode in parent
        if hasattr(self.parent_window, 'in_calibration_mode'):
            self.parent_window.in_calibration_mode = False
            self.parent_window.calibration_status_var.set("")
        
        self.destroy()
    
    def export_config(self):
        """Export the configuration to a file"""
        if not self.computed_steps:
            messagebox.showwarning("Warning", "No steps to export.")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("=== Calibration Routine Configuration ===\n\n")
                    f.write(f"Data Directory: {self.directory_var.get()}\n")
                    f.write(f"Input Gas Concentration: {self.input_concentration_var.get()} ppm\n")
                    f.write(f"Total Flow: {self.total_flow_var.get()} {self.flow_unit_var.get()}\n")
                    f.write(f"Step Duration: {self.step_duration_var.get()} {self.duration_unit_var.get()}\n")
                    f.write(f"Back and Forth: {'Yes' if self.back_forth_var.get() else 'No'}\n")
                    f.write(f"\n=== Steps ({len(self.computed_steps)} total) ===\n\n")
                    for i, step in enumerate(self.computed_steps, 1):
                        f.write(f"Step {i}: {step:.2f} ppm\n")
                        
                messagebox.showinfo("Success", f"Configuration exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration:\n{str(e)}")


class ManualStepDialog(tk.Toplevel):
    """Dialog for manual step entry"""
    
    def __init__(self, parent, initial_steps):
        super().__init__(parent)
        self.result = None
        self.title("Manual Step Entry")
        self.geometry("400x500")
        
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Enter concentration steps (one per line):",
                 font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(text_frame, yscrollcommand=scrollbar.set,
                                   font=('Consolas', 10), width=40, height=20)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_widget.yview)
        
        # Populate with initial steps
        if initial_steps:
            for step in initial_steps:
                self.text_widget.insert(tk.END, f"{step:.2f}\n")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        
    def on_ok(self):
        """Parse the entered steps and close dialog"""
        text_content = self.text_widget.get("1.0", tk.END)
        lines = text_content.strip().split('\n')
        
        steps = []
        errors = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            try:
                value = float(line)
                steps.append(value)
            except ValueError:
                errors.append(f"Line {i}: '{line}' is not a valid number")
        
        if errors:
            messagebox.showerror("Invalid Input", "\n".join(errors))
            return
            
        if not steps:
            messagebox.showwarning("Warning", "No valid steps entered.")
            return
            
        self.result = steps
        self.destroy()

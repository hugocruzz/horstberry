import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List
import os


class CalibrationWindow(tk.Toplevel):
    """Window for concentration calibration routine mode"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.title("Concentration Calibration Routine Mode")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # Variables
        self.directory_var = tk.StringVar(value="No directory selected")
        self.input_concentration_var = tk.StringVar(value="5000")
        self.total_flow_var = tk.StringVar(value="1.0")
        self.flow_unit_var = tk.StringVar(value="L/min")
        self.step_number_var = tk.StringVar(value="10")
        self.step_mode_var = tk.StringVar(value="automatic")  # "manual" or "automatic"
        self.initial_conc_var = tk.StringVar(value="0")
        self.final_conc_var = tk.StringVar(value="100")
        self.step_duration_var = tk.StringVar(value="60")
        self.duration_unit_var = tk.StringVar(value="seconds")
        self.back_forth_var = tk.BooleanVar(value=False)
        
        # Store computed steps
        self.computed_steps = []
        
        self.setup_gui()
        self.update_step_preview()
        
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
                    values=["L/min", "sccm"], state='readonly', 
                    width=8).pack(side=tk.LEFT)
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
        
        # Update button
        ttk.Button(left_frame, text="Update Step Preview", 
                  command=self.update_step_preview).grid(row=row, column=0, columnspan=2, 
                                                         pady=(20, 10))
        row += 1
        
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
        
        # === BOTTOM: Action Buttons ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(button_frame, text="Start Calibration Routine", 
                  command=self.start_routine,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Configuration", 
                  command=self.export_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", 
                  command=self.destroy).pack(side=tk.LEFT, padx=5)
        
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
        if self.directory_var.get() == "No directory selected":
            messagebox.showerror("Error", "Please select a directory for data logging.")
            return
            
        if not self.computed_steps:
            messagebox.showerror("Error", "No calibration steps configured.")
            return
            
        try:
            input_conc = float(self.input_concentration_var.get())
            total_flow = float(self.total_flow_var.get())
            step_duration = float(self.step_duration_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values in configuration.")
            return
        
        # Confirm before starting
        response = messagebox.askyesno(
            "Start Calibration",
            f"Start calibration routine with {len(self.computed_steps)} steps?\n\n"
            f"This will take approximately {self.summary_label.cget('text').split('Estimated time: ')[1]}",
            icon='question'
        )
        
        if response:
            messagebox.showinfo("Not Implemented", 
                              "Calibration routine execution will be implemented in the next phase.")
            # TODO: Implement actual calibration routine logic
            
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

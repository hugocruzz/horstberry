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
class MainWindow(tk.Frame):
    def __init__(self, parent: tk.Tk, controller: Any, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.settings = settings
        
        self.data_logger = DataLogger()
        # Initialize storage
        self.reading_labels: Dict = {}
        self.status_labels: Dict = {}
        self.variables = {
            'C_tot_ppm': tk.DoubleVar(value=2), #Around 2ppm in the air 
            'C1_ppm': tk.DoubleVar(value=200000),
            'C2_ppm': tk.DoubleVar(value=0)
        }
        
        # Configure fonts based on platform settings
        self.default_font = (self.settings['font_family'], self.settings['font_size'])

        # Initialize plot data
        self.times = []
        self.flow1_data = {'sp': [], 'pv': []}
        self.flow2_data = {'sp': [], 'pv': []}
        
        # Setup UI components
        self.setup_gui()
        self.setup_plots()
        self.start_updates()
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_plots()

    def update_status(self, message: str, color: str = "black"):
        """Update status message"""
        if 'Status' not in self.status_labels:
            self.status_labels['Status'] = ttk.Label(self)
            self.status_labels['Status'].grid(row=1, column=0, columnspan=2, pady=5)
        self.status_labels['Status'].config(text=message, foreground=color)

    def setup_gui(self):
        # Apply font settings
        style = ttk.Style()
        style.configure('.', font=self.default_font)
        # Create main frames
        self.concentration_frame = ttk.LabelFrame(self, text="Concentration Control")
        self.flow_frame = ttk.LabelFrame(self, text="Direct Flow Control")
        
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
        for i, (addr, name) in enumerate([(5, 'Gas 1'), (8, 'Gas 2')]):
            group = ttk.LabelFrame(self.flow_frame, text=f"{name} Control")
            group.grid(row=0, column=i, padx=5, pady=5)
            
            self.setup_instrument_controls(group, addr)
            
    def setup_instrument_controls(self, parent: ttk.Frame, addr: int):
        # Flow setter
        ttk.Label(parent, text="Set Flow:").grid(row=0, column=0, padx=5, pady=2)
        entry = ttk.Entry(parent, width=10)
        entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(parent, text="ln/min").grid(row=0, column=2, padx=2, pady=2)
        
        ttk.Button(parent, 
                  text="Set",
                  command=lambda: self.set_flow(addr, entry.get())).grid(
            row=0, column=3, padx=5, pady=2)
            
        # Reading displays
        self.reading_labels[addr] = {}
        for i, param in enumerate(['Flow', 'Valve', 'Temperature']):
            ttk.Label(parent, text=f"{param}:").grid(
                row=i+1, column=0, padx=5, pady=2)
            self.reading_labels[addr][param] = ttk.Label(parent, text="---")
            self.reading_labels[addr][param].grid(
                row=i+1, column=1, columnspan=3, padx=5, pady=2)
                
    def calculate_flows(self):
        try:
            flows = self.controller.calculate_flows(
                self.variables['C_tot_ppm'].get(),
                self.variables['C1_ppm'].get(),
                self.variables['C2_ppm'].get()
            )
            self.update_status(f"Calculated: Q1={flows['Q1']:.3f}, Q2={flows['Q2']:.3f} ln/min")
        except ValueError as e:
            self.update_status(f"Error: {str(e)}", "red")
            
    def start_updates(self):
        """Start periodic updates of instrument readings"""
        def update():
            while True:
                self.update_readings()
                time.sleep(1)
        
        Thread(target=update, daemon=True).start()
                    
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
        for addr in [5, 8]:  # For each instrument
            readings = self.controller.get_readings(addr)
            for param, value in readings.items():
                if value is not None:
                    self.reading_labels[addr][param].config(
                        text=f"{value:.3f}")
                else:
                    self.reading_labels[addr][param].config(
                        text="Error")
                 
    def setup_plots(self):
        plot_frame = ttk.LabelFrame(self, text="Flow Monitoring")
        plot_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        self.fig = Figure(figsize=(10, 4))
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def start_updates(self):
        def update():
            self.update_plots()
            self.after(1000, update)  # Schedule next update
        update()  # Start the update loop
        
    def update_plots(self):
        # Get current readings and setpoints
        flow1 = self.controller.get_readings(5).get('Flow', 0)
        flow2 = self.controller.get_readings(8).get('Flow', 0)
        sp1 = self.controller.get_setpoint(5)
        sp2 = self.controller.get_setpoint(8)
        
        # Update data lists
        now = datetime.now()
        self.times.append(now)
        self.flow1_data['pv'].append(flow1)
        self.flow2_data['pv'].append(flow2)
        self.flow1_data['sp'].append(sp1)
        self.flow2_data['sp'].append(sp2)
        
        # Keep last 60 seconds
        if len(self.times) > 60:
            self.times.pop(0)
            for data in [self.flow1_data, self.flow2_data]:
                data['sp'].pop(0)
                data['pv'].pop(0)
        
        # Plot data
        self.ax1.clear()
        self.ax2.clear()
        
        times_rel = [(t - self.times[0]).total_seconds() for t in self.times]
        
        # Plot both setpoint and measured value
        self.ax1.plot(times_rel, self.flow1_data['sp'], 'r--', label='Setpoint 1')
        self.ax1.plot(times_rel, self.flow1_data['pv'], 'b-', label='Flow 1')
        self.ax2.plot(times_rel, self.flow2_data['sp'], 'r--', label='Setpoint 2')
        self.ax2.plot(times_rel, self.flow2_data['pv'], 'b-', label='Flow 2')
        
        for ax in [self.ax1, self.ax2]:
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Flow (ln/min)')
            ax.grid(True)
            ax.legend()
        
        self.canvas.draw()
        
        # Log data
        self.data_logger.log_data({
            'flow1_sp': sp1,
            'flow1_pv': flow1,
            'flow2_sp': sp2,
            'flow2_pv': flow2
        })
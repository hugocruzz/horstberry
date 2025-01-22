import propar
import tkinter as tk
from tkinter import ttk
import time
from threading import Thread
from functions import calculate_times, calculate_flows_variable

class FlowSequenceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Flow Controller")
        
        # Detect platform and set port
        import platform
        self.PORT = '/dev/ttyUSB0' if platform.system() == 'Linux' else 'COM5'
        
        # Adjust for smaller screen
        self.root.geometry("800x480")  # Standard Pi display resolution
        
        # Initialize instruments
        self.instruments = {
            5: propar.instrument(self.PORT, 5),  # Gas1
            8: propar.instrument(self.PORT, 8)   # Gas2
        }
        
        # Increase font size for touch
        default_font = ('Helvetica', 12)
        self.root.option_add('*Font', default_font)
        # Get units for each instrument
        self.units = {}
        for addr, inst in self.instruments.items():
            try:
                self.units[addr] = inst.readParameter(129)
            except:
                self.units[addr] = "ln/min"
        
        # Variables for inputs
        self.vars = {
            'C_tot_ppm': tk.DoubleVar(value=10000),
            'C1_ppm': tk.DoubleVar(value=200000),
            'C2_ppm': tk.DoubleVar(value=0)
        }
        
        
        # Add flow control variables
        self.vars.update({
            'Q1_direct': tk.DoubleVar(value=0.0),
            'Q2_direct': tk.DoubleVar(value=0.0)
        })
        
        self.calculated_flows = {'Q1': 0.0, 'Q2': 0.0}
        self.sequence_active = False
        self.start_button = None
        self.setup_gui()
        
    def setup_gui(self):
        # Create main frames
        left_frame = ttk.LabelFrame(self.root, text="Parameters")
        right_frame = ttk.LabelFrame(self.root, text="Direct Flow Control")
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        # Concentration inputs
        for i, key in enumerate(['C_tot_ppm', 'C1_ppm', 'C2_ppm']):
            ttk.Label(left_frame, text=f"{key}:").grid(row=i, column=0, padx=5, pady=5)
            ttk.Entry(left_frame, textvariable=self.vars[key]).grid(row=i, column=1, padx=5, pady=5)
        
        # Direct flow control
        for i, (addr, name) in enumerate([(5, 'Q1'), (8, 'Q2')]):
            frame = ttk.Frame(right_frame)
            frame.grid(row=i, column=0, pady=5, sticky="w")
            
            ttk.Label(frame, text=f"{name} (ln/min):").pack(side="left", padx=5)
            entry = ttk.Entry(frame, width=10, textvariable=self.vars[f'{name}_direct'])
            entry.pack(side="left", padx=5)
            
            ttk.Button(frame, 
                      text="Set Flow", 
                      command=lambda a=addr, v=self.vars[f'{name}_direct']: 
                      self.set_direct_flow(a, v.get())
                      ).pack(side="left", padx=5)
        
        # Control buttons
        ttk.Button(left_frame, text="Calculate", command=self.calculate).grid(row=len(self.vars), column=0, pady=10)
        self.start_button = ttk.Button(left_frame, text="Start Sequence", command=self.start_sequence)
        self.start_button.grid(row=len(self.vars), column=1, pady=10)
        
        # Status frame
        self.status_frame = ttk.LabelFrame(self.root, text="Status")
        self.status_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        # Status labels
        self.status_labels = {}
        for i, param in enumerate(['Q1', 'Q2', 'Status']):
            ttk.Label(self.status_frame, text=f"{param}:").grid(row=i, column=0, padx=5, pady=5)
            self.status_labels[param] = ttk.Label(self.status_frame, text="---")
            self.status_labels[param].grid(row=i, column=1, padx=5, pady=5)
        
        self.create_readings_frame()
        
    def create_readings_frame(self):
        readings_frame = ttk.LabelFrame(self.root, text="Readings")
        readings_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        # Create labels for each instrument's readings
        self.reading_labels = {}
        row = 0
        for addr in self.instruments:
            ttk.Label(readings_frame, text=f"Instrument {addr}:").grid(row=row, column=0, pady=5)
            
            # Create frame for this instrument's readings
            inst_frame = ttk.Frame(readings_frame)
            inst_frame.grid(row=row+1, column=0, padx=5, pady=5, sticky="w")
            
            # Labels for each parameter
            self.reading_labels[addr] = {}
            for param in ['Flow', 'Valve', 'Temperature']:
                ttk.Label(inst_frame, text=f"{param}:").grid(sticky="w")
                label = ttk.Label(inst_frame, text="---")
                label.grid(row=len(self.reading_labels[addr]), column=1, padx=5)
                self.reading_labels[addr][param] = label
            
            row += 2
            
    def calculate(self):
        try:
            Q1, Q2 = calculate_flows_variable(
                self.vars['C_tot_ppm'].get(),
                self.vars['C1_ppm'].get(),
                self.vars['C2_ppm'].get(),
                Q_max_individual=self.Q_MAX_INDIVIDUAL
            )
            self.calculated_flows['Q1'] = Q1
            self.calculated_flows['Q2'] = Q2
            
            # Print calculated values
            print(f"\nCalculated Flow Rates:")
            print(f"Q1: {Q1:.3f} ln/min")
            print(f"Q2: {Q2:.3f} ln/min")
            
            # Update display
            self.status_labels['Q1'].config(text=f"{Q1:.3f} ln/min")
            self.status_labels['Q2'].config(text=f"{Q2:.3f} ln/min")
            self.status_labels['Status'].config(text="Ready to start")
            self.start_button.config(state="normal")
            
        except ValueError as e:
            self.status_labels['Status'].config(text=f"Error: {str(e)}")
            print(f"Calculation Error: {str(e)}")
    
    def start_sequence(self):
        # Validate calculation was done
        if not self.calculated_flows['Q1'] or not self.calculated_flows['Q2']:
            self.status_labels['Status'].config(text="Please calculate flows first")
            return
        
        # Handle sequence start/stop
        if not self.sequence_active:
            try:
                self.sequence_active = True
                Thread(target=self.run_sequence, daemon=True).start()
                self.start_button.config(text="Stop")
            except Exception as e:
                self.status_labels['Status'].config(text=f"Error starting: {str(e)}")
                self.sequence_active = False
        else:
            self.stop_sequence()

    def stop_sequence(self):
        try:
            self.sequence_active = False
            # Stop flows safely
            for addr in [5, 8]:
                try:
                    self.instruments[addr].writeParameter(9, 0)
                except Exception as e:
                    print(f"Error stopping instrument {addr}: {e}")
            
            self.start_button.config(text="Start Sequence")
            self.status_labels['Status'].config(text="Sequence stopped")
        except Exception as e:
            self.status_labels['Status'].config(text=f"Error stopping: {str(e)}")

    def run_sequence(self):
        try:
            # Convert calculated flows to setpoints
            for addr, flow in [(5, self.calculated_flows['Q1']), 
                              (8, self.calculated_flows['Q2'])]:
                # Convert flow to percentage of max flow
                percentage = (flow / self.Q_MAX_INDIVIDUAL) * 100
                # Convert percentage to instrument value (0-32000)
                setpoint = int((percentage / 100.0) * 32000)
                
                # Set flow
                self.instruments[addr].writeParameter(9, setpoint)
                print(f"Setting instrument {addr} to {flow:.3f} ln/min (setpoint: {setpoint})")
                
            # Monitor flows
            while self.sequence_active:
                self.update_readings()
                time.sleep(1)
                
        except Exception as e:
            self.status_labels['Status'].config(text=f"Error: {str(e)}")
            self.stop_sequence()

    def update_readings(self):
        """Update displayed readings for both instruments"""
        for addr, inst in self.instruments.items():
            try:
                # Read actual values
                flow = inst.read(33, 0, propar.PP_TYPE_FLOAT)
                valve = inst.read(33, 1, propar.PP_TYPE_FLOAT)
                temp = inst.read(33, 7, propar.PP_TYPE_FLOAT)
                
                if all(v is not None for v in [flow, valve, temp]):
                    self.reading_labels[addr]['Flow'].config(
                        text=f"{flow:.3f} {self.units[addr]}")
                    self.reading_labels[addr]['Valve'].config(
                        text=f"{valve:.1f}%")
                    self.reading_labels[addr]['Temperature'].config(
                        text=f"{temp:.1f}°C")
            except Exception as e:
                print(f"Error reading instrument {addr}: {e}")
                for param in ['Flow', 'Valve', 'Temperature']:
                    self.reading_labels[addr][param].config(text="Error")
    def set_direct_flow(self, addr, flow):
        try:
            # Validate flow
            if not 0 <= flow <= self.Q_MAX_INDIVIDUAL:
                raise ValueError(f"Flow must be between 0 and {self.Q_MAX_INDIVIDUAL} ln/min")
                
            # Set flow
            percentage = (flow / self.Q_MAX_INDIVIDUAL) * 100
            setpoint = int((percentage / 100.0) * 32000)
            self.instruments[addr].writeParameter(9, setpoint)
            
            # Calculate resulting concentration
            flows = {5: 0.0, 8: 0.0}
            flows[addr] = flow
            total_flow = sum(flows.values())
            
            if total_flow > 0:
                C1 = self.vars['C1_ppm'].get() / 1_000_000
                C2 = self.vars['C2_ppm'].get() / 1_000_000
                C_actual = (flows[5] * C1 + flows[8] * C2) / total_flow
                C_target = self.vars['C_tot_ppm'].get() / 1_000_000
                
                if abs(C_actual - C_target) > 1e-6:
                    self.status_labels['Status'].config(
                        text="Warning: Target concentration cannot be maintained",
                        foreground="orange")
                else:
                    self.status_labels['Status'].config(
                        text="Flow set successfully",
                        foreground="black")
            
        except Exception as e:
            self.status_labels['Status'].config(
                text=f"Error: {str(e)}",
                foreground="red")
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowSequenceGUI(root)
    root.mainloop()
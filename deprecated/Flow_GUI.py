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
        self.root.geometry("1024x600")
        
        # Initialize storage
        self.reading_labels = {}
        self.status_labels = {}
        self.calculated_flows = {'Q1': 0.0, 'Q2': 0.0}
        
        # Fixed maximum flow rate
        self.Q_MAX_INDIVIDUAL = 1.5  # ln/min
        
        # Initialize instruments
        self.instruments = {
            5: propar.instrument('COM5', 5),  # Gas1
            8: propar.instrument('COM5', 8)   # Gas2
        }
        
        # Variables for inputs
        self.vars = {
            'C_tot_ppm': tk.DoubleVar(value=10000),
            'C1_ppm': tk.DoubleVar(value=200000),
            'C2_ppm': tk.DoubleVar(value=0)
        }
        
        self.setup_gui()
    def setup_gui(self):
        # Create main frames
        left_frame = ttk.LabelFrame(self.root, text="Concentration Control")
        right_frame = ttk.LabelFrame(self.root, text="Direct Flow Control")
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        # Left frame - Concentration inputs and calculated flows
        row = 0
        for key in ['C_tot_ppm', 'C1_ppm', 'C2_ppm']:
            ttk.Label(left_frame, text=f"{key}:").grid(row=row, column=0, padx=5, pady=5)
            ttk.Entry(left_frame, textvariable=self.vars[key]).grid(row=row, column=1, padx=5, pady=5)
            row += 1
        
        ttk.Button(left_frame, text="Calculate", command=self.calculate).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1
        
        # Display calculated flows
        ttk.Label(left_frame, text="Calculated Q1:").grid(row=row, column=0, padx=5, pady=5)
        self.status_labels['Q1'] = ttk.Label(left_frame, text="0.000 ln/min")
        self.status_labels['Q1'].grid(row=row, column=1, padx=5, pady=5)
        row += 1
        
        ttk.Label(left_frame, text="Calculated Q2:").grid(row=row, column=0, padx=5, pady=5)
        self.status_labels['Q2'] = ttk.Label(left_frame, text="0.000 ln/min")
        self.status_labels['Q2'].grid(row=row, column=1, padx=5, pady=5)
        
        # Right frame - Direct flow control (keep existing code)
        for i, (addr, name) in enumerate([(5, 'Gas 1'), (8, 'Gas 2')]):
            group = ttk.LabelFrame(right_frame, text=f"{name} Control")
            group.grid(row=0, column=i, padx=5, pady=5)
            
            # Initialize reading labels for this instrument
            self.reading_labels[addr] = {}
            
            # Flow setter
            ttk.Label(group, text="Set Flow:").grid(row=0, column=0, padx=5, pady=2)
            entry = ttk.Entry(group, width=10)
            entry.grid(row=0, column=1, padx=5, pady=2)
            ttk.Label(group, text="ln/min").grid(row=0, column=2, padx=2, pady=2)
            
            # Set button with safer float conversion
            ttk.Button(group, 
                      text="Set", 
                      command=lambda a=addr, e=entry: self.safe_set_flow(a, e)
                      ).grid(row=0, column=3, padx=5, pady=2)
            
            # Reading displays
            for j, param in enumerate(['Flow', 'Valve', 'Temperature', 'setpoint']):
                ttk.Label(group, text=f"{param}:").grid(row=j+1, column=0, padx=5, pady=2)
                self.reading_labels[addr][param] = ttk.Label(group, text="---")
                self.reading_labels[addr][param].grid(row=j+1, column=1, columnspan=3, padx=5, pady=2)

        # Status label at bottom
        self.status_labels['Status'] = ttk.Label(self.root, text="Ready")
        self.status_labels['Status'].grid(row=2, column=0, columnspan=2, pady=5)
        
        # Start periodic updates
        self.update_readings_periodic()

    def update_readings_periodic(self):
        """Update readings every second"""
        self.update_readings()
        self.root.after(1000, self.update_readings_periodic)

    def safe_set_flow(self, addr, entry):
        """Safely convert entry text to float and set flow"""
        try:
            # Handle both '.' and ',' decimal separators
            flow_text = entry.get().replace(',', '.')
            flow = float(flow_text)
            self.set_direct_flow(addr, flow)
        except ValueError:
            self.status_labels['Status'].config(
                text="Error: Please enter a valid number",
                foreground="red")
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
            
            # Update display
            self.status_labels['Q1'].config(text=f"{Q1:.3f} ln/min")
            self.status_labels['Q2'].config(text=f"{Q2:.3f} ln/min")
            self.status_labels['Status'].config(text="Ready to start")
            
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
                setpoint = inst.read(33, 3, propar.PP_TYPE_FLOAT)
                valve = inst.read(33, 1, propar.PP_TYPE_FLOAT)
                temp = inst.read(33, 7, propar.PP_TYPE_FLOAT)
                
                if all(v is not None for v in [flow, valve, temp]):
                    self.reading_labels[addr]['Flow'].config(
                        text=f"{flow:.3f} ln/min")
                    self.reading_labels[addr]['Valve'].config(
                        text=f"{valve:.1f}%")
                    self.reading_labels[addr]['Temperature'].config(
                        text=f"{temp:.1f}°C")
                    self.reading_labels[addr]['setpoint'].config(
                        text=f"{setpoint:.3f} ln/min")
                    
            except Exception as e:
                print(f"Error reading instrument {addr}: {e}")
                for param in ['Flow', 'Valve', 'Temperature', 'setpoint']:
                    self.reading_labels[addr][param].config(text="Error")

    def set_direct_flow(self, addr, flow):
        try:
            if not 0 <= flow <= self.Q_MAX_INDIVIDUAL:
                raise ValueError(f"Flow must be between 0 and {self.Q_MAX_INDIVIDUAL} ln/min")
                
            percentage = (flow / self.Q_MAX_INDIVIDUAL) * 100
            setpoint = int((percentage / 100.0) * 32000)
            self.instruments[addr].writeParameter(9, setpoint)
            
            self.status_labels['Status'].config(
                text=f"Flow set to {flow:.3f} ln/min",
                foreground="black")
                
        except ValueError as e:
            self.status_labels['Status'].config(
                text=f"Error: {str(e)}",
                foreground="red")
        except Exception as e:
            self.status_labels['Status'].config(
                text=f"Error setting flow: {str(e)}",
                foreground="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = FlowSequenceGUI(root)
    root.mainloop()
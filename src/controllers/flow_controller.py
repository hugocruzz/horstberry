import propar
from typing import Dict, Optional

from src.models.calculations import calculate_flows_variable
class FlowController:
    def __init__(self, port: str, addresses: list = [5, 8]):
        self.instruments = {}
        self.initialize_instruments(port, addresses)
        self.max_flow = 1.5
        self.setpoints = {5: 0.0, 8: 0.0}  # Track setpoints

    def set_flow(self, address: int, flow: float) -> bool:
        try:
            percentage = (flow / self.max_flow) * 100
            value = int((percentage / 100.0) * 32000)
            self.instruments[address].writeParameter(9, value)
            self.setpoints[address] = flow  # Store setpoint
            return True
        except Exception as e:
            print(f"Error setting flow: {e}")
            return False

    def get_setpoint(self, address: int) -> float:
        return self.setpoints.get(address, 0.0)
    def calculate_flows(self, C_tot_ppm: float, C1_ppm: float, C2_ppm: float) -> Dict[str, float]:
        """Calculate required flows based on concentrations"""
        try:
            Q1, Q2 = calculate_flows_variable(C_tot_ppm, C1_ppm, C2_ppm)
            return {'Q1': Q1, 'Q2': Q2}
        except ValueError as e:
            raise ValueError(f"Flow calculation error: {e}")
        
    def get_readings(self, address: int) -> dict:
        """Get all readings from an instrument"""
        try:
            return {
                'Flow': self.read_flow(address),
                'Valve': self.read_valve(address),
                'Temperature': self.read_temperature(address)
            }
        except Exception as e:
            print(f"Error getting readings: {e}")
            return {'Flow': None, 'Valve': None, 'Temperature': None}
        
    def initialize_instruments(self, port: str, addresses: list) -> None:
        """Connect to all instruments"""
        for addr in addresses:
            try:
                self.instruments[addr] = propar.instrument(port, addr)
            except Exception as e:
                print(f"Error connecting to instrument {addr}: {e}")
    
    def read_flow(self, address: int) -> Optional[float]:
        """Read current flow in ln/min"""
        try:
            measure = self.instruments[address].read(33, 0, propar.PP_TYPE_FLOAT)
            return measure
        except Exception as e:
            print(f"Error reading flow: {e}")
            return None
    
    def read_valve(self, address: int) -> Optional[float]:
        """Read valve position in %"""
        try:
            valve = self.instruments[address].read(33, 1, propar.PP_TYPE_FLOAT)
            return valve
        except Exception as e:
            print(f"Error reading valve: {e}")
            return None
    
    def read_temperature(self, address: int) -> Optional[float]:
        """Read temperature in °C"""
        try:
            temp = self.instruments[address].read(33, 7, propar.PP_TYPE_FLOAT)
            return temp
        except Exception as e:
            print(f"Error reading temperature: {e}")
            return None
            
    def read_unit(self, address: int) -> str:
        """Read flow unit"""
        try:
            return self.instruments[address].readParameter(129)
        except:
            return "ln/min"
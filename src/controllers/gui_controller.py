from typing import Dict, Any
from src.models.calculations import calculate_flows_variable

class GUIController:
    """Controller handling GUI logic and flow calculations"""
    
    def __init__(self, flow_controller):
        self.flow_controller = flow_controller
        self.calculated_flows = {'Q1': 0.0, 'Q2': 0.0}
    
    def calculate_flows(self, C_tot_ppm: float, C1_ppm: float, C2_ppm: float) -> Dict[str, float]:
        """Calculate required flows based on concentrations"""
        try:
            Q1, Q2 = calculate_flows_variable(C_tot_ppm, C1_ppm, C2_ppm)
            self.calculated_flows = {'Q1': Q1, 'Q2': Q2}
            return self.calculated_flows
        except ValueError as e:
            raise ValueError(f"Flow calculation error: {e}")
    
    def set_direct_flow(self, address: int, flow: float) -> bool:
        """Set flow directly on instrument"""
        return self.flow_controller.set_flow(address, flow)
    
    def get_readings(self, address: int) -> Dict[str, Any]:
        """Get all readings from an instrument"""
        return {
            'flow': self.flow_controller.read_flow(address),
            'valve': self.flow_controller.read_valve(address),
            'temperature': self.flow_controller.read_temperature(address)
        }
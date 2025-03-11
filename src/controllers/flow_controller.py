import propar
from typing import Dict, Optional, Any, List
import time

from src.models.calculations import calculate_flows_variable

class FlowController:
    def __init__(self, port: str, addresses: list = None):
        self.port = port
        self.instruments = {}
        self.connected = False
        self.max_flow = 1.5
        self.setpoints = {}  # Track setpoints - will be populated when addresses are known
        
        # Only initialize with provided addresses
        if addresses and isinstance(addresses, list) and addresses[0] is not None:
            self.initialize_instruments(port, addresses)

    def initialize_instruments(self, port: str, addresses: list) -> None:
        """Initialize connections to instruments with known addresses"""
        try:
            if not addresses:
                print("No addresses provided for initialization")
                return
                
            for addr in addresses:
                if addr is not None:  # Skip None addresses
                    self.instruments[addr] = propar.instrument(port, addr)
                    # Test connection by reading a parameter
                    self.instruments[addr].readParameter(1)
                    # Initialize setpoint tracking
                    self.setpoints[addr] = 0.0
                    
            self.connected = True
        except Exception as e:
            print(f"Error connecting to instruments: {e}")
            self.connected = False
    
    def scan_for_instruments(self, start_addr=1, end_addr=24) -> List[int]:
        """Scan for instruments on the bus and return list of found addresses"""
        found_instruments = []
        
        print(f"Scanning for instruments from address {start_addr} to {end_addr}...")
        
        for addr in range(start_addr, end_addr + 1):
            try:
                # Create temporary instrument connection
                temp_instrument = propar.instrument(self.port, addr)
                
                # Try to read a parameter to verify it's responding
                value = temp_instrument.readParameter(1)
                if value is None:
                    raise Exception("No response")
                # If we get here without exception, we found an instrument
                found_instruments.append(addr)
                print(f"Found instrument at address {addr}")
                
                # Initialize this instrument in our instruments dict
                self.instruments[addr] = temp_instrument
                self.setpoints[addr] = 0.0
                
                # Small delay to prevent bus overload
                time.sleep(0.1)
            except Exception as e:
                # No instrument at this address
                print(f"No instrument at address {addr}: {e}")
                pass
        
        # Set connected flag if we found any instruments
        if found_instruments:
            self.connected = True
            print(f"Connected to {len(found_instruments)} instruments")
        else:
            self.connected = False
            print("No instruments found")
            
        return found_instruments

    def set_flow(self, address: int, flow: float) -> bool:
        """Set flow for a specific instrument"""
        try:
            percentage = (flow / self.max_flow) * 100
            value = int((percentage / 100.0) * 32000)
            self.instruments[address].writeParameter(9, value)
            self.setpoints[address] = flow  # Store setpoint
            return True
        except KeyError:
            print(f"Error: No instrument at address {address}")
            return False
        except Exception as e:
            print(f"Error setting flow: {e}")
            return False

    def get_setpoint(self, address: int) -> float:
        """Get the stored setpoint for a specific instrument"""
        return self.setpoints.get(address, 0.0)
        
    def calculate_flows(self, C_tot_ppm: float, C1_ppm: float, C2_ppm: float) -> Dict[str, float]:
        """Calculate required flows based on concentrations"""
        try:
            Q1, Q2 = calculate_flows_variable(C_tot_ppm, C1_ppm, C2_ppm)
            return {'Q1': Q1, 'Q2': Q2}
        except ValueError as e:
            raise ValueError(f"Flow calculation error: {e}")
        
    def get_readings(self, address: int) -> Dict[str, Any]:
        """Get all readings from an instrument"""
        try:
            readings = {
                'Flow': self.read_flow(address),
                'Valve': self.read_valve(address),
                'Temperature': self.read_temperature(address)
            }
            print(f"Debug - Readings for {address}: {readings}")  # Debug print
            return readings
        except Exception as e:
            print(f"Error getting readings: {e}")
            return {'Flow': None, 'Valve': None, 'Temperature': None}
            
    def is_connected(self) -> bool:
        """Check if we have active instrument connections"""
        return self.connected and bool(self.instruments)

    def read_flow(self, address: int) -> Optional[float]:
        """Read current flow in ln/min"""
        try:
            measure = self.instruments[address].read(33, 0, propar.PP_TYPE_FLOAT)
            return measure
        except Exception as e:
            print(f"Error reading flow: {address}")
            return None
    
    def read_valve(self, address: int) -> Optional[float]:
        """Read valve position in %"""
        try:
            valve = self.instruments[address].read(33, 1, propar.PP_TYPE_FLOAT)
            return valve
        except Exception as e:
            print(f"Error reading valve: {address}")
            return None
    
    def read_temperature(self, address: int) -> Optional[float]:
        """Read temperature in °C"""
        try:
            temp = self.instruments[address].read(33, 7, propar.PP_TYPE_FLOAT)
            return temp
        except Exception as e:
            print(f"Error reading temperature: {address}")
            return None
            
    def read_unit(self, address: int) -> str:
        """Read flow unit"""
        try:
            return self.instruments[address].readParameter(129)
        except:
            return "ln/min"
import propar
from typing import Dict, Optional, Any, List
import time

from src.models.calculations import calculate_flows_variable

KNOWN_FLOW_RANGES = {
    8: (0.13604, 10, "mln/min"),
    3: (0.012023, 1.5, "ln/min"),
    5: (1.233, 150, "mln/min"),
    10: (0.000856, 2.5, "ln/min"),  # Helium: 0.856-2500 mL/min = 0.000856-2.5 L/min
    20: (0.012023, 1.5, "ln/min"),
}

# MFC Uncertainty specifications (based on ±0.5%Rd + ±0.1%FS)
# Format: {address: {'Rd': reading_error_percent, 'FS': full_scale_error_percent}}
MFC_UNCERTAINTIES = {
    8: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 10.0, 'unit': 'mln/min'},      # Low flow: 10 mL/min max
    3: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 1500.0, 'unit': 'mln/min'},    # High flow: 1500 mL/min max
    5: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 150.0, 'unit': 'mln/min'},     # Medium flow: 150 mL/min max
    10: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 2500.0, 'unit': 'mln/min'},   # Helium: 2500 mL/min max
    20: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 1500.0, 'unit': 'mln/min'},   # Base gas (air): 1500 mL/min max
}

class FlowController:
    def __init__(self, port: str = None, addresses: list = None):
        self.port = port
        self.instruments = {}
        self.connected = False
        self.max_flows = {}
        self.setpoints = {}  # Track setpoints - will be populated when addresses are known
        self.units = {}       # Dictionnaire pour stocker l'unité de chaque instrument
        self.max_flows = {}   # Dictionnaire pour stocker le débit max de chaque instrument
        
        # Only initialize with provided addresses if port is also known
        if port and addresses and isinstance(addresses, list) and addresses[0] is not None:
            self.initialize_instruments(port, addresses)

    def get_port(self) -> Optional[str]:
        """Gets the current COM port."""
        return self.port

    def set_port(self, port: str):
        """Sets the COM port for the connection. If the port changes, it resets the connection."""
        if self.port != port:
            self.port = port
            self.connected = False
            self.instruments = {}
            print(f"Flow controller port set to {self.port}. Connection reset.")
        else:
            self.port = port

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
        
        if not self.port:
            print("Error: COM port not set. Cannot scan for instruments.")
            return []

        print(f"Scanning for instruments from address {start_addr} to {end_addr} on port {self.port}...")
        
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
                
                # Read and store the unit for this instrument
                try:
                    self.units[addr] = temp_instrument.readParameter(129).strip()
                    if self.units[addr] == "mln/min":
                        self.units[addr] = "ml/min"
                except Exception as e:
                    print(f"Could not read unit for instrument {addr}: {e}")
                    # Fallback to known unit if available
                    if addr in KNOWN_FLOW_RANGES:
                        _, _, self.units[addr] = KNOWN_FLOW_RANGES[addr]
                    else:
                        self.units[addr] = "ln/min"
                
                # Set max flow from KNOWN_FLOW_RANGES (more reliable than reading from device)
                if addr in KNOWN_FLOW_RANGES:
                    _, self.max_flows[addr], _ = KNOWN_FLOW_RANGES[addr]
                    print(f"Set max flow for address {addr}: {self.max_flows[addr]} {self.units[addr]}")
                else:
                    # Try to read max flow from instrument if not in known ranges
                    try:
                        # Parameter 21 typically contains the max flow capacity
                        max_flow_reading = temp_instrument.readParameter(21)
                        if max_flow_reading and max_flow_reading > 0:
                            self.max_flows[addr] = max_flow_reading
                        else:
                            self.max_flows[addr] = 1.5  # Default fallback
                    except:
                        self.max_flows[addr] = 1.5  # Default fallback
                    print(f"Set max flow for address {addr}: {self.max_flows[addr]} {self.units[addr]} (not in known ranges)")

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
            max_flow = self.max_flows.get(address, 1.5) # Default to 1.5 if not set
            percentage = (flow / max_flow) * 100
            value = int((percentage / 100.0) * 32000)
            self.instruments[address].writeParameter(9, value)
            self.setpoints[address] = flow  # Store setpoint
            print(f"Debug - Set flow for address {address}: Flow={flow}, Max Flow={max_flow}, Value={value}")
            return True
        except KeyError:
            print(f"Error: No instrument at address {address}")
            return False
        except Exception as e:
            print(f"Error setting flow: {e}")
            return False

    def get_instrument_metadata(self, address: int = None) -> Dict[str, Any]:
        """Returns stored metadata for an instrument or all instruments.
        
        Args:
            address: If provided, returns metadata for that specific instrument.
                    If None, returns metadata for all instruments.
        
        Returns:
            If address is provided: {'unit': str, 'max_flow': float, 'min_flow': float}
            If address is None: {address: {'unit': str, 'max_flow': float, 'min_flow': float}, ...}
        """
        if address is not None:
            # Get min_flow from KNOWN_FLOW_RANGES if available
            min_flow, max_flow_range, _ = KNOWN_FLOW_RANGES.get(address, (0.0, None, None))
            return {
                'unit': self.units.get(address, 'N/A'),
                'max_flow': self.max_flows.get(address, 0.0),
                'min_flow': min_flow
            }
        else:
            # Return metadata for all instruments
            all_metadata = {}
            for addr in self.instruments.keys():
                min_flow, max_flow_range, _ = KNOWN_FLOW_RANGES.get(addr, (0.0, None, None))
                all_metadata[addr] = {
                    'unit': self.units.get(addr, 'N/A'),
                    'max_flow': self.max_flows.get(addr, 0.0),
                    'min_flow': min_flow
                }
            return all_metadata

    def get_setpoint(self, address: int) -> float:
        """Get the stored setpoint for a specific instrument"""
        return self.setpoints.get(address, 0.0)
    
    def calculate_flows(self, C_tot_ppm: float, C1_ppm: float, C2_ppm: float, max_flow: float = 1.5) -> Dict[str, float]:
        """Calculate required flows based on concentrations and adjust for units"""
        try:
            # Calculate flows in ln/min
            Q1, Q2 = calculate_flows_variable(C_tot_ppm, C1_ppm, C2_ppm)
            
            # Scale flows based on max_flow
            Q1 = min(Q1, max_flow)
            Q2 = min(Q2, max_flow)
            
            # Adjust flows based on the unit of each instrument
            flows = {}
            for addr, flow in zip(self.instruments.keys(), [Q1, Q2]):
                unit = self.read_unit(addr)
                if unit == "ml/min":
                    flows[f"Q{addr}"] = flow * 1000  # Convert ln/min to ml/min
                else:
                    flows[f"Q{addr}"] = flow  # Keep as ln/min

            return flows
        except ValueError as e:
            raise ValueError(f"Flow calculation error: {e}")
            
    def get_readings(self, address: int) -> Dict[str, Any]:
        """Get all readings from an instrument, including the unit"""
        try:
            # Use cached unit instead of reading it every time
            unit = self.units.get(address, "ln/min")
            
            readings = {
                'Flow': self.read_flow(address),
                'Valve': self.read_valve(address),
                'Temperature': self.read_temperature(address),
                'Unit': unit
            }
            return readings
        except Exception as e:
            print(f"Error getting readings from address {address}: {e}")
            return {'Flow': None, 'Valve': None, 'Temperature': None, 'Unit': "ln/min"}
            
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
        """Read flow unit from cache (faster) or from instrument if not cached"""
        # First try to get from cache
        if address in self.units:
            return self.units[address]
        
        # If not cached, read from instrument and cache it
        try:
            unit = self.instruments[address].readParameter(129).strip()
            if unit == "mln/min":
                unit = "ml/min"  # Normalize unit
            self.units[address] = unit  # Cache it
            return unit
        except:
            return "ln/min"

    def start_all(self):
        """Set flow to the stored setpoint for all instruments."""
        for addr, setpoint in self.setpoints.items():
            self.set_flow(addr, setpoint)
            time.sleep(0.1) # Small delay between commands

    def stop_all(self):
        """Set flow to 0 for all instruments."""
        for addr in self.instruments.keys():
            self.set_flow(addr, 0)
            time.sleep(0.1) # Small delay between commands


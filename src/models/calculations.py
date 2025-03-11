from typing import Tuple, Optional

def calculate_flows_variable(C_tot_ppm: float, C1_ppm: float, C2_ppm: float, 
                           Q_max_individual: float = 1.5) -> Tuple[float, float]:
    """Calculate required flow rates for desired concentration."""
    # Convert ppm to fractional concentrations
    C_tot = C_tot_ppm / 1_000_000
    C1 = C1_ppm / 1_000_000
    C2 = C2_ppm / 1_000_000

    # Validate inputs
    if C_tot > max(C1, C2):
        raise ValueError("Cannot achieve higher concentration than source gases")
    if C1 == C2:
        raise ValueError("Gas concentrations must be different")

    # Calculate flow ratios
    Q1_ratio = (C_tot - C2) / (C1 - C2)
    Q2_ratio = 1 - Q1_ratio

    # Scale flows to maximum allowed individual flow
    scaling_factor = Q_max_individual / max(Q1_ratio, Q2_ratio)
    Q1 = Q1_ratio * scaling_factor
    Q2 = Q2_ratio * scaling_factor

    # Verify solution exists within constraints
    if Q1 < 0 or Q2 < 0 or Q1 > Q_max_individual or Q2 > Q_max_individual:
        raise ValueError("No solution exists within flow constraints")

    return Q1, Q2

def calculate_real_outflow(C1, V1, C2, V2):
    """Calculate the final concentration based on input concentrations and flow rates.
    
    Args:
        C1: Concentration of first gas (ppm)
        V1: Flow rate of first gas (ln/min)
        C2: Concentration of second gas (ppm)
        V2: Flow rate of second gas (ln/min)
        
    Returns:
        Final concentration (ppm) or 0 if inputs are invalid
    """
    # Check for None or invalid values
    if None in (C1, V1, C2, V2) or (V1 + V2) == 0:
        return 0
    
    C_final = (C1*V1 + C2*V2)/(V1+V2)
    return C_final
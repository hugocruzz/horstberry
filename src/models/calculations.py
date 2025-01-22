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
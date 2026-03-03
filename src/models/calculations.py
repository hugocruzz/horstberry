from typing import Tuple

def calculate_flows_variable(C_tot_ppm: float, C1_ppm: float, C2_ppm: float, 
                           Q_max_individual: float = 1.5) -> Tuple[float, float]:
    """Calculate required flow rates for desired concentration.

    Returns (Q1, Q2) where Q1 corresponds to gas with concentration C1_ppm and
    Q2 corresponds to gas with concentration C2_ppm.

    This helper scales flows so that neither exceeds Q_max_individual.
    It does NOT enforce a specific total flow.
    """
    # Convert ppm to fractional concentrations
    C_tot = C_tot_ppm / 1_000_000
    C1 = C1_ppm / 1_000_000
    C2 = C2_ppm / 1_000_000

    # Validate inputs
    c_min = min(C1, C2)
    c_max = max(C1, C2)
    if C_tot < c_min:
        raise ValueError(
            f"Cannot achieve a concentration below the lowest source gas ({c_min*1_000_000:.3f} ppm)"
        )
    if C_tot > c_max:
        raise ValueError(
            f"Cannot achieve a concentration above the highest source gas ({c_max*1_000_000:.3f} ppm)"
        )
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


def calculate_flows_for_total_flow(
    C_tot_ppm: float,
    C1_ppm: float,
    C2_ppm: float,
    Q_total: float,
) -> Tuple[float, float]:
    """Calculate flows that achieve C_tot_ppm with a fixed total flow.

    Returns (Q1, Q2) such that Q1 + Q2 == Q_total.
    """
    if Q_total < 0:
        raise ValueError("Total flow must be non-negative")
    if Q_total == 0:
        return 0.0, 0.0

    # Convert ppm to fractional concentrations
    C_tot = C_tot_ppm / 1_000_000
    C1 = C1_ppm / 1_000_000
    C2 = C2_ppm / 1_000_000

    c_min = min(C1, C2)
    c_max = max(C1, C2)
    if C_tot < c_min:
        raise ValueError(
            f"Cannot achieve a concentration below the lowest source gas ({c_min*1_000_000:.3f} ppm)"
        )
    if C_tot > c_max:
        raise ValueError(
            f"Cannot achieve a concentration above the highest source gas ({c_max*1_000_000:.3f} ppm)"
        )
    if C1 == C2:
        raise ValueError("Gas concentrations must be different")

    # Solve: C_tot = (C1*Q1 + C2*Q2) / (Q1 + Q2), with Q1+Q2=Q_total
    # => Q1 = Q_total * (C_tot - C2) / (C1 - C2)
    q1_ratio = (C_tot - C2) / (C1 - C2)
    q2_ratio = 1.0 - q1_ratio
    Q1 = Q_total * q1_ratio
    Q2 = Q_total * q2_ratio

    if Q1 < -1e-12 or Q2 < -1e-12:
        raise ValueError("No solution exists within flow constraints")

    # Clamp tiny negatives due to floating point
    Q1 = max(0.0, Q1)
    Q2 = max(0.0, Q2)
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
"""
Uncertainty calculation module for MFC flow measurements and concentration propagation.

Based on Bronkhorst MFC specifications: ±0.5%Rd + ±0.1%FS
where Rd = reading (actual flow), FS = full scale (maximum flow)
"""

import numpy as np
from typing import Tuple, Dict, Optional

# MFC Uncertainty specifications
MFC_UNCERTAINTIES = {
    8: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 10.0, 'unit': 'mln/min'},      # Low flow
    3: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 1500.0, 'unit': 'mln/min'},    # High flow
    5: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 150.0, 'unit': 'mln/min'},     # Medium flow
    10: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 2500.0, 'unit': 'mln/min'},   # Helium
    20: {'Rd': 0.5, 'FS': 0.1, 'FS_value': 1500.0, 'unit': 'mln/min'},   # Base gas (air)
}


def calculate_flow_uncertainty(flow_mln_min: float, address: int) -> float:
    """
    Calculate the uncertainty of a flow measurement in mln/min.
    
    Formula: u = ±(0.5% × Reading + 0.1% × Full_Scale)
    
    Args:
        flow_mln_min: Flow reading in mln/min
        address: Instrument address to determine uncertainty specs
        
    Returns:
        Uncertainty in mln/min (1-sigma)
    """
    if address not in MFC_UNCERTAINTIES:
        # Default uncertainty if address not known
        return flow_mln_min * 0.01  # 1% default
    
    specs = MFC_UNCERTAINTIES[address]
    
    # Calculate uncertainty: u = (Rd% × Reading) + (FS% × Full_Scale)
    u_reading = (specs['Rd'] / 100.0) * abs(flow_mln_min)
    u_fullscale = (specs['FS'] / 100.0) * specs['FS_value']
    
    uncertainty = u_reading + u_fullscale
    
    return uncertainty


def convert_flow_to_mln_min(flow: float, unit: str) -> float:
    """Convert flow to mln/min for uncertainty calculations."""
    if unit == "ln/min":
        return flow * 1000.0  # L/min to mL/min
    elif unit in ("ml/min", "mln/min"):
        return flow
    else:
        return flow  # Assume mln/min if unknown


def propagate_concentration_uncertainty(
    C1_ppm: float, 
    F1_mln_min: float, 
    C2_ppm: float, 
    F2_mln_min: float,
    addr1: int,
    addr2: int
) -> Tuple[float, Dict[str, float]]:
    """
    Propagate flow uncertainties to concentration uncertainty.
    
    Formula for concentration: C = (C1×F1 + C2×F2) / (F1 + F2)
    
    Using partial derivatives:
    ∂C/∂F1 = (C1×(F1+F2) - (C1×F1+C2×F2)) / (F1+F2)² = (C1×F2 - C2×F2) / (F1+F2)²
    ∂C/∂F2 = (C2×(F1+F2) - (C1×F1+C2×F2)) / (F1+F2)² = (C2×F1 - C1×F1) / (F1+F2)²
    
    Args:
        C1_ppm: Concentration of gas 1 in ppm
        F1_mln_min: Flow of gas 1 in mln/min
        C2_ppm: Concentration of gas 2 in ppm
        F2_mln_min: Flow of gas 2 in mln/min
        addr1: Address of MFC 1
        addr2: Address of MFC 2
        
    Returns:
        (uncertainty_ppm, details_dict) where details_dict contains:
            - 'u_C': concentration uncertainty in ppm
            - 'u_F1': flow 1 uncertainty in mln/min
            - 'u_F2': flow 2 uncertainty in mln/min
            - 'dC_dF1': sensitivity to flow 1 (ppm per mln/min)
            - 'dC_dF2': sensitivity to flow 2 (ppm per mln/min)
            - 'C_expected': expected concentration in ppm
    """
    # Calculate flow uncertainties
    u_F1 = calculate_flow_uncertainty(F1_mln_min, addr1)
    u_F2 = calculate_flow_uncertainty(F2_mln_min, addr2)
    
    # Calculate expected concentration
    F_total = F1_mln_min + F2_mln_min
    if F_total == 0:
        return 0.0, {
            'u_C': 0.0, 'u_F1': u_F1, 'u_F2': u_F2,
            'dC_dF1': 0.0, 'dC_dF2': 0.0, 'C_expected': 0.0
        }
    
    C_expected = (C1_ppm * F1_mln_min + C2_ppm * F2_mln_min) / F_total
    
    # Calculate partial derivatives (sensitivity coefficients)
    # ∂C/∂F1 = (C1 - C2) × F2 / (F1 + F2)²
    dC_dF1 = (C1_ppm - C2_ppm) * F2_mln_min / (F_total ** 2)
    
    # ∂C/∂F2 = (C2 - C1) × F1 / (F1 + F2)²
    dC_dF2 = (C2_ppm - C1_ppm) * F1_mln_min / (F_total ** 2)
    
    # Propagate uncertainty (assuming independent errors)
    # u_C² = (∂C/∂F1)² × u_F1² + (∂C/∂F2)² × u_F2²
    u_C_squared = (dC_dF1 ** 2) * (u_F1 ** 2) + (dC_dF2 ** 2) * (u_F2 ** 2)
    u_C = np.sqrt(u_C_squared)
    
    details = {
        'u_C': u_C,
        'u_F1': u_F1,
        'u_F2': u_F2,
        'dC_dF1': dC_dF1,
        'dC_dF2': dC_dF2,
        'C_expected': C_expected
    }
    
    return u_C, details


def calculate_required_flow_with_uncertainty(
    C_target_ppm: float,
    C1_ppm: float,
    F1_mln_min: float,
    C2_ppm: float,
    addr1: int,
    addr2: int
) -> Dict[str, float]:
    """
    Calculate the required F2 to achieve target concentration, 
    and compute the uncertainty on the achieved concentration.
    
    Formula: F2 = F1 × (C_target - C1) / (C2 - C_target)
    
    Args:
        C_target_ppm: Target concentration in ppm
        C1_ppm: Concentration of gas 1 (typically diluent) in ppm
        F1_mln_min: Flow of gas 1 in mln/min
        C2_ppm: Concentration of gas 2 (source gas) in ppm
        addr1: Address of MFC 1
        addr2: Address of MFC 2
        
    Returns:
        Dictionary with:
            - 'F2_required': Required flow for gas 2 in mln/min
            - 'u_C': Concentration uncertainty in ppm
            - 'u_F1': Flow 1 uncertainty in mln/min
            - 'u_F2': Flow 2 uncertainty in mln/min
            - 'C_achieved': Expected concentration in ppm
            - 'relative_error': Relative error as percentage
    """
    # Calculate required F2
    if (C2_ppm - C_target_ppm) == 0:
        return {
            'F2_required': 0.0, 'u_C': 0.0, 'u_F1': 0.0, 'u_F2': 0.0,
            'C_achieved': 0.0, 'relative_error': 0.0
        }
    
    F2_required = F1_mln_min * (C_target_ppm - C1_ppm) / (C2_ppm - C_target_ppm)
    
    # Propagate uncertainty
    u_C, details = propagate_concentration_uncertainty(
        C1_ppm, F1_mln_min, C2_ppm, F2_required, addr1, addr2
    )
    
    relative_error = (u_C / C_target_ppm * 100.0) if C_target_ppm > 0 else 0.0
    
    return {
        'F2_required': F2_required,
        'u_C': u_C,
        'u_F1': details['u_F1'],
        'u_F2': details['u_F2'],
        'C_achieved': C_target_ppm,  # This is the target
        'relative_error': relative_error,
        'dC_dF1': details['dC_dF1'],
        'dC_dF2': details['dC_dF2']
    }


def format_uncertainty_string(value: float, uncertainty: float, unit: str = "") -> str:
    """
    Format a value with its uncertainty in scientific notation if needed.
    
    Args:
        value: The measured/calculated value
        uncertainty: The uncertainty (1-sigma)
        unit: Optional unit string
        
    Returns:
        Formatted string like "100.0 ± 0.8 ppm" or "10.20 ± 0.01 mL/min"
    """
    if abs(value) < 0.01 or abs(value) > 10000:
        # Use scientific notation
        return f"{value:.3e} ± {uncertainty:.2e} {unit}".strip()
    elif abs(value) < 1:
        return f"{value:.4f} ± {uncertainty:.4f} {unit}".strip()
    elif abs(value) < 10:
        return f"{value:.3f} ± {uncertainty:.3f} {unit}".strip()
    elif abs(value) < 100:
        return f"{value:.2f} ± {uncertainty:.2f} {unit}".strip()
    else:
        return f"{value:.1f} ± {uncertainty:.1f} {unit}".strip()

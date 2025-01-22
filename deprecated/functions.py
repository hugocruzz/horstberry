def calculate_times(Q1, Q2, V_tank, C_tank_ppm, C1_ppm, C2_ppm):
    """
    Calculate the times t1 and t2 required to achieve the desired methane concentration.

    Parameters:
        Q1 (float): Flow rate of Gas1 (ln/min).
        Q2 (float): Flow rate of Gas2 (ln/min).
        V_tank (float): Tank volume (liters).
        C_tank_ppm (float): Desired methane concentration in the tank (ppm).
        C1_ppm (float): Methane concentration in Gas1 (ppm).

    Returns:
        t1 (float): Time Gas1 is open (minutes).
        t2 (float): Time Gas2 is open (minutes).
    """
    # Ensure inputs are valid
    if Q1 + Q2 <= 0:
        raise ValueError("Total flow (Q1 + Q2) must be greater than 0.")
    if C1_ppm <= 0:
        raise ValueError("Methane concentration in Gas1 (C1_ppm) must be greater than 0.")

    # Convert ppm to fractional concentrations
    C_tank = C_tank_ppm / 1_000_000
    C1 = C1_ppm / 1_000_000
    C2 = C2_ppm / 1_000_000

    # Total flow rate
    Q_total = Q1 + Q2

    # Total time to fill the tank
    total_time = V_tank / Q_total

    # Calculate t1 based on methane concentration requirement
    t1 = (C_tank * V_tank - C2 * Q2 * total_time) / (C1 * Q1)

    # Calculate t2 as the remaining time
    t2 = total_time - t1

    # Validate results
    if t1 < 0 or t2 < 0:
        raise ValueError("Calculated times are invalid. Check the input values.")

    return t1, t2


def calculate_flows_variable(C_tot_ppm, C1_ppm, C2_ppm, Q_max_individual=1.5):
    """
    Calculate flow rates Q1 and Q2 to achieve the desired concentration with constraints.

    Parameters:
        C_tot_ppm (float): Desired methane concentration in the output (ppm).
        C1_ppm (float): Methane concentration in Gas1 (ppm).
        C2_ppm (float): Methane concentration in Gas2 (ppm).
        Q_max_individual (float): Maximum flow rate for each gas (ln/min).

    Returns:
        Q1 (float): Flow rate of Gas1 (ln/min).
        Q2 (float): Flow rate of Gas2 (ln/min).
    """
    # Convert ppm to fractional concentrations
    C_tot = C_tot_ppm / 1_000_000
    C1 = C1_ppm / 1_000_000
    C2 = C2_ppm / 1_000_000

    # Check feasibility of desired concentration
    if C_tot > max(C1, C2) or C_tot < min(C1, C2):
        raise ValueError("Desired concentration is not achievable with given gas concentrations.")
    if C1 == C2:
        raise ValueError("Methane concentrations in Gas1 and Gas2 must be different.")

    # Calculate flow ratios
    Q1_ratio = (C_tot - C2) / (C1 - C2)
    Q2_ratio = 1 - Q1_ratio

    # Scale flows to respect constraints
    Q1 = Q1_ratio * Q_max_individual
    Q2 = Q2_ratio * Q_max_individual

    # Validate results against individual flow constraints
    if Q1 > Q_max_individual or Q2 > Q_max_individual:
        # Scale flows proportionally if they exceed the maximum
        scaling_factor = Q_max_individual / max(Q1, Q2)
        Q1 *= scaling_factor
        Q2 *= scaling_factor

    # Ensure the result is valid
    if Q1 < 0 or Q2 < 0 or Q1 > Q_max_individual or Q2 > Q_max_individual:
        raise ValueError("No solution exists within the given constraints.")

    return Q1, Q2

if __name__ == "__main__":
    # Example usage:
    Q1 = 0.5  # Flow rate of Gas1 (ln/min)
    Q2 = 1.0  # Flow rate of Gas2 (ln/min)
    V_tank = 2000  # Tank volume (liters)
    C_tank_ppm = 10000  # Desired methane concentration in the tank (ppm)
    C1_ppm = 200000  # Methane concentration in Gas1 (ppm)

    t1, t2 = calculate_times(Q1, Q2, V_tank, C_tank_ppm, C1_ppm, C2_ppm=0)
    print(f"Time for Gas1 (t1): {t1:.2f} minutes")
    print(f"Time for Gas2 (t2): {t2:.2f} minutes")
        # Example usage:
    # Example usage:
    C_tot_ppm = 1000  # Desired methane concentration in the output (ppm)
    C1_ppm = 200000  # Methane concentration in Gas1 (ppm)
    C2_ppm = 0  # Methane concentration in Gas2 (ppm)

    Q1, Q2 = calculate_flows_variable(C_tot_ppm, C1_ppm, C2_ppm)
    print(f"Flow rate of Gas1 (Q1): {Q1:.2f} ln/min")
    print(f"Flow rate of Gas2 (Q2): {Q2:.2f} ln/min")

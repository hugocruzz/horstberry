"""
MFC Calibration Analysis Script

This script analyzes the calibration data from Test_MFCs_installation.txt to:
1. Determine if the offset is linear (multiplicative) or constant (additive)
2. Compare measurements across different locations and gases
3. Visualize the relationships between set and measured flows
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import curve_fit
import pandas as pd

# Parse the data from Test_MFCs_installation.txt
data = [
    # (Gas, Set_Flow, Measured_Flow, Location)
    ("Zero", 0, 0, "Table"),
    ("Air", 0.1, 0.114, "Table"),
    ("Air", 0.3, 0.342, "Table"),
    ("Air", 0.5, 0.575, "Table"),
    ("CH4", 0.3, 0.362, "Table"),
    ("CH4", 0.1, 0.120, "Table"),
    ("CH4", 0.1, 0.119, "Table"),  # medium MFC
    ("CH4", 0.01, 0.0116, "Table"),
    ("CH4", 0.02, 0.0237, "Table"),  # .01 (med)+0.01 (low)
    ("CH4", 0.001, 0.0017, "Table"),
    ("Mix", 0.6, 0.733, "Table"),  # 0.5+0.1
    ("Mix", 0.51, 0.592, "Table"),  # 0.5+0.01
    ("Mix", 0.501, 0.579, "Table"),  # 0.5+0.001
    ("Mix", 0.3, 0.362, "Table"),
    ("Mix", 0.4, 0.485, "Table"),  # 0.1+0.3 or 0.3+0.1
    ("He", 0.1, 0.114, "Table"),
    ("He", 0.5, 0.574, "Table"),
    ("Air", 0.1, 0.122, "Enceinte"),
    ("Air", 0.5, 0.615, "Enceinte"),
    ("He", 0.1, 0.115, "Enceinte"),  # =0.06 He actual
    ("He", 0.5, 0.574, "Enceinte"),  # =0.3 He actual
    ("Mix", 0.6, 0.737, "Enceinte"),  # 0.5+0.1
    ("Mix", 0.31, 0.377, "Enceinte"),  # 0.3+0.01
    ("Mix", 0.101, 0.124, "Enceinte"),  # 0.1+0.001
    ("He", 0.1, 0.115, "Pompe"),
    ("He", 0.5, 0.576, "Pompe"),
]

# Create DataFrame
df = pd.DataFrame(data, columns=["Gas", "Set_Flow", "Measured_Flow", "Location"])

print("="*80)
print("MFC CALIBRATION ANALYSIS")
print("="*80)
print(f"\nDataset contains {len(df)} measurements")
print(f"Gases tested: {', '.join(df['Gas'].unique())}")
print(f"Locations: {', '.join(df['Location'].unique())}")
print(f"Flow range: {df['Set_Flow'].min():.4f} - {df['Set_Flow'].max():.2f} L/min")
print("\n" + "="*80)

# Filter out zero flow for regression analysis
df_nonzero = df[df['Set_Flow'] > 0].copy()

# Linear model: y = a*x (multiplicative offset)
def linear_model(x, a):
    return a * x

# Affine model: y = a*x + b (additive offset)
def affine_model(x, a, b):
    return a * x + b

# Fit both models
x = df_nonzero['Set_Flow'].values
y = df_nonzero['Measured_Flow'].values

# Linear fit (forced through origin)
params_linear, _ = curve_fit(linear_model, x, y)
y_pred_linear = linear_model(x, *params_linear)
r2_linear = 1 - (np.sum((y - y_pred_linear)**2) / np.sum((y - np.mean(y))**2))
rmse_linear = np.sqrt(np.mean((y - y_pred_linear)**2))

# Affine fit
params_affine, _ = curve_fit(affine_model, x, y)
y_pred_affine = affine_model(x, *params_affine)
r2_affine = 1 - (np.sum((y - y_pred_affine)**2) / np.sum((y - np.mean(y))**2))
rmse_affine = np.sqrt(np.mean((y - y_pred_affine)**2))

print("\n1. OFFSET TYPE ANALYSIS")
print("-"*80)
print(f"\nLinear Model: y = {params_linear[0]:.4f} * x")
print(f"  R² = {r2_linear:.6f}")
print(f"  RMSE = {rmse_linear:.6f} L/min")
print(f"  Interpretation: Measured flow is {params_linear[0]:.2%} of set flow")

print(f"\nAffine Model: y = {params_affine[0]:.4f} * x + {params_affine[1]:.6f}")
print(f"  R² = {r2_affine:.6f}")
print(f"  RMSE = {rmse_affine:.6f} L/min")
print(f"  Interpretation: {params_affine[0]:.2%} scaling + {params_affine[1]*1000:.3f} mL/min offset")

print(f"\n{'='*80}")
if abs(params_affine[1]) < 0.005 or r2_linear > 0.999:
    print("CONCLUSION: Offset is MULTIPLICATIVE (linear through origin)")
    print(f"The flowmeter reads approximately {params_linear[0]:.2%} of the actual flow.")
elif r2_affine - r2_linear > 0.001:
    print("CONCLUSION: Offset has both MULTIPLICATIVE and ADDITIVE components")
    print(f"There's a {params_affine[1]*1000:.3f} mL/min constant offset plus {params_affine[0]:.2%} scaling.")
else:
    print("CONCLUSION: Offset is primarily MULTIPLICATIVE with negligible constant term")
print(f"{'='*80}\n")

# Analysis by location
print("\n2. ANALYSIS BY LOCATION")
print("-"*80)
for location in df['Location'].unique():
    df_loc = df_nonzero[df_nonzero['Location'] == location]
    if len(df_loc) > 0:
        x_loc = df_loc['Set_Flow'].values
        y_loc = df_loc['Measured_Flow'].values
        params_loc, _ = curve_fit(linear_model, x_loc, y_loc)
        r2_loc = 1 - (np.sum((y_loc - linear_model(x_loc, *params_loc))**2) / 
                      np.sum((y_loc - np.mean(y_loc))**2))
        print(f"\n{location}:")
        print(f"  Scaling factor: {params_loc[0]:.4f} (R² = {r2_loc:.4f})")
        print(f"  Number of measurements: {len(df_loc)}")

# Analysis by gas type
print("\n\n3. ANALYSIS BY GAS TYPE")
print("-"*80)
for gas in sorted(df['Gas'].unique()):
    df_gas = df_nonzero[df_nonzero['Gas'] == gas]
    if len(df_gas) > 2:
        x_gas = df_gas['Set_Flow'].values
        y_gas = df_gas['Measured_Flow'].values
        params_gas, _ = curve_fit(linear_model, x_gas, y_gas)
        r2_gas = 1 - (np.sum((y_gas - linear_model(x_gas, *params_gas))**2) / 
                      np.sum((y_gas - np.mean(y_gas))**2))
        print(f"\n{gas}:")
        print(f"  Scaling factor: {params_gas[0]:.4f} (R² = {r2_gas:.4f})")
        print(f"  Number of measurements: {len(df_gas)}")

# Check for redundant measurements (same flow, different conditions)
print("\n\n4. REDUNDANT MEASUREMENTS CONSISTENCY CHECK")
print("-"*80)

# Define tolerance for "same" flow
tolerance = 0.05

# Group by approximate flow values
flow_groups = {}
for _, row in df_nonzero.iterrows():
    # Find or create group
    found_group = False
    for flow_val in flow_groups.keys():
        if abs(row['Set_Flow'] - flow_val) < tolerance:
            flow_groups[flow_val].append(row)
            found_group = True
            break
    if not found_group:
        flow_groups[row['Set_Flow']] = [row]

# Report on groups with multiple measurements
print("\nFlow settings with multiple measurements:")
for flow_val in sorted(flow_groups.keys()):
    group = flow_groups[flow_val]
    if len(group) > 1:
        print(f"\nSet flow ≈ {flow_val:.3f} L/min ({len(group)} measurements):")
        for item in group:
            print(f"  {item['Gas']:8s} @ {item['Location']:10s}: "
                  f"Set={item['Set_Flow']:.4f}, Measured={item['Measured_Flow']:.4f}")
        
        measured_values = [item['Measured_Flow'] for item in group]
        std_dev = np.std(measured_values)
        mean_val = np.mean(measured_values)
        cv = (std_dev / mean_val * 100) if mean_val > 0 else 0
        print(f"  → Measured flow: mean={mean_val:.4f}, std={std_dev:.4f}, CV={cv:.2f}%")

# Create visualizations
print("\n\n5. GENERATING PLOTS...")
print("-"*80)

# Define colors for locations
location_colors = {
    'Table': '#2E86AB',      # Blue
    'Enceinte': '#A23B72',   # Purple
    'Pompe': '#F18F01'       # Orange
}

# Define markers for gases
gas_markers = {
    'Zero': 'X',
    'Air': 'o',
    'CH4': 's',
    'Mix': '^',
    'He': 'D'
}

# Plot 1: Overall calibration with both models
fig1, ax1 = plt.subplots(figsize=(12, 8))

for location in df['Location'].unique():
    for gas in df['Gas'].unique():
        df_subset = df[(df['Location'] == location) & (df['Gas'] == gas)]
        if len(df_subset) > 0:
            ax1.scatter(df_subset['Set_Flow'], df_subset['Measured_Flow'],
                       c=location_colors[location], marker=gas_markers[gas],
                       s=100, alpha=0.7, edgecolors='black', linewidth=1,
                       label=f'{gas} @ {location}')

# Plot regression lines
x_range = np.linspace(0, df_nonzero['Set_Flow'].max(), 100)
ax1.plot(x_range, linear_model(x_range, *params_linear),
         'r--', linewidth=2, label=f'Linear: y={params_linear[0]:.3f}x (R²={r2_linear:.4f})')
ax1.plot(x_range, affine_model(x_range, *params_affine),
         'g:', linewidth=2, label=f'Affine: y={params_affine[0]:.3f}x+{params_affine[1]:.3f} (R²={r2_affine:.4f})')
ax1.plot([0, df['Set_Flow'].max()], [0, df['Set_Flow'].max()],
         'k-', linewidth=1, alpha=0.3, label='Ideal (y=x)')

ax1.set_xlabel('Set Flow (L/min)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Measured Flow (L/min)', fontsize=12, fontweight='bold')
ax1.set_title('MFC Calibration: Set vs Measured Flow', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
plt.tight_layout()
plt.savefig('c:/Users/cruz/Documents/SENSE/horstberry/scripts/mfc_calibration_overall.png', dpi=300, bbox_inches='tight')
print("  ✓ Saved: mfc_calibration_overall.png")

# Plot 2: By location
fig2, axes = plt.subplots(1, 3, figsize=(18, 6))

for idx, location in enumerate(sorted(df['Location'].unique())):
    ax = axes[idx]
    df_loc = df[df['Location'] == location]
    df_loc_nonzero = df_loc[df_loc['Set_Flow'] > 0]
    
    for gas in df['Gas'].unique():
        df_subset = df_loc[df_loc['Gas'] == gas]
        if len(df_subset) > 0:
            ax.scatter(df_subset['Set_Flow'], df_subset['Measured_Flow'],
                      marker=gas_markers[gas], s=120, alpha=0.7,
                      edgecolors='black', linewidth=1, label=gas)
    
    if len(df_loc_nonzero) > 0:
        x_loc = df_loc_nonzero['Set_Flow'].values
        y_loc = df_loc_nonzero['Measured_Flow'].values
        params_loc, _ = curve_fit(linear_model, x_loc, y_loc)
        x_range_loc = np.linspace(0, x_loc.max(), 100)
        ax.plot(x_range_loc, linear_model(x_range_loc, *params_loc),
                'r--', linewidth=2, label=f'Fit: y={params_loc[0]:.3f}x')
    
    ax.plot([0, df_loc['Set_Flow'].max()], [0, df_loc['Set_Flow'].max()],
            'k-', linewidth=1, alpha=0.3, label='Ideal')
    
    ax.set_xlabel('Set Flow (L/min)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Measured Flow (L/min)', fontsize=11, fontweight='bold')
    ax.set_title(f'{location}', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig('c:/Users/cruz/Documents/SENSE/horstberry/scripts/mfc_calibration_by_location.png', dpi=300)
print("  ✓ Saved: mfc_calibration_by_location.png")

# Plot 3: Residuals analysis
fig3, axes = plt.subplots(2, 2, figsize=(14, 10))

# Residuals vs Set Flow - Linear model
ax = axes[0, 0]
residuals_linear = y - y_pred_linear
for location in df_nonzero['Location'].unique():
    mask = df_nonzero['Location'] == location
    ax.scatter(x[mask], residuals_linear[mask], 
              c=location_colors[location], s=80, alpha=0.7,
              label=location, edgecolors='black', linewidth=0.5)
ax.axhline(y=0, color='k', linestyle='--', linewidth=1)
ax.set_xlabel('Set Flow (L/min)', fontweight='bold')
ax.set_ylabel('Residual (L/min)', fontweight='bold')
ax.set_title('Residuals - Linear Model', fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend()

# Residuals vs Set Flow - Affine model
ax = axes[0, 1]
residuals_affine = y - y_pred_affine
for location in df_nonzero['Location'].unique():
    mask = df_nonzero['Location'] == location
    ax.scatter(x[mask], residuals_affine[mask],
              c=location_colors[location], s=80, alpha=0.7,
              label=location, edgecolors='black', linewidth=0.5)
ax.axhline(y=0, color='k', linestyle='--', linewidth=1)
ax.set_xlabel('Set Flow (L/min)', fontweight='bold')
ax.set_ylabel('Residual (L/min)', fontweight='bold')
ax.set_title('Residuals - Affine Model', fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend()

# Histogram of residuals - Linear
ax = axes[1, 0]
ax.hist(residuals_linear, bins=15, edgecolor='black', alpha=0.7)
ax.axvline(x=0, color='r', linestyle='--', linewidth=2)
ax.set_xlabel('Residual (L/min)', fontweight='bold')
ax.set_ylabel('Count', fontweight='bold')
ax.set_title(f'Residual Distribution - Linear (RMSE={rmse_linear:.4f})', fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

# Histogram of residuals - Affine
ax = axes[1, 1]
ax.hist(residuals_affine, bins=15, edgecolor='black', alpha=0.7, color='green')
ax.axvline(x=0, color='r', linestyle='--', linewidth=2)
ax.set_xlabel('Residual (L/min)', fontweight='bold')
ax.set_ylabel('Count', fontweight='bold')
ax.set_title(f'Residual Distribution - Affine (RMSE={rmse_affine:.4f})', fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('c:/Users/cruz/Documents/SENSE/horstberry/scripts/mfc_calibration_residuals.png', dpi=300)
print("  ✓ Saved: mfc_calibration_residuals.png")

# Plot 4: Error percentage analysis
fig4, ax4 = plt.subplots(figsize=(12, 8))

error_pct = ((y - x) / x * 100)

for location in df_nonzero['Location'].unique():
    mask = df_nonzero['Location'].values == location
    ax4.scatter(x[mask], error_pct[mask],
               c=location_colors[location], s=100, alpha=0.7,
               label=location, edgecolors='black', linewidth=1)

ax4.axhline(y=0, color='k', linestyle='-', linewidth=1, alpha=0.5)
ax4.axhline(y=np.mean(error_pct), color='r', linestyle='--', linewidth=2,
           label=f'Mean error: {np.mean(error_pct):.2f}%')

ax4.set_xlabel('Set Flow (L/min)', fontsize=12, fontweight='bold')
ax4.set_ylabel('Measurement Error (%)', fontsize=12, fontweight='bold')
ax4.set_title('Percentage Error vs Set Flow', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3)
ax4.legend(fontsize=10)
plt.tight_layout()
plt.savefig('c:/Users/cruz/Documents/SENSE/horstberry/scripts/mfc_calibration_error_pct.png', dpi=300)
print("  ✓ Saved: mfc_calibration_error_pct.png")

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print(f"\nGenerated {4} plots in the scripts/ directory:")
print("  1. mfc_calibration_overall.png - Complete dataset with regression lines")
print("  2. mfc_calibration_by_location.png - Separated by measurement location")
print("  3. mfc_calibration_residuals.png - Residual analysis for both models")
print("  4. mfc_calibration_error_pct.png - Percentage error trends")

# Export summary to CSV
summary_df = df.copy()
summary_df['Error_Abs'] = summary_df['Measured_Flow'] - summary_df['Set_Flow']
summary_df['Error_Pct'] = ((summary_df['Measured_Flow'] - summary_df['Set_Flow']) / 
                            summary_df['Set_Flow'] * 100)
summary_df['Predicted_Linear'] = linear_model(summary_df['Set_Flow'].values, *params_linear)
summary_df['Predicted_Affine'] = affine_model(summary_df['Set_Flow'].values, *params_affine)

summary_df.to_csv('c:/Users/cruz/Documents/SENSE/horstberry/scripts/mfc_calibration_analysis.csv', 
                  index=False)
print("\n✓ Exported detailed analysis to: mfc_calibration_analysis.csv")
print("\n" + "="*80)


import numpy as np
import matplotlib.pyplot as plt

# Define flow range (0 to 1.5 L/min = 1500 mL/min for comparison)
flow = np.linspace(1, 1500, 300)  # avoid zero to prevent divide-by-zero

# --------------------------
# Error formulas
# --------------------------

# 1) Agilent CrossLab CS: ±2% of reading OR ±0.2 mL/min (whichever is greater)
crosslab_error = np.maximum(0.02 * flow, 0.2)

# 2) MFC #1 (0.012...1.5 L/min → FS = 1500 mL/min)
mfc1_error = 0.005 * flow + 0.001 * 1500  # ±0.5%Rd + ±0.1%FS = ±[0.005*Rd + 1.5]

# 3) MFC #2 (0.136...10 mL/min? → Spec unclear: assuming FS = 10 mL/min?)
# User provided: "10 mln/min" likely means 10 mL/min (NOT L/min). To compare, convert scale.
fs2 = 10  # mL/min
mfc2_error = 0.005 * flow + 0.001 * fs2  # ±0.5%Rd + ±0.1%FS

# 4) MFC #3 (4.051...500 mln/min → FS=500 mL/min)
fs3 = 500
mfc3_error = 0.005 * flow + 0.001 * fs3

# -------------------------
# Plot
# -------------------------
plt.figure(figsize=(10, 6))
plt.plot(flow, crosslab_error, label="Agilent CrossLab CS")
plt.plot(flow, mfc1_error, label="MFC #1 (0–1500 mL/min)")
plt.plot(flow, mfc2_error, label="MFC #2 (0–10 mL/min scale extrapolated)")
plt.plot(flow, mfc3_error, label="MFC #3 (0–500 mL/min)")

plt.xlabel("Flow (mL/min)")
plt.ylabel("Absolute Error (± mL/min)")
plt.title("Absolute Measurement Error vs. Flow Rate")
plt.legend()
plt.grid(True)

plt.show()

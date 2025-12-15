# 📊 Measurement Uncertainty Guide

## Overview

The SENSE Flow interface now includes **comprehensive measurement uncertainty tracking and display** based on the actual specifications of each Bronkhorst Mass Flow Controller (MFC).

---

## 🎯 What's New

### 1. **Updated Helium Range**
- **Old**: 0.012023 - 1.5 L/min (same as other instruments)
- **New**: 0.000856 - 2.5 L/min (0.856 - 2500 mL/min)
- **Impact**: Better selection in automatic mode, correct proportionality calculations

### 2. **MFC Uncertainty Specifications**

Each Bronkhorst MFC has the following uncertainty specification:
```
Uncertainty = ±(0.5% × Reading + 0.1% × Full_Scale)
```

| Instrument | Address | Range (mL/min) | Full Scale (mL/min) |
|------------|---------|----------------|---------------------|
| Low flow   | 8       | 0.136 - 10     | 10                  |
| Medium flow| 5       | 1.233 - 150    | 150                 |
| High flow  | 3       | 12.023 - 1500  | 1500                |
| Helium     | 10      | 0.856 - 2500   | 2500                |
| Base gas   | 20      | 12.023 - 1500  | 1500                |

### 3. **Real-time Uncertainty Display**

New section in the **Concentration Control** panel shows:
- **Concentration uncertainty**: ±X.XX ppm (Y.Y%)
- **Base gas flow uncertainty**: ±X.XXX mln/min
- **Variable gas flow uncertainty**: ±X.XXX mln/min

### 4. **Error Bands on Plots**

The concentration plot now displays:
- **Blue line**: Actual measured concentration
- **Red dashed line**: Target concentration
- **Blue shaded area**: ±1σ (one standard deviation) uncertainty band

### 5. **Uncertainty Logging**

When you calculate flows, the system log shows:
```
Expected uncertainty: ±0.78 ppm (0.78% of target)
Flow uncertainties: Base gas ±4.000 mln/min, Variable gas ±0.010 mln/min
```

---

## 📐 How Uncertainty is Calculated

### Flow Uncertainty

For each MFC reading:
```
u_flow = (0.5% × Flow_reading) + (0.1% × Full_scale)
```

**Example**: Low flow MFC (address 8) reading 10.0 mL/min:
```
u_flow = (0.005 × 10.0) + (0.001 × 10.0)
       = 0.05 + 0.01
       = ±0.06 mL/min
```

### Concentration Uncertainty Propagation

Using the mixing equation:
```
C = (C₁ × F₁ + C₂ × F₂) / (F₁ + F₂)
```

The uncertainty is propagated using partial derivatives:
```
∂C/∂F₁ = (C₁ - C₂) × F₂ / (F₁ + F₂)²
∂C/∂F₂ = (C₂ - C₁) × F₁ / (F₁ + F₂)²

u_C = √[(∂C/∂F₁)² × u_F₁² + (∂C/∂F₂)² × u_F₂²]
```

This assumes **independent errors** between the two MFCs.

---

## 💡 Practical Example

### Scenario
- **Target concentration**: 100 ppm
- **Base gas (air)**: 0 ppm, Flow = 500 mL/min
- **Source gas**: 5000 ppm
- **Required variable gas flow**: ~10.2 mL/min

### Step 1: Calculate Required Flows

Using the mixing equation:
```
F₂ = F₁ × (C_target - C₁) / (C₂ - C_target)
F₂ = 500 × (100 - 0) / (5000 - 100)
F₂ = 10.204 mL/min
```

### Step 2: Select Instrument

**Automatic mode evaluates**:
- Low flow (0.136-10 mL/min): ❌ Flow too high (10.204 > 10)
- Medium flow (1.233-150 mL/min): ✅ Utilization = 6.8%
- High flow (12.023-1500 mL/min): ✅ Utilization = 0.68%

**Selected**: Medium flow (best utilization at 6.8%)

### Step 3: Calculate Flow Uncertainties

**Base gas MFC (address 20)**: High flow, FS = 1500 mL/min
```
u_F₁ = (0.005 × 500) + (0.001 × 1500)
     = 2.5 + 1.5
     = ±4.0 mL/min
```

**Variable gas MFC (address 5)**: Medium flow, FS = 150 mL/min
```
u_F₂ = (0.005 × 10.2) + (0.001 × 150)
     = 0.051 + 0.15
     = ±0.201 mL/min
```

### Step 4: Propagate to Concentration

**Sensitivity coefficients**:
```
∂C/∂F₁ = (0 - 5000) × 10.2 / (510.2)² = -0.196 ppm/(mL/min)
∂C/∂F₂ = (5000 - 0) × 500 / (510.2)² = +9.61 ppm/(mL/min)
```

**Concentration uncertainty**:
```
u_C² = (-0.196)² × (4.0)² + (9.61)² × (0.201)²
     = 0.615 + 3.73
     = 4.35

u_C = √4.35 = ±2.08 ppm
```

**Relative error**: 2.08 / 100 = **2.08%**

### Step 5: Interpretation

- **Expected concentration**: 100 ppm
- **Uncertainty (1σ)**: ±2.08 ppm
- **68% confidence**: Result will be between **97.92 - 102.08 ppm**
- **95% confidence (2σ)**: Result will be between **95.84 - 104.16 ppm**

---

## 🎨 Visual Display

### Concentration Control Panel
```
┌─ ⚗️ Concentration Control ──────────────────┐
│  Base gas (air):         Address 20         │
│  Variable gas:           [5 (Medium flow)]  │
│  ─────────────────────────────────────────  │
│  Outflow desired         [100.0    ] ppm    │
│  Base gas                [0.0      ] ppm    │
│  Gas concentration       [5000.0   ] ppm    │
│  Max Flow                [1.5      ] ln/min │
│                                              │
│  [⚡ Calculate Flows]                        │
│  ─────────────────────────────────────────  │
│  📊 Measurement Uncertainty                  │
│                                              │
│  Concentration:          ±2.08 ppm (2.1%)   │
│  Base gas flow:          ±4.000 mln/min     │
│  Variable gas flow:      ±0.201 mln/min     │
└──────────────────────────────────────────────┘
```

### Plot Display
```
Concentration with Uncertainty
│
│     ┌─────────────────────────┐
│     │   ±1σ uncertainty       │  ← Blue shaded area
│ 102 ├─────────────────────────┤
│     │                         │
│ 100 ├─────●───●───●───●───●───┤  ← Actual (blue line)
│     │ - - - - - - - - - - - - │  ← Target (red dashed)
│  98 ├─────────────────────────┤
│     │                         │
│     └─────────────────────────┘
└──────────────────────────────────→ Time
```

---

## 🔍 Interpreting Results

### What the Uncertainty Means

**1σ (68% confidence)**:
- There's a 68% probability the true concentration is within ±u_C of the measured value

**2σ (95% confidence)**:
- There's a 95% probability the true concentration is within ±2×u_C

### What Affects Uncertainty?

1. **MFC Selection** 
   - Operating at higher utilization = better precision
   - Low flow MFC at 90% capacity: ±0.06 mL/min
   - High flow MFC at 1% capacity: ±1.51 mL/min

2. **Flow Rates**
   - Higher flows generally have larger absolute uncertainties
   - But relative uncertainty (%) may improve

3. **Concentration Ratio**
   - Large differences between C₁ and C₂ increase sensitivity to F₂ errors
   - Example: 0 ppm vs 5000 ppm → High sensitivity

4. **Full Scale Value**
   - The ±0.1% FS term is constant regardless of reading
   - Larger FS instruments have larger base uncertainty

---

## ⚠️ Limitations & Considerations

### What's Included
✅ MFC reading uncertainty (±0.5% Rd)  
✅ MFC full-scale uncertainty (±0.1% FS)  
✅ Statistical propagation of flow uncertainties  
✅ Independent error assumption

### What's NOT Included
❌ Gas composition uncertainties  
❌ Temperature effects  
❌ Pressure variations  
❌ Calibration gas uncertainty (e.g., "5000 ppm" is assumed exact)  
❌ Line leaks or plumbing effects  
❌ MFC cross-sensitivity to different gases  
❌ Systematic biases

### Real-World Uncertainties

The displayed uncertainties are **lower bounds**. In practice:
- Add 1-2% for gas composition tables
- Add temperature coefficient effects
- Add calibration gas uncertainty (typically 2-5%)
- Consider systematic biases from setpoint vs actual flow

**Realistic total uncertainty**: Often **2-3× the calculated value**

---

## 🎯 Optimization Tips

### To Minimize Uncertainty

1. **Use Automatic Mode**
   - System selects MFC with best utilization
   - Higher utilization → better precision

2. **Choose Appropriate Target Concentration**
   - Avoid very low concentrations (< 1 ppm)
   - Uncertainty scales with concentration ratio

3. **Maximize Base Gas Flow**
   - Within instrument limits
   - Reduces relative impact of F₁ uncertainty

4. **Select Compatible MFC**
   - Variable gas MFC should operate at 50-100% capacity
   - Avoid running at < 10% of range

5. **Consider External Measurement**
   - Use Agilent Crosslab or similar for verification
   - Independent measurement reduces systematic errors

---

## 📝 Technical Files

New/modified files for uncertainty tracking:

### New Files
- `src/models/uncertainty.py` - Core uncertainty calculations
  - `calculate_flow_uncertainty()` - MFC uncertainty
  - `propagate_concentration_uncertainty()` - Error propagation
  - `calculate_required_flow_with_uncertainty()` - Full analysis
  - `format_uncertainty_string()` - Display formatting

### Modified Files
- `src/views/main_window.py`
  - Added uncertainty display labels
  - Added real-time uncertainty calculation
  - Added error bands to plots
  - Updated logging to show uncertainties

- `src/controllers/flow_controller.py`
  - Updated Helium range (address 10)
  - Added MFC_UNCERTAINTIES dictionary

---

## 🚀 Usage Workflow

### Standard Operation with Uncertainty

1. **Scan Instruments**
   ```
   [🔍 Scan Instruments]
   ```

2. **Set Parameters**
   - Target concentration: e.g., 100 ppm
   - Base gas: 0 ppm
   - Source gas: 5000 ppm

3. **Calculate Flows**
   ```
   [⚡ Calculate Flows]
   ```
   
   System log shows:
   ```
   ✓ Calculated: Base gas (air): 500.000 mln/min, Medium flow: 10.204 mln/min
   ℹ️ Expected uncertainty: ±2.08 ppm (2.08% of target)
   ℹ️ Flow uncertainties: Base gas ±4.000 mln/min, Variable gas ±0.201 mln/min
   ```

4. **Review Uncertainty**
   - Check the **📊 Measurement Uncertainty** section
   - Verify uncertainties are acceptable for your application

5. **Apply Flows**
   ```
   [✓ Apply] buttons
   ```

6. **Monitor Real-time**
   - Watch the concentration plot
   - Blue shaded area shows ±1σ uncertainty
   - Verify actual concentration stays within error band

---

## 🔬 For Advanced Users

### Accessing Uncertainty Data Programmatically

The uncertainty module can be imported:
```python
from src.models.uncertainty import (
    calculate_flow_uncertainty,
    propagate_concentration_uncertainty
)

# Calculate flow uncertainty
u_flow = calculate_flow_uncertainty(
    flow_mln_min=10.0,
    address=8  # Low flow MFC
)

# Propagate to concentration
u_C, details = propagate_concentration_uncertainty(
    C1_ppm=0,
    F1_mln_min=500,
    C2_ppm=5000,
    F2_mln_min=10.2,
    addr1=20,
    addr2=5
)

print(f"Concentration uncertainty: {u_C:.2f} ppm")
print(f"Sensitivity to F1: {details['dC_dF1']:.3f} ppm/(mL/min)")
print(f"Sensitivity to F2: {details['dC_dF2']:.3f} ppm/(mL/min)")
```

---

## ❓ FAQ

**Q: Why is the uncertainty larger at low concentrations?**  
A: The relative uncertainty (%) increases because the base gas flow dominates, and its absolute uncertainty becomes significant compared to the small amount of source gas.

**Q: Can I trust the displayed uncertainty?**  
A: It's a good **lower bound** based on MFC specs. Real-world uncertainty is typically 2-3× higher when including all systematic effects.

**Q: Should I use automatic mode?**  
A: Yes! Automatic mode selects the MFC with best utilization, minimizing uncertainty.

**Q: What if my uncertainty is too high?**  
A: Consider:
- Using a different MFC with better range
- Adjusting target concentration
- Increasing base gas flow
- Using external verification measurement

**Q: How does this relate to Agilent Crosslab?**  
A: Agilent Crosslab is an independent measurement device. Use it to:
- Verify the calculated concentrations
- Detect systematic biases
- Provide traceability
- Cross-check MFC accuracy

---

**Enjoy more transparent and trustworthy measurements! 📊✨**

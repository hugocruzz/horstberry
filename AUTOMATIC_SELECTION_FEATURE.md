# 🤖 Automatic Instrument Selection Feature

## Overview

The SENSE Flow software now includes an intelligent **Automatic** mode that automatically selects the best flow controller instrument based on the required flow rate. This ensures optimal precision by operating instruments close to their maximum capacity.

---

## 🎯 How It Works

### Selection Algorithm

When **Automatic** mode is enabled, the system:

1. **Calculates required flow** from concentration parameters
2. **Evaluates all available instruments** (excluding base gas)
3. **Checks compatibility** - Can the instrument handle this flow?
4. **Calculates utilization** - How close to max capacity?
5. **Selects best match** - Highest utilization percentage

### Why Utilization Matters

Flow controllers are most accurate when operating near their maximum flow rate:

```
Example: Required flow = 10 mln/min

Option A: Low flow (0.13-10 mln/min)
  → Utilization: 100% ✅ BEST CHOICE
  → Running at maximum capacity

Option B: Medium flow (1.2-150 mln/min)
  → Utilization: 6.7%
  → Running at very low capacity (less precise)

Option C: High flow (0.012-1.5 ln/min = 12-1500 mln/min)
  → Utilization: 0.67%
  → Running at extremely low capacity (poor precision)
```

**Result:** System automatically selects **Low flow** instrument for best precision.

---

## 📋 Usage Guide

### Step 1: Scan Instruments
```
1. Select COM port
2. Click [🔍 Scan Instruments]
3. Wait for scan to complete
```

### Step 2: Enable Automatic Mode
```
After scanning:
┌─ ⚗️ Concentration Control ──────┐
│  Variable gas: [Automatic ▼]    │  ← Automatically selected
└──────────────────────────────────┘
```

The dropdown will show:
- **Automatic** (default)
- 3 (High flow)
- 5 (Medium flow)
- 8 (Low flow)
- 10 (Helium)

### Step 3: Set Concentration Parameters
```
┌─ ⚗️ Concentration Control ──────┐
│  Outflow desired: [2.0    ] ppm │
│  Base gas:        [0.0    ] ppm │
│  Gas conc:        [5000.0 ] ppm │
│  Max Flow:        [1.5    ] ln/min │
└──────────────────────────────────┘
```

### Step 4: Calculate Flows
```
Click [⚡ Calculate Flows]

System will:
✓ Calculate required flows (Q1, Q2)
✓ Automatically select best instrument for Q2
✓ Display selection in log
✓ Pre-fill flow values
```

### Step 5: Review Selection
```
System Log shows:
[12:34:56] ℹ️ Flow 10.000 ln/min → Low flow 
           (range: 0.1360-10.00 ln/min, utilization: 100.0%)
[12:34:57] ✓ Automatic mode: Selected Low flow (address 8) 
           for flow 10.000 ln/min
```

### Step 6: Apply Flows
```
Click [✓ Apply] buttons to start flows
```

---

## 🔧 Selection Examples

### Example 1: Very Low Flow
```
Required: 0.5 ln/min (500 mln/min)

Candidates:
- Low flow:    0.14-10 mln/min    → ❌ Flow too high
- Medium flow: 1.2-150 mln/min    → ❌ Flow too high
- High flow:   12-1500 mln/min    → ✓ Utilization: 33%

Selected: High flow ✅
```

### Example 2: Medium Flow
```
Required: 0.075 ln/min (75 mln/min)

Candidates:
- Low flow:    0.14-10 mln/min    → ❌ Flow too high
- Medium flow: 1.2-150 mln/min    → ✓ Utilization: 50%
- High flow:   12-1500 mln/min    → ✓ Utilization: 5%

Selected: Medium flow ✅ (highest utilization)
```

### Example 3: High Flow
```
Required: 0.01 ln/min (10 mln/min)

Candidates:
- Low flow:    0.14-10 mln/min    → ✓ Utilization: 100%
- Medium flow: 1.2-150 mln/min    → ✓ Utilization: 6.7%
- High flow:   12-1500 mln/min    → ✓ Utilization: 0.67%

Selected: Low flow ✅ (highest utilization)
```

---

## 🎚️ Manual Override

You can always override automatic selection:

```
┌─ ⚗️ Concentration Control ──────┐
│  Variable gas: [5 (Medium) ▼]   │  ← Manually select
└──────────────────────────────────┘

Options:
- Automatic       ← Smart selection
- 3 (High flow)   ← Manual
- 5 (Medium flow) ← Manual
- 8 (Low flow)    ← Manual
- 10 (Helium)     ← Manual
```

**When to use manual:**
- Testing specific instrument
- Known instrument preference
- Troubleshooting
- Specific experimental requirements

---

## 📊 Instrument Ranges Reference

| Address | Name | Range | Unit | Best For |
|---------|------|-------|------|----------|
| 3 | High flow | 0.012 - 1.5 | ln/min | 12-1500 mln/min |
| 5 | Medium flow | 1.233 - 150 | mln/min | 1.2-150 mln/min |
| 8 | Low flow | 0.136 - 10 | mln/min | 0.14-10 mln/min |
| 10 | Helium | 0.012 - 1.5 | ln/min | 12-1500 mln/min (Helium) |
| 20 | Base gas (air) | 0.012 - 1.5 | ln/min | Always base gas |

---

## 🔍 System Log Messages

### Automatic Selection Messages

**Selection Analysis:**
```
[12:34:56] ℹ️ Flow 10.000 ln/min → Low flow 
           (range: 0.1360-10.00 ln/min, utilization: 100.0%)
```

**Successful Selection:**
```
[12:34:57] ✓ Automatic mode: Selected Low flow (address 8) 
           for flow 10.000 ln/min
```

**Mode Enabled:**
```
[12:34:55] ✓ Variable gas set to Automatic mode
```

**Mode Info:**
```
[12:34:55] ℹ️ Variable gas set to Automatic mode 
           (will select best instrument based on flow)
```

### Error Messages

**No Suitable Instrument:**
```
[12:34:56] ✗ Automatic selection failed: no suitable instrument found.
```
This happens when:
- Required flow is outside all instrument ranges
- No instruments available (except base gas)

---

## 🧮 Technical Details

### Selection Algorithm Code
```python
def select_best_instrument_for_flow(self, required_flow: float) -> int:
    """
    Select the best instrument for the required flow.
    Prioritizes highest utilization (closest to max capacity).
    """
    # Get all instruments except base gas (20)
    # Filter by: min_flow <= required_flow <= max_flow
    # Calculate: utilization = (required_flow / max_flow) * 100
    # Select: highest utilization
    # Return: instrument address
```

### Utilization Formula
```
Utilization (%) = (Required Flow / Max Flow) × 100

Higher utilization = Better precision
Target: Close to 100%
```

### Filtering Logic
```
For each instrument:
  IF min_flow <= required_flow <= max_flow:
    → Candidate (can handle this flow)
  ELSE:
    → Skip (cannot handle this flow)

From candidates:
  SELECT instrument with highest utilization
```

---

## ✅ Benefits

| Benefit | Description |
|---------|-------------|
| **Better Precision** | Instruments run at optimal capacity |
| **Ease of Use** | No need to know instrument ranges |
| **Flexibility** | Can override with manual selection |
| **Transparency** | Selection reasoning shown in log |
| **Reliability** | Prevents instrument overload/underuse |

---

## 🎯 Best Practices

### When to Use Automatic
✅ Normal operation  
✅ Don't know which instrument to use  
✅ Want optimal precision  
✅ Variable flow requirements  
✅ Quick experiments  

### When to Use Manual
✅ Testing specific instrument  
✅ Instrument-specific calibration  
✅ Known preference for experiment  
✅ Troubleshooting issues  
✅ Research on instrument behavior  

---

## 🔄 Workflow Comparison

### Before (Manual Selection)
```
1. Scan instruments
2. Calculate required flow mentally
3. Compare with instrument ranges manually
4. Select best instrument from dropdown
5. Calculate flows
6. Apply
```

### After (Automatic Mode)
```
1. Scan instruments
2. Keep "Automatic" selected (default)
3. Calculate flows ← System selects best instrument
4. Review selection in log
5. Apply
```

**Result:** 3 steps saved! ⚡

---

## 📝 Configuration

### Default Behavior
- **Automatic** is selected by default after scanning
- Can be changed at any time from dropdown
- Selection persists until changed

### Changing Mode
```
Simply select from dropdown:
┌─────────────────┐
│ Automatic      │ ← Smart selection
│ 3 (High flow)  │
│ 5 (Medium flow)│
│ 8 (Low flow)   │
│ 10 (Helium)    │
└─────────────────┘
```

---

## 🐛 Troubleshooting

### Issue: "No suitable instrument found"
**Cause:** Required flow outside all ranges  
**Solution:** 
- Check concentration parameters
- Verify max flow setting
- Ensure all instruments scanned

### Issue: Unexpected instrument selected
**Cause:** Utilization logic prioritizes high %  
**Solution:**
- Review selection reasoning in log
- Manually select preferred instrument
- Verify instrument ranges are correct

### Issue: Automatic not available
**Cause:** No instruments scanned  
**Solution:**
- Click [🔍 Scan Instruments]
- Verify COM port connection
- Check instruments are powered on

---

## 🆕 Version History

**Version 1.0** (October 29, 2025)
- Initial release
- Automatic instrument selection
- Utilization-based algorithm
- Default to Automatic mode

---

**Smart instrument selection for optimal precision! 🎯**

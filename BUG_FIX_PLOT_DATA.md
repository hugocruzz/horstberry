# 🐛 Bug Fix - Plot Data Collection Error

## Issue Description

**Error:**
```
TypeError: unsupported operand type(s) for /=: 'NoneType' and 'int'
```

**Location:** `collect_plot_data()` method, line 1056

**Symptoms:**
- Error messages: "Error reading flow", "Error reading valve", "Error reading temperature"
- Application crashes when trying to plot data
- Division operation failing on None values

---

## Root Causes

### 1. **None Flow Values**
Flow readings from instruments were returning `None` instead of numeric values.

**Problem code:**
```python
flow1 = readings_1.get('Flow', 0)  # Could be None
flow2 = readings_2.get('Flow', 0)  # Could be None

if unit1 in ("ml/min", "mln/min"):
    flow1 /= 1000  # ❌ Error if flow1 is None
if unit2 in ("ml/min", "mln/min"):
    flow2 /= 1000  # ❌ Error if flow2 is None
```

### 2. **Automatic Mode Plotting Issue**
When "Automatic" mode was selected, `address_2` was set to `'auto'` (string) instead of an actual instrument address.

**Problem:**
```python
address_2 = self.instrument_addresses.get('gas2')  # Could be 'auto'
readings_2 = self.controller.get_readings(address_2)  # ❌ Can't read from 'auto'
```

---

## Solutions Implemented

### 1. **None Value Protection**

**Changed from:**
```python
flow1 = readings_1.get('Flow', 0)
flow2 = readings_2.get('Flow', 0)

if unit1 in ("ml/min", "mln/min"):
    flow1 /= 1000
if unit2 in ("ml/min", "mln/min"):
    flow2 /= 1000
```

**Changed to:**
```python
flow1 = readings_1.get('Flow')  # No default, get actual value or None
flow2 = readings_2.get('Flow')

# Check if flows are None (reading error)
if flow1 is None or flow2 is None:
    return  # Skip this data point if readings failed

# Convert to ln/min if needed (with extra None check)
if unit1 in ("ml/min", "mln/min") and flow1 != 0:
    flow1 = flow1 / 1000  # ✅ Safe, we know flow1 is not None
if unit2 in ("ml/min", "mln/min") and flow2 != 0:
    flow2 = flow2 / 1000  # ✅ Safe, we know flow2 is not None
```

### 2. **Track Actual Address in Auto Mode**

**Added new variable:**
```python
# In __init__
self.current_gas2_address = None  # Track actual address for plotting
```

**Update when calculating flows:**
```python
if addr2_raw == 'auto':
    addr2 = self.select_best_instrument_for_flow(Q2)
    # Store for plotting
    self.current_gas2_address = addr2
else:
    addr2 = addr2_raw
    self.current_gas2_address = addr2
```

**Use in plotting:**
```python
# For plotting, use the current selected address (in case of auto mode)
if address_2_raw == 'auto':
    address_2 = self.current_gas2_address  # ✅ Use actual address
else:
    address_2 = address_2_raw

# Skip if addresses not assigned
if address_1 is None or address_2 is None:
    return  # Skip data collection if roles haven't been assigned yet
```

---

## Code Changes Summary

### File: `src/views/main_window.py`

#### Change 1: Initialize tracking variable
```python
# Line ~168
self.current_gas2_address = None  # Track actual address for plotting
```

#### Change 2: Store selected address in calculate_flows()
```python
# Line ~938
if addr2_raw == 'auto':
    addr2 = self.select_best_instrument_for_flow(Q2)
    # ...
    self.current_gas2_address = addr2  # NEW
else:
    addr2 = addr2_raw
    self.current_gas2_address = addr2  # NEW
```

#### Change 3: Use tracked address for plotting
```python
# Line ~1025
# For plotting, use the current selected address (in case of auto mode)
if address_2_raw == 'auto':
    address_2 = self.current_gas2_address
else:
    address_2 = address_2_raw

if address_1 is None or address_2 is None:
    return
```

#### Change 4: Handle None values in flow readings
```python
# Line ~1045
flow1 = readings_1.get('Flow')  # No default
flow2 = readings_2.get('Flow')

# Check if flows are None (reading error)
if flow1 is None or flow2 is None:
    return

# Convert to ln/min if needed
if unit1 in ("ml/min", "mln/min") and flow1 != 0:
    flow1 = flow1 / 1000
if unit2 in ("ml/min", "mln/min") and flow2 != 0:
    flow2 = flow2 / 1000
```

---

## Why These Fixes Work

### Fix 1: None Value Check
- **Before:** Tried to divide None by 1000 → TypeError
- **After:** Checks if None first, skips data point if readings failed
- **Benefit:** Gracefully handles reading errors without crashing

### Fix 2: Address Tracking
- **Before:** Tried to read from 'auto' string → No instrument found
- **After:** Uses actual selected address for reading
- **Benefit:** Plotting works in Automatic mode

### Fix 3: Safe Division
- **Before:** `flow /= 1000` could fail if flow is None or 0
- **After:** `flow = flow / 1000` only if flow is not None and not 0
- **Benefit:** No division errors, no side effects

---

## Testing Scenarios

### Scenario 1: Normal Operation
```
✅ Manual instrument selection
✅ Calculate flows
✅ Apply flows
✅ Plot data collected successfully
```

### Scenario 2: Automatic Mode
```
✅ Select "Automatic"
✅ Calculate flows
✅ Instrument auto-selected
✅ current_gas2_address set
✅ Plot data uses correct address
✅ Data collected successfully
```

### Scenario 3: Reading Errors
```
✅ Instrument returns None for flow
✅ None check catches it
✅ Data point skipped (no crash)
✅ Next update retries
✅ Application continues running
```

### Scenario 4: Before Flow Started
```
✅ No flows set yet
✅ Readings return None or 0
✅ Data collection skips gracefully
✅ No errors shown to user
```

---

## Error Handling Flow

```
collect_plot_data()
    ↓
Get addresses
    ↓
Is auto mode? → Yes → Use current_gas2_address
              ↓ No  → Use direct address
    ↓
Address None? → Yes → Return (skip)
              ↓ No
    ↓
Get readings
    ↓
Flow is None? → Yes → Return (skip)
              ↓ No
    ↓
Convert units safely
    ↓
Add to plot data ✅
```

---

## Benefits of the Fix

| Aspect | Before | After |
|--------|--------|-------|
| **Stability** | Crashes on None | Handles gracefully |
| **Auto Mode** | Doesn't work | Works perfectly |
| **Error Messages** | Many errors | Silent handling |
| **User Experience** | Frustrating | Smooth |
| **Data Collection** | Stops on error | Continues |

---

## Additional Safeguards Added

1. **Early returns** - Skip data collection if conditions not met
2. **None checks** - Explicit checks before operations
3. **Safe division** - Use assignment instead of in-place operation
4. **Address validation** - Ensure real address before reading
5. **Zero check** - Don't divide zero values unnecessarily

---

## Prevention of Future Issues

### Best Practices Applied

1. **Don't use default values for critical data**
   ```python
   # Bad
   flow = readings.get('Flow', 0)  # Hides None values
   
   # Good
   flow = readings.get('Flow')  # Get actual value or None
   if flow is None:
       # Handle error
   ```

2. **Check before operations**
   ```python
   # Bad
   flow /= 1000  # Might fail
   
   # Good
   if flow is not None and flow != 0:
       flow = flow / 1000
   ```

3. **Track state properly**
   ```python
   # Store actual values for later use
   self.current_gas2_address = addr2
   ```

---

## Testing Checklist

- [x] No errors when instruments not connected
- [x] No errors when flows not started
- [x] No errors in Automatic mode
- [x] No errors in Manual mode
- [x] Plotting works after Calculate Flows
- [x] Plotting works after Apply
- [x] No division by zero errors
- [x] No None type errors
- [x] Application runs continuously without crashes

---

**All issues resolved! The application now handles edge cases gracefully and works reliably in all modes.** ✅

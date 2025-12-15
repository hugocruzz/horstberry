# Calibration Routine Mode - User Guide

## Overview

The **Concentration Calibration Routine Mode** provides an automated way to calibrate your system across a range of concentrations. This feature is accessible from the main window via the "⚙️ Calibration Routine" button in the Connection panel.

## Features

### 1. Data Directory Selection
- Click the "**...**" button to select where calibration data will be saved
- The selected directory path will be displayed
- This is **required** before starting a routine

### 2. Configuration Parameters

#### Input Gas Concentration
- **Default:** 5000 ppm
- The concentration of your input/source gas
- Used as the basis for calculating dilutions

#### Total Flow
- **Units:** L/min or sccm (selectable)
- The total flow rate for all calibration steps
- Dropdown allows switching between L/min and sccm

### 3. Step Configuration

#### Number of Steps
- Define how many concentration points you want to calibrate
- Example: 10 steps

#### Step Generation Mode

**A. Manual Step Entry**
- Select the "Manual Step Entry" radio button
- Click "Enter Steps Manually" to open a dialog
- Enter each concentration value (one per line)
- Example:
  ```
  0
  25
  50
  75
  100
  ```

**B. Automatic Computation** (Default)
- Select the "Automatic Computation" radio button
- **Initial Concentration (ppm):** Starting concentration (default: 0)
- **Final Concentration (ppm):** Ending concentration (default: 100)
- Steps are automatically computed with linear spacing
- Example: 0 → 10 → 20 → 30 → ... → 100

### 4. Step Duration
- Define how long each concentration step should run
- **Units:** seconds, minutes, or hours (selectable)
- Example: 60 seconds = 1 minute per step

### 5. Back and Forth Mode
- **Checkbox:** Enable/disable
- When enabled, the routine will:
  1. Run through all steps in ascending order
  2. Then run through all steps in descending order (excluding duplicate at the end)
- Example with 3 steps (0, 50, 100):
  - Forward: 0 → 50 → 100
  - Backward: 50 → 0
  - Total: 5 steps

## Step Preview Panel

The right panel shows:
- **List of all computed steps** with step numbers and concentrations
- **Total number of steps**
- **Estimated total time** for the entire routine
  - Automatically converts to appropriate units (seconds/minutes/hours)

### Example Display
```
Step   1:     0.00 ppm
Step   2:    10.00 ppm
Step   3:    20.00 ppm
...
Step  10:   100.00 ppm
Step  11:    90.00 ppm  (back and forth)
...

Total: 19 steps | Estimated time: 19.0 minutes
```

## Actions

### Update Step Preview
- Click to recalculate steps based on current configuration
- Automatically updates when changing automatic mode parameters

### Start Calibration Routine
- Validates all configuration parameters
- Confirms before starting
- Shows estimated duration
- **Note:** Full execution logic will be implemented in future updates

### Export Configuration
- Saves the current configuration to a text file
- Includes:
  - All parameters
  - Complete step list
  - Useful for documentation and reproducibility

### Close
- Closes the calibration window without starting a routine

## Usage Example

### Basic Calibration (0-100 ppm, 10 steps)

1. **Open the window:** Click "⚙️ Calibration Routine" in the main window
2. **Select directory:** Click "..." and choose a folder for data logging
3. **Set input gas:** 5000 ppm (default)
4. **Set total flow:** 1.0 L/min (default)
5. **Configure steps:**
   - Number of Steps: 10
   - Mode: Automatic Computation
   - Initial Conc: 0 ppm
   - Final Conc: 100 ppm
6. **Set duration:** 60 seconds per step
7. **Enable back and forth:** ✓ (optional)
8. **Review preview:** Check the step list (19 steps with back-and-forth)
9. **Start routine:** Click "Start Calibration Routine"

**Result:** System will run through 0, 11.1, 22.2, ..., 100, 88.9, ..., 0 ppm, spending 60 seconds at each concentration.

## Tips

- **Use back-and-forth mode** to check for hysteresis in your system
- **Export configuration** before starting for record-keeping
- **Start with fewer steps** (3-5) to test the system before long calibrations
- **Adjust step duration** based on your system's response time
- For quick testing, use seconds; for thorough calibration, use minutes

## Future Enhancements

- Real-time progress monitoring
- Data visualization during routine
- Automatic data analysis
- Custom step patterns
- Temperature compensation
- Flow stability checks

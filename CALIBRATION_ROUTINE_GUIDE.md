# Calibration Routine Mode - User Guide

## Overview

The **Concentration Calibration Routine Mode** provides an automated way to calibrate your system across a range of concentrations. This feature is accessible from the main window via the "⚙️ Calibration Routine" button in the Connection panel.

## NEW: Automatic Execution & Smart Features

### ✨ Key Updates
- **✅ Full Calibration Execution**: Routine now runs automatically through all steps
- **✅ Automatic Instrument Selection**: Smart selection of best MFC for each flow requirement
- **✅ Persistent Settings**: All settings saved and restored automatically
- **✅ Default Directory**: `calibration_file` folder created automatically
- **✅ Calibration Mode Indicator**: Main window shows "CALIBRATION MODE ACTIVE" during routine
- **✅ CSV Data Logging**: All data automatically saved with timestamps

## Features

### 1. Data Directory Selection
- **Default:** `calibration_file` folder (created automatically in project directory)
- Click the "**...**" button to select a different directory
- **Last used directory is remembered** when you reopen the window
- All calibration data saved as timestamped CSV files

### 2. Configuration Parameters

#### Input Gas Concentration
- **Default:** 5000 ppm
- The concentration of your input/source gas
- Used as the basis for calculating dilutions

#### Total Flow
- **Default:** 1.0 L/min
- **Units:** L/min or mL/min (sccm)
  - **Note:** sccm = mL/min = 0.001 L/min (1000 mL/min = 1 L/min)
- The total flow rate for all calibration steps
- Dropdown allows switching between L/min and mL/min (sccm)

### 3. Step Configuration

#### Number of Steps
- **Default:** 11 steps
- Define how many concentration points you want to calibrate

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
- Example with 11 steps: 0 → 10 → 20 → 30 → ... → 100

### 4. Step Duration
- Define how long each concentration step should run
- **Default:** 60 seconds
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
Step  11:   100.00 ppm

Total: 11 steps | Estimated time: 11.0 minutes
```

## Running a Calibration

### Start Calibration Routine

When you click **"Start Calibration Routine"**:

1. **Validation**: System checks all requirements
   - Valid data directory
   - Steps configured
   - Instruments connected

2. **Automatic Instrument Selection**: For each step:
   - Calculates required flows based on target concentration
   - **Automatically selects the best MFC** for the variable gas flow
   - Can switch between instruments during routine if optimal

3. **Execution**:
   - Sets flows for base gas (air) and variable gas
   - Waits for specified duration at each concentration
   - Logs all data to CSV file

4. **Status Display**:
   - Main window shows **"CALIBRATION MODE ACTIVE"** in red banner
   - Command output shows progress for each step
   - Instrument selection displayed for each step

5. **Data Logging**:
   - File: `calibration_YYYYMMDD_HHMMSS.csv`
   - Columns: Step, Target_Conc_ppm, Actual_Conc_ppm, Base_Flow_Lmin, Variable_Flow_Lmin, Variable_Instrument, Timestamp

### During Calibration

- **Close Window**: Can close calibration window, routine continues
- **Stop Early**: Closing window will prompt to stop calibration
- **Real-time Updates**: Main window command output shows progress
- **Mode Indicator**: Red "CALIBRATION MODE ACTIVE" banner visible

## Settings Persistence

All settings are **automatically saved** when:
- Starting a calibration
- Closing the calibration window

Settings are **automatically loaded** when:
- Reopening the calibration window

**Saved settings include:**
- Data directory path (last used)
- Input gas concentration
- Total flow and unit
- Step number
- Step mode (manual/automatic)
- Initial and final concentrations
- Step duration and unit
- Back and forth mode

## Actions

### Export Configuration
- Saves the current configuration to a text file
- Includes:
  - All parameters
  - Complete step list
  - Useful for documentation and reproducibility

### Close
- Saves settings automatically
- If calibration running, prompts to stop
- Clears calibration mode indicator

## Usage Example

### Basic Calibration (0-100 ppm, 11 steps)

1. **Open the window:** Click "⚙️ Calibration Routine" in the main window
2. **Check directory:** Default `calibration_file` folder is pre-selected
3. **Set input gas:** 5000 ppm (default)
4. **Set total flow:** 1.0 L/min (default)
5. **Configure steps:**
   - Number of Steps: 11 (default)
   - Mode: Automatic Computation
   - Initial Conc: 0 ppm
   - Final Conc: 100 ppm
6. **Set duration:** 60 seconds per step (default)
7. **Review preview:** 11 steps shown
8. **Start routine:** Click "Start Calibration Routine"
9. **Monitor:** Main window shows "CALIBRATION MODE ACTIVE" and progress updates

**Result:** System automatically:
- Calculates optimal flows for each concentration
- Selects best MFC for each step
- Runs through 0, 10, 20, ..., 100 ppm
- Logs all data to timestamped CSV file

## Data Output

### CSV File Format
```csv
Step,Target_Conc_ppm,Actual_Conc_ppm,Base_Flow_Lmin,Variable_Flow_Lmin,Variable_Instrument,Timestamp
1,0.00,0.12,0.9850,0.0150,8,2025-12-15T10:30:45.123456
2,10.00,9.87,0.9823,0.0177,8,2025-12-15T10:31:45.234567
...
```

## Unit Conversion Reference

- **L/min** (liters per minute) = **1000 mL/min**
- **mL/min** (milliliters per minute) = **sccm** (standard cubic centimeters per minute)
- Example: 1.5 L/min = 1500 mL/min = 1500 sccm

## Tips

- **Use back-and-forth mode** to check for hysteresis in your system
- **Export configuration** before starting for record-keeping
- **Start with fewer steps** (3-5) to test the system before long calibrations
- **Adjust step duration** based on your system's response time
- For quick testing, use seconds; for thorough calibration, use minutes
- **Settings persist** - next time you open, everything is remembered
- **Default directory** is always available and ready to use

## Troubleshooting

### "No suitable instrument found"
- Check that MFCs are scanned and connected
- Verify flow requirements are within instrument ranges
- System will skip steps that can't be achieved

### Calibration stops unexpectedly
- Check instrument connections
- Verify MFC communication
- Review command output for specific errors

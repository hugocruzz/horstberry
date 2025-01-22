# Pyhorst - Bronkhorst Flow Controller Interface

A Python interface for Bronkhorst flow controllers with concentration mixing capabilities.

## Features

- Real-time flow control and monitoring
- Concentration-based flow calculations
- Live data plotting
- Data logging
- Cross-platform support (Windows & Raspberry Pi)
- Touch screen compatible (RB-LCD-B10)

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/pyhorst.git
cd pyhorst
```

# Install dependencies
pip install -e .

# Configuration
Windows: Uses COM5 by default
Raspberry Pi: Uses /dev/ttyUSB0
Edit settings in config/settings.ini

# Usage 
```bash
# Run on Windows
python main.py

# Run on Raspberry Pi
python3 main.py
```
# Flow Control Methods
Direct Flow Control:

Set flow rates directly (0-1.5 ln/min)
Monitor actual flow rates
View valve positions and temperatures
Concentration-based Control:

Set desired output concentration
Automatic flow rate calculation
Real-time concentration monitoring


# Data Logging
CSV files stored in logs directory
Format: timestamp, setpoints, actual flows
Auto-generated filenames with timestamps

# Project structure:

```
bronkhorst/
│
├── src/
│   ├── controllers/     # Hardware & GUI controllers
│   ├── models/         # Flow calculations & data logging
│   ├── views/          # GUI implementation
│   └── platform/       # Platform-specific code
│
├── config/             # Configuration files
├── logs/              # Data logs directory
└── tests/             # Unit tests

```

License
MIT License

Authors
Hugo Cruz

futur:
- Input: concentration à la sortie
- fonction: debit de chaque EL-FLOW qui injectera directement pendant x temps 
https://github.com/bronkhorst-developer/bronkhorst-propar/blob/master/propar/__init__.py

Structure:

```
bronkhorst/
│
├── src/
│   ├── __init__.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── flow_controller.py    # Hardware interface
│   │   └── gui_controller.py     # GUI logic
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── calculations.py       # Flow calculations
│   │
│   └── views/
│       ├── __init__.py
│       └── main_window.py        # GUI layout
│
├── tests/
│   ├── __init__.py
│   ├── test_flow_controller.py
│   └── test_calculations.py
│
├── config/
│   └── settings.ini             # Configuration (COM ports, etc)
│
└── main.py                      # Entry point
```
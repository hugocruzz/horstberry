# Pyhorst - Bronkhorst Flow Controller Interface

A Python interface for Bronkhorst flow controllers with concentration mixing capabilities.

## To do:
- Apply a moving average with 10 second window
- Calculate target ppm based on flow1 and 2
- Show dynamic flow as number additionnaly to the graph.

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
git clone https://github.com/hugocruzz/horstberry.git
cd horstberry
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
Making scripts exececutable for git operations:

```
chmod +x commit_push.sh update_project.sh
```

Update:
```bash
./update_project.sh
```

Add commit and push:
```bash
./commit_push.sh "Your commit message here"
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

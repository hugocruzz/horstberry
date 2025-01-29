#!/bin/bash

# Enable debug output
set -x

# Log file
exec 1> >(tee "flow_controller_$(date +%Y%m%d_%H%M%S).log")
exec 2>&1

echo "Script started at $(date)"

# Check if virtual environment exists
VENV_PATH="$HOME/sense/python_scripts/horstberry/bronkhorst/bin/activate"
if [ ! -f "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH"

# Check if main.py exists
MAIN_PATH="$HOME/sense/python_scripts/horstberry/main.py"
if [ ! -f "$MAIN_PATH" ]; then
    echo "Error: main.py not found at $MAIN_PATH"
    exit 1
fi

# Start application
echo "Starting Flow Controller..."
python "$MAIN_PATH"

echo "Script ended at $(date)"
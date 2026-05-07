#!/bin/bash

# Ensure script is run in bash
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Python
if command_exists python3; then
    PYTHON_CMD="python3"
elif command_exists python; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

# Create venv directory if not exists
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv $VENV_DIR
else
    echo "Virtual environment already exists."
fi

# Activate venv
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found! Skipping dependency installation."
fi

echo ""
echo "========================================================"
echo "Environment setup complete!"
echo ""
echo "To activate the environment, run:"
echo "   source $VENV_DIR/bin/activate"
echo ""
echo "To run the server:"
echo "   python run_server.py"
echo "========================================================"

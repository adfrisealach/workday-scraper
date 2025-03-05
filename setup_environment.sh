#!/bin/bash

# Setup script for Workday Scraper
echo "Setting up environment for Workday Scraper..."

# Check if pip is installed
if ! command -v pip &> /dev/null; then
    echo "Error: pip is not installed. Please install pip first."
    exit 1
fi

# Create virtual environment (optional)
if command -v python3 -m venv &> /dev/null; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        echo "Activating virtual environment..."
        source venv/Scripts/activate
    else
        echo "Warning: Could not activate virtual environment. Continuing with system Python."
    fi
else
    echo "Warning: python3 venv module not available. Continuing with system Python."
fi

# Install required dependencies
echo "Installing required dependencies..."
pip install -r requirements.txt

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Create configs directory if it doesn't exist
if [ ! -d "configs" ]; then
    echo "Creating configs directory..."
    mkdir -p configs
    
    # Create a sample config file
    echo "Creating sample config file..."
    echo "autodesk,https://autodesk.wd1.myworkdayjobs.com/Ext" > configs/sample.txt
    echo "Sample config file created at configs/sample.txt"
fi

echo "Setup complete!"
echo ""
echo "To run the scraper, use:"
echo "  python -m workday_scraper -f <config_file>"
echo ""
echo "For more information, see README.md"
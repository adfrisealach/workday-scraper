#!/bin/bash
# Setup script for the JSON-LD extractor

# Exit on error
set -e

echo "Setting up JSON-LD extractor..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
python -m playwright install chromium

echo "Setup complete!"
echo "To use the JSON-LD extractor, activate the virtual environment with:"
echo "  source venv/bin/activate"
echo "Then run the test script with:"
echo "  python test_jsonld_extractor.py --url <workday-url>"
echo "Or run the enhanced scraper with:"
echo "  python workday_scraper_enhanced.py --config <config-file>"
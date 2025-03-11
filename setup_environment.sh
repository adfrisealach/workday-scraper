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

# Ask if the user wants to set up Telegram bot
echo ""
echo "Would you like to set up the Telegram bot for notifications? (y/n)"
read setup_telegram

if [ "$setup_telegram" = "y" ] || [ "$setup_telegram" = "Y" ]; then
    echo ""
    echo "Setting up Telegram bot..."
    echo ""
    echo "To use the Telegram bot, you need to:"
    echo "1. Create a bot using BotFather (https://t.me/BotFather)"
    echo "2. Get your chat ID (you can use @RawDataBot or @userinfobot)"
    echo ""
    
    # Ask for Telegram bot token
    echo "Enter your Telegram bot token from BotFather:"
    read telegram_token
    
    # Ask for Telegram chat ID
    echo "Enter your Telegram chat ID:"
    read telegram_chat_id
    
    # Detect shell and add environment variables
    shell_config=""
    if [ -n "$ZSH_VERSION" ]; then
        shell_config="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        shell_config="$HOME/.bashrc"
    else
        echo "Could not detect shell. Please manually add these environment variables:"
        echo "export TELEGRAM_BOT_TOKEN='$telegram_token'"
        echo "export TELEGRAM_CHAT_ID='$telegram_chat_id'"
        echo ""
    fi
    
    if [ -n "$shell_config" ]; then
        # Check if variables already exist in config
        if grep -q "TELEGRAM_BOT_TOKEN" "$shell_config"; then
            echo "TELEGRAM_BOT_TOKEN already exists in $shell_config. Skipping."
        else
            echo "# Workday Scraper Telegram bot configuration" >> "$shell_config"
            echo "export TELEGRAM_BOT_TOKEN='$telegram_token'" >> "$shell_config"
            echo "export TELEGRAM_CHAT_ID='$telegram_chat_id'" >> "$shell_config"
            echo "Environment variables added to $shell_config"
            echo "Please restart your terminal or run 'source $shell_config' to apply changes."
        fi
    fi
    
    # Set the variables for the current session
    export TELEGRAM_BOT_TOKEN="$telegram_token"
    export TELEGRAM_CHAT_ID="$telegram_chat_id"
    
    echo ""
    echo "Telegram bot setup complete!"
    echo "You can run the bot standalone with: ./run_telegram_bot.py"
fi

echo ""
echo "Setup complete!"
echo ""
echo "To run the scraper, use:"
echo "  python -m workday_scraper -f <config_file>"
echo ""
echo "To run the Telegram bot, use:"
echo "  ./run_telegram_bot.py"
echo ""
echo "For more information, see README.md"
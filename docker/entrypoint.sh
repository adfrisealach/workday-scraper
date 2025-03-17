#!/bin/bash
set -e

# Ensure we're in the correct directory
cd /app || exit 1

# Create necessary directories and set permissions
mkdir -p /app/data /app/configs /app/logs

# Setup and verify Playwright browser installation
echo "Checking Playwright browser installation..."
PLAYWRIGHT_VERSION=$(pip show playwright | grep "Version: " | cut -d' ' -f2)
echo "Using Playwright version: ${PLAYWRIGHT_VERSION}"

# Ensure the mount point exists and has correct permissions
if [ ! -d "/ms-playwright" ]; then
    echo "Creating Playwright directory..."
    mkdir -p /ms-playwright
fi

# Set proper permissions on the directory
chown -R root:root /ms-playwright
chmod -R 755 /ms-playwright

# Check for browser executable
if ! find /ms-playwright -name "chrome" -type f -executable | grep -q "chrome-linux/chrome"; then
    echo "Playwright browsers not found or incomplete, installing..."
    
    # Clean up any existing browser files (but not the mount point itself)
    echo "Cleaning up existing browser files..."
    find /ms-playwright -mindepth 1 -delete || true
    
    # Install browsers
    echo "Installing Playwright browsers..."
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright playwright install --with-deps chromium

    # Verify installation succeeded
    browser_path=$(find /ms-playwright -name "chrome" -type f | grep "chrome-linux/chrome" || true)
    if [ -n "$browser_path" ]; then
        echo "✓ Verified: Playwright browser executable is available"
        echo "Browser location: $browser_path"
        
        # Set permissions on browser files
        chrome_dir=$(dirname "$browser_path")
        echo "Setting permissions in $chrome_dir"
        
        # Fix permissions for the entire chrome-linux directory
        chmod -R u+rwX,go+rX "$chrome_dir"
        # Ensure the chrome binary is executable
        chmod 755 "$browser_path"
        
        # Set up Chrome sandbox
        sandbox_dir="/tmp/.chrome-sandbox"
        if [ ! -d "$sandbox_dir" ]; then
            mkdir -p "$sandbox_dir"
        fi
        chown root:root "$sandbox_dir"
        chmod 4755 "$sandbox_dir"
        
        # Set special capabilities for Chrome
        setcap cap_net_raw,cap_net_admin,cap_net_bind_service=+ep "$browser_path"
        
        echo "Chrome sandbox configured at $sandbox_dir"
        echo "Browser permissions:"
        ls -la "$browser_path"
        getcap "$browser_path"
    else
        echo "✗ ERROR: Failed to install Playwright browsers"
        echo "Contents of /ms-playwright:"
        ls -la /ms-playwright
        exit 1
    fi
else
    echo "✓ Playwright browsers already installed"
    echo "Browser location:"
    find /ms-playwright -name "chrome" -type f -executable
fi

# Check and fix permissions only if directories are empty
# This way we don't modify existing mounted data
for dir in /app/data /app/configs /app/logs; do
    if [ -z "$(ls -A $dir)" ]; then
        echo "Setting permissions for empty directory: $dir"
        chmod 755 "$dir"
    else
        echo "Directory not empty, preserving permissions: $dir"
    fi
done

# Check SQLite database permissions
if [ ! -f /app/data/workday_jobs.db ]; then
    echo "Database file doesn't exist, it will be created with proper permissions"
elif [ ! -r /app/data/workday_jobs.db ] || [ ! -w /app/data/workday_jobs.db ]; then
    echo "Fixing database file permissions"
    chmod 644 /app/data/workday_jobs.db
else
    echo "Database file permissions OK"
fi

# Run database migrations if needed
echo "Checking for database migrations..."
if [ -f /app/data/workday_jobs.db ]; then
    echo "Running database migrations..."
    if ! /usr/local/bin/python /app/scripts/run_migration.py; then
        echo "ERROR: Database migration failed"
        exit 1
    fi
    echo "✅ Database migrations completed successfully"
else
    echo "Database file doesn't exist yet, migrations will be applied when it's created"
fi

# Initialize sample config if needed
if [ ! "$(ls -A /app/configs)" ]; then
    echo "Creating sample config file..."
    echo "autodesk,https://autodesk.wd1.myworkdayjobs.com/Ext" > /app/configs/autodesk.txt
    echo "Created: /app/configs/autodesk.txt"
fi

# Verify environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required"
    exit 1
fi

# Set default config file for the scheduler
CONFIG_FILE=${CONFIG_FILE:-autodesk.txt}
export CONFIG_FILE

# Define cleanup function
cleanup() {
    echo "Received shutdown signal, cleaning up..."
    if [ -f /tmp/telegram_bot.pid ]; then
        kill -SIGTERM $(cat /tmp/telegram_bot.pid) 2>/dev/null || true
    fi
    exit 0
}

# Set trap for cleanup
trap cleanup SIGTERM SIGINT SIGQUIT

# Add the current directory to the Python path
export PYTHONPATH=/app:$PYTHONPATH

# Run the Telegram bot with integrated scheduler
echo "Starting Telegram bot with integrated scheduler..."
echo "Python path: $PYTHONPATH"
if ! /usr/local/bin/python /app/scripts/run_telegram_bot.py \
    -db /app/data/workday_jobs.db \
    -l /app/logs/telegram_bot.log 2>&1 | tee /app/logs/startup_error.log; then
    echo "ERROR: Failed to start Telegram bot"
    echo "Error details:"
    cat /app/logs/startup_error.log
    exit 1
fi
PID=$!
echo $PID > /tmp/telegram_bot.pid

# Verify the bot process started
if ! kill -0 $PID 2>/dev/null; then
    echo "ERROR: Telegram bot process failed to start"
    exit 1
fi

echo "🤖 Workday Scraper is running!"
echo "- Telegram bot is active with integrated scheduler"
echo "- Default config: $CONFIG_FILE"
echo "- Data directory: /app/data"
echo "- Logs directory: /app/logs"
echo "- Use /help to see available commands"
echo "- Use /schedule to view current schedule"
echo "- Use /set_schedule to modify schedule"

# Monitor the bot process
while true; do
    if ! kill -0 $PID 2>/dev/null; then
        echo "Telegram bot has stopped, restarting..."
        echo "Restarting with Python path: $PYTHONPATH"
        if ! /usr/local/bin/python /app/scripts/run_telegram_bot.py \
            -db /app/data/workday_jobs.db \
            -l /app/logs/telegram_bot.log & then
            echo "ERROR: Failed to restart Telegram bot"
            continue
        fi
        PID=$!
        echo $PID > /tmp/telegram_bot.pid
        
        # Verify the restart
        if ! kill -0 $PID 2>/dev/null; then
            echo "ERROR: Telegram bot failed to restart"
            continue
        fi
        echo "✅ Telegram bot successfully restarted"
    fi
    sleep 60
done
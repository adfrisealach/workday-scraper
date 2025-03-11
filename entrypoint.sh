#!/bin/sh
set -e

# Ensure we're in the correct directory
cd /app || exit 1

# Create necessary directories
mkdir -p /app/data /app/configs /app/logs

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

# Run the Telegram bot with integrated scheduler
echo "Starting Telegram bot with integrated scheduler..."
if ! /usr/local/bin/python /app/run_telegram_bot.py \
    -db /app/data/workday_jobs.db \
    -l /app/logs/telegram_bot.log & then
    echo "ERROR: Failed to start Telegram bot"
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
        if ! /usr/local/bin/python /app/run_telegram_bot.py \
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
#!/bin/bash

# Load environment variables from config/.env.test
export $(cat ../config/.env.test | grep -v '^#' | xargs)

# Print loaded configuration
echo "Loaded test configuration:"
echo "- Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}... (truncated)"
echo "- Chat ID: $TELEGRAM_CHAT_ID"
echo "- Schedule: $SCHEDULE_HOUR:$SCHEDULE_MINUTE $SCHEDULE_TIMEZONE"
echo "- Config File: $CONFIG_FILE"
echo

# Run the bot
echo "Starting Telegram bot..."
python ../scripts/run_telegram_bot.py \
    -db "$DB_FILE" \
    -l "$LOG_FILE" \
    -ll "$LOG_LEVEL"
#!/usr/bin/env python
"""
Standalone script to run the Telegram bot for the Workday Scraper.

This script initializes and runs the Telegram bot, allowing users to
interact with it via commands without running a scrape job.
"""

import os
import sys
import asyncio
import logging
from argparse import ArgumentParser

from workday_scraper.db_manager import DatabaseManager
from workday_scraper.telegram_bot import initialize_bot, get_bot_instance
from workday_scraper.logging_utils import configure_logger, get_logger


async def main():
    """Main entry point for the standalone Telegram bot."""
    parser = ArgumentParser(description="Workday Scraper Telegram Bot")
    parser.add_argument(
        "-db", "--db-file", 
        dest="db_file", 
        type=str,
        default="workday_jobs.db",
        help="Path to the SQLite database file (default: workday_jobs.db)"
    )
    parser.add_argument(
        "-l", "--log-file", 
        dest="log_file", 
        type=str,
        default="telegram_bot.log",
        help="Path to the log file (default: telegram_bot.log)"
    )
    parser.add_argument(
        "-ll", "--log-level", 
        dest="log_level", 
        type=str,
        default="INFO", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Environment paths for Docker
    default_db_path = "/app/data/workday_jobs.db"
    default_log_path = "/app/logs/telegram_bot.log"
    
    # Get configuration from environment variables first, fallback to command line args
    db_file = os.environ.get("DB_FILE", default_db_path if os.path.exists("/app") else args.db_file)
    log_file = os.environ.get("LOG_FILE", default_log_path if os.path.exists("/app") else args.log_file)
    log_level = os.environ.get("LOG_LEVEL", args.log_level)

    # Configure logging first
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    configure_logger(log_file=log_file, log_level=numeric_level)
    logger = get_logger()

    # Now we can log
    logger.info(f"Using database path: {db_file}")
    logger.info(f"Using log file path: {log_file}")

    # Check for required environment variables
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    config_dir = os.environ.get("CONFIG_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs"))
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
        print("Error: TELEGRAM_BOT_TOKEN environment variable is not set")
        print("Please set it to your Telegram bot token from BotFather")
        print("Example: export TELEGRAM_BOT_TOKEN=your_token_here")
        return 1
    
    if not chat_id:
        logger.error("TELEGRAM_CHAT_ID environment variable is not set")
        print("Error: TELEGRAM_CHAT_ID environment variable is not set")
        print("Please set it to your Telegram chat ID")
        print("Example: export TELEGRAM_CHAT_ID=your_chat_id_here")
        return 1
    
    # Initialize database manager
    db_manager = DatabaseManager(db_file=db_file)
    logger.info(f"Connected to database: {db_file}")
    
    # Initialize Telegram bot
    try:
        bot = await initialize_bot(db_manager)
        logger.info("Telegram bot initialized")
        
        # Print success message with instructions
        print(f"Telegram bot started successfully")
        print(f"Log file: {log_file}")
        print(f"Using database: {db_file}")
        print("\nAvailable commands:")
        print("- /start - Get started with the bot")
        print("- /help - Show available commands")
        print("- /jobs_by_location - Get job count by Country and State")
        print("- /top_job_titles - Get top 10 job titles with posting counts")
        print("- /search_jobs <keyword> - Search for jobs with title containing a keyword and see locations")
        print("- /run_scrape <config_file> - Manually trigger the scraper")
        print("- /list_configs - List available config files")
        print("- /scrape_status - Check status of running scrape jobs")
        print("\nPress Ctrl+C to stop the bot")
        
        # Start the bot
        await bot.start_polling()
        
        # Keep the bot running until interrupted
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Error running Telegram bot: {str(e)}")
        print(f"Error running Telegram bot: {str(e)}")
        return 1
    finally:
        # Stop the bot and close database connection
        bot = get_bot_instance()
        if bot and hasattr(bot, "stop"):
            await bot.stop()
        
        db_manager.close()
        logger.info("Bot stopped and database connection closed")
    
    return 0


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
"""
Telegram bot module for the Workday Scraper.

This module provides functionality for sending notifications via Telegram
when scrapes complete and for interacting with the scraper via commands.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler

from .db_manager import DatabaseManager
from .logging_utils import get_logger
from .scheduler import get_scheduler

logger = get_logger()


class TelegramBot:
    """Telegram bot for interacting with the Workday Scraper."""
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize the TelegramBot.
        
        Args:
            db_manager (DatabaseManager, optional): The database manager instance.
                If not provided, a new one will be created.
        """
        # Get token and chat ID from environment variables
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram notifications will not be available.")
            self.enabled = False
            return
            
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not set. Telegram notifications will not be available.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # Initialize database manager if not provided
        self.db_manager = db_manager or DatabaseManager()
        
        # Get config directory from environment or default to /app/configs for Docker
        self.config_dir = os.environ.get("CONFIG_DIR", "/app/configs")
        logger.info(f"Using config directory: {self.config_dir}")
        if not os.path.exists(self.config_dir):
            logger.error(f"Config directory not found: {self.config_dir}")
        
        # Store running scrape jobs
        self.running_jobs = {}
        # Store job title mappings for search feature
        self.job_title_mappings = {}
        
        # Initialize scheduler
        self.scheduler = get_scheduler()
        
        logger.info("Telegram bot initialized with scheduler")
        
    async def initialize(self):
        """Initialize the Telegram bot application and handlers."""
        if not self.enabled:
            logger.warning("Telegram bot not enabled. Skipping initialization.")
            return
            
        try:
            # Initialize the bot application
            self.application = Application.builder().token(self.token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.handle_start))
            self.application.add_handler(CommandHandler("help", self.handle_help))
            self.application.add_handler(CommandHandler("jobs_by_location", self.handle_jobs_by_location))
            self.application.add_handler(CommandHandler("jobs_at_location", self.handle_jobs_at_location))
            self.application.add_handler(CommandHandler("top_job_titles", self.handle_top_job_titles))
            self.application.add_handler(CommandHandler("run_scrape", self.handle_run_scrape))
            self.application.add_handler(CommandHandler("list_configs", self.handle_list_configs))
            self.application.add_handler(CommandHandler("scrape_status", self.handle_scrape_status))
            self.application.add_handler(CommandHandler("search_jobs", self.handle_search_jobs))
            
            # Add scheduler command handlers
            self.application.add_handler(CommandHandler("schedule", self.handle_view_schedule))
            self.application.add_handler(CommandHandler("set_schedule", self.handle_set_schedule))
            
            # Add callback query handler for interactive buttons
            self.application.add_handler(CallbackQueryHandler(self.handle_button_click))
            
            logger.info("Telegram bot application initialized with command handlers")
        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {str(e)}")
            self.enabled = False
    
    async def start_polling(self):
        """Start polling for updates."""
        if not self.enabled:
            logger.warning("Telegram bot not enabled. Skipping polling.")
            return
            
        try:
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Start the scheduler
            await self.scheduler.start()
            
            logger.info("Telegram bot and scheduler started")
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {str(e)}")
            self.enabled = False
    
    async def stop(self):
        """Stop the bot."""
        if not self.enabled or not hasattr(self, "application"):
            return
            
        try:
            # Stop the scheduler first
            await self.scheduler.stop()
            
            # Stop the bot
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            logger.info("Telegram bot and scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {str(e)}")
    
    async def send_notification(self, jobs: List[Dict[str, Any]]):
        """Send a notification about completed scraping.
        
        Args:
            jobs (list): List of scraped job dictionaries.
        """
        if not self.enabled:
            logger.warning("Telegram bot not enabled. Skipping notification.")
            return
            
        if not jobs:
            logger.info("No jobs to send notification for")
            return
            
        try:
            # Get unique companies
            companies = {}
            for job in jobs:
                company = job.get("company", "Unknown")
                if company in companies:
                    companies[company] += 1
                else:
                    companies[company] = 1
            
            # Get top locations
            locations = {}
            for job in jobs:
                location = job.get("location", "Unknown")
                if location in locations:
                    locations[location] += 1
                else:
                    locations[location] = 1
            
            # Sort locations by count
            sorted_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)
            top_locations = sorted_locations[:3]
            other_count = sum(count for _, count in sorted_locations[3:])
            
            # Format the summary message
            message = f"✅ Scrape Completed\n"
            message += f"- {len(jobs)} new jobs found\n"
            
            # Add companies
            message += f"- Companies: "
            message += ", ".join([f"{company} ({count})" for company, count in companies.items()])
            message += "\n"
            
            # Add top locations
            message += f"- Top locations: "
            message += ", ".join([f"{location} ({count})" for location, count in top_locations])
            if other_count > 0:
                message += f", Other ({other_count})"
            message += "\n\n"
            
            # Add command suggestions
            message += "Use /jobs_by_location for detailed location breakdown\n"
            message += "Use /top_job_titles to see the most common positions"
            
            # Send the summary message
            async with self.application.bot:
                await self.application.bot.send_message(chat_id=self.chat_id, text=message)
            
            # Prepare detailed job listings message
            if jobs:
                await self._send_job_details(jobs)
            
            logger.info(f"Sent Telegram notification for {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
    
    async def _send_job_details(self, jobs: List[Dict[str, Any]]):
        """Send detailed information about each job.
        
        Args:
            jobs (list): List of scraped job dictionaries.
        """
        if not jobs:
            return
            
        try:
            # Start the job details message
            details_message = f"📋 *New Job Listings:*\n\n"
            
            # Telegram has a message limit of ~4096 characters
            # We'll track the length and split into multiple messages if needed
            current_message = details_message
            message_part = 1
            
            # Add each job to the message
            for job in jobs:
                title = job.get("title", "Unknown Title")
                location = job.get("location", "Unknown Location")
                company = job.get("company", "")
                
                # Format the job entry
                job_entry = f"• *{title}* | {location}\n"
                
                # Check if adding this job would exceed Telegram's limit
                if len(current_message) + len(job_entry) > 4000:
                    # Send the current message
                    async with self.application.bot:
                        await self.application.bot.send_message(
                            chat_id=self.chat_id,
                            text=current_message,
                            parse_mode="Markdown"
                        )
                    
                    # Start a new message
                    message_part += 1
                    current_message = f"📋 *New Job Listings (Continued {message_part}):*\n\n"
                
                # Add the job to the current message
                current_message += job_entry
            
            # Send the final message (if not empty)
            if current_message != details_message and current_message != f"📋 *New Job Listings (Continued {message_part}):*\n\n":
                async with self.application.bot:
                    await self.application.bot.send_message(
                        chat_id=self.chat_id,
                        text=current_message,
                        parse_mode="Markdown"
                    )
                    
            logger.info(f"Sent detailed job listings in {message_part} message(s)")
        except Exception as e:
            logger.error(f"Error sending detailed job listings: {str(e)}")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        user = update.effective_user
        message = (
            f"👋 Hello, {user.first_name}!\n\n"
            "Welcome to the Workday Scraper bot. This bot helps you interact with "
            "the Workday Scraper and get notifications about new job postings.\n\n"
            "Use /help to see available commands."
        )
        await update.message.reply_text(message)
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        message = (
            "🤖 *Workday Scraper Bot Commands*\n\n"
            "*/jobs_by_location* - Get job count by Country and State\n"
            "*/jobs_at_location* `<location>` - Get detailed job listings for a specific location\n"
            "   Example: `/jobs_at_location California`\n"
            "*/top_job_titles* - Get top 10 job titles with posting counts\n"
            "*/search_jobs* `<keyword>` - Search for jobs with title containing a keyword and see locations\n"
            "   Example: `/search_jobs data analyst`\n"
            "*/run_scrape* `<config_file> [options]` - Manually trigger the scraper\n"
            "   Example: `/run_scrape autodesk.txt -i`\n"
            "*/list_configs* - List available config files\n"
            "*/scrape_status* - Check status of running scrape jobs\n"
            "*/schedule* - View current scraper schedule\n"
            "*/set_schedule* `<hour> <minute> [timezone]` - Set scraper schedule\n"
            "   Example: `/set_schedule 0 0` for midnight UTC\n"
            "   Example: `/set_schedule 8 30 America/Los_Angeles` for 8:30 AM PT\n"
            "*/help* - Display this help message\n"
        )
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def handle_jobs_by_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /jobs_by_location command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        await update.message.reply_text("Fetching jobs by location... This may take a moment.")
        
        try:
            # Get jobs by location
            location_stats = await self._get_jobs_by_location()
            
            if not location_stats:
                await update.message.reply_text("No job location data available.")
                return
            
            # Format the message
            message = "📊 *Jobs by Location*\n\n"
            
            for country, states in location_stats.items():
                if not states:  # Skip countries with no valid states
                    continue
                    
                total_country = sum(states.values())
                message += f"*{country}* ({total_country})\n"
                
                # Add states, skip empty or Unknown states
                for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
                    if state and state != "Unknown":
                        message += f"• {state} ({count})\n"
                
                message += "\n"
            
            # Add total only if we have jobs to show
            if location_stats:
                total_jobs = sum(sum(states.values()) for states in location_stats.values())
                message += f"*Total*: {total_jobs} jobs"
                
                # Add hint about the new command
                message += "\n\n💡 *Tip:* Use `/jobs_at_location <location>` to see detailed job listings for a specific location."
            
            # Send the message
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error handling jobs_by_location command: {str(e)}")
            await update.message.reply_text(f"Error fetching location data: {str(e)}")
    
    async def handle_jobs_at_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /jobs_at_location command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        if not context.args:
            await update.message.reply_text(
                "Please provide a location.\n"
                "Example: `/jobs_at_location California`\n"
                "Example: `/jobs_at_location United States - California`\n"
                "Use `/jobs_by_location` to see available locations."
            )
            return
        
        location = " ".join(context.args)
        await update.message.reply_text(f"Fetching jobs for location: {location}...")
        
        try:
            jobs = self.db_manager.get_jobs_by_specific_location(location)
            
            if not jobs:
                await update.message.reply_text(f"No jobs found for location: {location}")
                return
            
            # Group jobs by title and company
            jobs_by_title_and_company = {}
            for job in jobs:
                title = job.get('title', 'Unknown Title')
                company = job.get('company', 'Unknown Company')
                
                key = (title, company)
                if key not in jobs_by_title_and_company:
                    jobs_by_title_and_company[key] = {
                        'count': 0,
                        'url': job.get('url', '')  # Store one URL for reference
                    }
                
                jobs_by_title_and_company[key]['count'] += 1
            
            # Calculate total for summary
            unique_companies = len(set(company for (_, company), _ in jobs_by_title_and_company.items()))
            total_summary = f"*Total*: {len(jobs)} jobs from {unique_companies} companies matching '{location}'"
            
            # Format the message with pagination support
            # Start with header message
            header_message = f"📍 *Jobs in {location}*\n\n"
            
            # Telegram has a message limit of ~4096 characters
            # We'll track the length and split into multiple messages if needed
            current_message = header_message
            message_part = 1
            job_count = 0
            max_message_length = 4000  # Leave some buffer for Markdown formatting
            
            # Add each job with company and URL
            for (title, company), details in sorted(jobs_by_title_and_company.items()):
                count = details['count']
                url = details['url']
                
                count_text = f"{count} positions" if count > 1 else "1 position"
                job_entry = f"• *{title}* - {company} ({count_text})\n"
                if url:
                    job_entry += f"  [View Job]({url})\n"
                
                job_entry += "\n"
                
                # Check if adding this job would exceed Telegram's limit
                if len(current_message) + len(job_entry) > max_message_length:
                    # Add partial summary to current message
                    if message_part == 1:
                        current_message += f"(Continued in next message...)\n"
                    else:
                        current_message += f"(Part {message_part} of {message_part+1}...)\n"
                    
                    # Send the current message
                    await update.message.reply_text(current_message, parse_mode="Markdown", disable_web_page_preview=True)
                    
                    # Start a new message
                    message_part += 1
                    current_message = f"📍 *Jobs in {location} (Part {message_part})*\n\n"
                
                # Add the job to the current message
                current_message += job_entry
                job_count += 1
            
            # Add summary to final message
            if current_message != header_message and current_message != f"📍 *Jobs in {location} (Part {message_part})*\n\n":
                current_message += total_summary
                
                # Send the final message
                await update.message.reply_text(current_message, parse_mode="Markdown", disable_web_page_preview=True)
            
            logger.info(f"Sent jobs for location '{location}' in {message_part} message(s)")
        except Exception as e:
            logger.error(f"Error handling jobs_at_location command: {str(e)}")
            await update.message.reply_text(f"Error fetching jobs: {str(e)}")
    
    async def handle_top_job_titles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /top_job_titles command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        await update.message.reply_text("Fetching top job titles... This may take a moment.")
        
        try:
            # Get top job titles
            limit = 10
            job_titles = await self._get_top_job_titles(limit)
            
            if not job_titles:
                await update.message.reply_text("No job title data available.")
                return
            
            # Format the message
            message = "🏆 *Top Job Titles:*\n\n"
            
            for i, (title, count) in enumerate(job_titles, 1):
                message += f"{i}. {title}: {count} postings\n"
            
            # Send the message
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error handling top_job_titles command: {str(e)}")
            await update.message.reply_text(f"Error fetching job title data: {str(e)}")
    
    async def handle_run_scrape(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /run_scrape command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        # Check if update contains a message
        if not update.message:
            logger.error("Received update without message")
            return
            
        if not context.args:
            await update.message.reply_text(
                "Please provide a config file name.\n"
                "Example: `/run_scrape autodesk.txt`\n"
                "Use `/list_configs` to see available config files."
            )
            return
        
        config_file = context.args[0]
        options = context.args[1:] if len(context.args) > 1 else []
        
        # Check if the config file exists
        config_path = os.path.join(self.config_dir, config_file)
        if not os.path.exists(config_path):
            await update.message.reply_text(
                f"Config file '{config_file}' not found in {self.config_dir}.\n"
                "Use `/list_configs` to see available config files."
            )
            return
        
        # Parse options
        args = {
            "file": config_file,
            "initial": "-i" in options or "--initial" in options,
            "json": "-j" in options or "--json" in options,
            "rss": "-rs" in options or "--rss" in options,
        }
        
        await update.message.reply_text(
            f"Starting scrape job with config '{config_file}'...\n"
            f"Options: {', '.join(f'{k}={v}' for k, v in args.items() if k != 'file')}"
        )
        
        # Start the scrape job in a new task
        job_id = f"{config_file}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.running_jobs[job_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "config_file": config_file,
            "options": options,
            "user_id": update.effective_user.id,
            "chat_id": update.effective_chat.id,
        }
        
        # Run the scrape job in a separate task
        asyncio.create_task(self._run_scrape_job(job_id, args, update, context))
    
    async def handle_list_configs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /list_configs command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        try:
            # List config files
            if not os.path.exists(self.config_dir):
                await update.message.reply_text(f"Config directory {self.config_dir} not found.")
                return
            
            config_files = [f for f in os.listdir(self.config_dir) if f.endswith(".txt")]
            
            if not config_files:
                await update.message.reply_text("No config files found.")
                return
            
            # Format the message
            message = "📁 *Available config files:*\n\n"
            
            for i, config in enumerate(sorted(config_files), 1):
                message += f"{i}. `{config}`\n"
            
            message += "\nUse `/run_scrape <config_file>` to start a scrape job."
            
            # Send the message
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error handling list_configs command: {str(e)}")
            await update.message.reply_text(f"Error listing config files: {str(e)}")
    
    async def handle_scrape_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /scrape_status command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        if not self.running_jobs:
            await update.message.reply_text("No active scrape jobs.")
            return
        
        # Format the message
        message = "🔄 *Active Scrape Jobs:*\n\n"
        
        for job_id, job_info in self.running_jobs.items():
            status = job_info.get("status", "unknown")
            started_at = job_info.get("started_at", "unknown")
            config_file = job_info.get("config_file", "unknown")
            
            # Calculate duration
            if started_at != "unknown":
                start_time = datetime.fromisoformat(started_at)
                duration = datetime.now() - start_time
                duration_str = str(duration).split(".")[0]  # Remove microseconds
            else:
                duration_str = "unknown"
            
            message += f"*Job ID*: `{job_id}`\n"
            message += f"*Config*: {config_file}\n"
            message += f"*Status*: {status}\n"
            message += f"*Started*: {started_at}\n"
            message += f"*Running for*: {duration_str}\n\n"
        
        # Send the message
        await update.message.reply_text(message, parse_mode="Markdown")

    async def handle_view_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /schedule command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        if not update.message:
            logger.error("Received update without message for schedule command")
            return
            
        schedule = self.scheduler.get_schedule()
        
        # Format the schedule message
        message = "📅 *Current Schedule*\n\n"
        message += f"• Hour: {schedule['hour']}\n"
        message += f"• Minute: {schedule['minute']}\n"
        message += f"• Timezone: {schedule['timezone']}\n"
        message += f"• Next Run: {schedule['next_run']}\n"
        message += f"• Status: {'Active' if schedule['is_running'] else 'Inactive'}\n\n"
        message += "Use `/set_schedule hour minute [timezone]` to update"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def handle_set_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /set_schedule command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        if not update.message:
            logger.error("Received update without message for set_schedule command")
            return
            
        # Log the raw message for debugging
        logger.info(f"Received set_schedule command. Raw message text: {update.message.text}")
        logger.info(f"Message entities: {update.message.entities}")
            
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Please provide hour and minute.\n"
                "Example: `/set_schedule 0 0` for midnight\n"
                "Example: `/set_schedule 8 30 America/Los_Angeles` for 8:30 AM PT",
                parse_mode="Markdown"
            )
            return
            
        try:
            # Log the raw arguments
            logger.info(f"Processing schedule arguments: {context.args}")
            
            # Log each argument's format
            for i, arg in enumerate(context.args):
                logger.info(f"Argument {i} type: {type(arg)}, value: {arg}, length: {len(arg)}")
            
            # Parse hour and minute with validation
            hour = int(context.args[0])
            logger.info(f"Parsed hour: {hour}")
            
            minute = int(context.args[1])
            logger.info(f"Parsed minute: {minute}")
            
            # Handle timezone with careful parsing
            timezone = None
            if len(context.args) > 2:
                timezone = context.args[2]
                logger.info(f"Using timezone: {timezone}")
            
            if not (0 <= hour <= 23):
                await update.message.reply_text("Hour must be between 0 and 23")
                return
                
            if not (0 <= minute <= 59):
                await update.message.reply_text("Minute must be between 0 and 59")
                return
            
            schedule = self.scheduler.update_schedule(hour=hour, minute=minute, timezone=timezone)
            
            try:
                # Format the response message carefully escaping special characters
                message = "✅ Schedule Updated\n\n"
                message += f"• Hour: {schedule['hour']}\n"
                message += f"• Minute: {schedule['minute']}\n"
                message += f"• Timezone: {schedule['timezone']}\n"
                message += f"• Next Run: {schedule['next_run']}"
                
                logger.info(f"Sending response message: {message}")
                
                # Send without Markdown parsing first to test
                await update.message.reply_text(message)
                
            except Exception as e:
                logger.error(f"Error sending schedule response: {str(e)}", exc_info=True)
                # Fallback to plain text if formatting fails
                await update.message.reply_text(f"Schedule updated: {schedule['hour']}:{schedule['minute']} {schedule['timezone']}")
            
        except ValueError as e:
            await update.message.reply_text(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error setting schedule: {str(e)}")
            await update.message.reply_text(f"Error setting schedule: {str(e)}")
    
    async def handle_search_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /search_jobs command.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        # Check if keyword was provided
        if not context.args:
            await update.message.reply_text(
                "Please provide a job title to search for.\n"
                "Example: `/search_jobs data analyst`"
            )
            return
        
        # Get the job title
        job_title = " ".join(context.args)
        
        await update.message.reply_text(f"Searching for jobs with title containing '{job_title}'...")
        
        try:
            # Get detailed job information including posting dates
            search_result = self.db_manager.search_jobs_with_details(job_title)
            
            if not search_result or not search_result['jobs_by_title']:
                await update.message.reply_text(f"No jobs found with title containing '{job_title}'.")
                return
            
            jobs_by_title = search_result['jobs_by_title']
            title_recency = search_result['title_recency']
            
            # Calculate totals
            total_jobs = sum(len(jobs) for jobs in jobs_by_title.values())
            total_titles = len(jobs_by_title)
            
            # Get all unique locations
            all_locations = {}
            for jobs in jobs_by_title.values():
                for job in jobs:
                    location = job.get('location') or "Unknown"
                    if location not in all_locations:
                        all_locations[location] = 0
                    all_locations[location] += 1
            
            # Format the main message
            message = f"🔍 *Jobs Matching '{job_title}'*\n\n"
            message += f"Found {total_jobs} jobs matching your search across {total_titles} job titles and {len(all_locations)} locations.\n\n"
            
            # Sort titles by recency (most recent first)
            sorted_titles = sorted(title_recency.items(), key=lambda x:
                                  10000 if x[1] == 'unknown' else x[1])
            
            # Telegram has a message limit of ~4096 characters
            current_message = message
            message_part = 1
            
            for i, (title, recency) in enumerate(sorted_titles):
                jobs = jobs_by_title[title]
                
                # Find the most recent job with a URL to use as representative link
                representative_job = None
                for job in jobs:
                    if job.get('url'):
                        representative_job = job
                        break
                
                # Format title block
                title_block = ""
                # Add a blank line between job titles (except for the first one)
                if i > 0:
                    title_block += "\n"
                
                # Format job title line without listing age
                title_block += f"• *{title}*: {len(jobs)} jobs"
                
                # Add link to the job if available
                if representative_job and representative_job.get('url'):
                    title_block += f" - [View Job]({representative_job['url']})\n"
                else:
                    title_block += "\n"
                
                # Group jobs by country and state with simplified posting info
                jobs_by_location = {}
                for job in jobs:
                    full_location = job.get('location') or "Unknown"
                    simplified_location = self._simplify_location_for_search(full_location)
                    
                    if simplified_location not in jobs_by_location:
                        jobs_by_location[simplified_location] = {
                            'count': 0,
                            'most_recent': 10000,  # Default to very old
                            'companies': set(),
                        }
                    
                    jobs_by_location[simplified_location]['count'] += 1
                    jobs_by_location[simplified_location]['companies'].add(job.get('company', 'Unknown'))
                    
                    # Track the most recent job for this location
                    days_ago = job.get('days_ago')
                    if days_ago != 'unknown' and days_ago < jobs_by_location[simplified_location]['most_recent']:
                        jobs_by_location[simplified_location]['most_recent'] = days_ago
                
                # Add location details with simplified posting info
                for location, location_info in sorted(jobs_by_location.items(), key=lambda x: x[1]['count'], reverse=True):
                    location_block = f"  - {location}: {location_info['count']} jobs"
                    
                    # Don't include posting date information
                    
                    # Add company info if there are multiple companies
                    companies = location_info['companies']
                    if len(companies) > 1:
                        location_block += f" - {len(companies)} companies"
                    elif len(companies) == 1:
                        location_block += f" - {next(iter(companies))}"
                    
                    location_block += "\n"
                    
                    # Check if adding this block would exceed Telegram's limit
                    if len(current_message) + len(title_block) + len(location_block) > 4000:
                        # Send the current message
                        await update.message.reply_text(
                            current_message,
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                        
                        # Start a new message
                        message_part += 1
                        current_message = f"🔍 *Jobs Matching '{job_title}' (Part {message_part})*\n\n"
                        
                        # Reset the title block (without the blank line at the beginning)
                        title_block = title_block.lstrip('\n')
                    
                    title_block += location_block
                
                # Check if adding the entire title block would exceed limit
                if len(current_message) + len(title_block) > 4000:
                    # Send current message before adding new title block
                    await update.message.reply_text(
                        current_message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                    
                    # Start a new message
                    message_part += 1
                    current_message = f"🔍 *Jobs Matching '{job_title}' (Part {message_part})*\n\n"
                
                current_message += title_block
            
            # Send the final message if not empty
            if current_message != message and current_message != f"🔍 *Jobs Matching '{job_title}' (Part {message_part})*\n\n":
                await update.message.reply_text(
                    current_message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                
            logger.info(f"Sent search results for '{job_title}' in {message_part} message(s)")
        except Exception as e:
            logger.error(f"Error handling search_jobs command: {str(e)}")
            await update.message.reply_text(f"Error searching for jobs: {str(e)}")
    
    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks from inline keyboards.
        
        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        query = update.callback_query
        await query.answer()  # Acknowledge the button click
        
        # Get the callback data
        callback_data = query.data
        
        try:
            if callback_data.startswith("loc:"):
                # Extract the search_id and index from callback data
                # Format is "loc:{search_id}:{index}"
                parts = callback_data.split(":")
                if len(parts) != 3:
                    await query.edit_message_text("Invalid callback data format.")
                    return
                
                search_id = parts[1]
                index = parts[2]
                
                # Retrieve the job title from our mappings
                if (search_id in self.job_title_mappings and
                    index in self.job_title_mappings[search_id]):
                    
                    job_title = self.job_title_mappings[search_id][index]
                    
                    # Get locations for this job title
                    await query.edit_message_text(f"Fetching locations for '{job_title}'...")
                    
                    # Get locations for the job title
                    locations = await self._get_locations_for_job_title(job_title)
                    
                    # Clean up the mapping after use
                    self._cleanup_job_title_mapping(search_id)
                else:
                    await query.edit_message_text("Error: Job title information not found. Please try searching again.")
                    return
                
                if not locations:
                    await query.edit_message_text(f"No locations found for '{job_title}'.")
                    return
                
                # Format the message
                message = f"📍 *Locations for '{job_title}'*\n\n"
                
                for location, count in locations:
                    message += f"• {location}: {count}\n"
                
                # Add a total count
                total = sum(count for _, count in locations)
                message += f"\n*Total*: {total} positions"
                
                # Send the message
                await query.edit_message_text(
                    message,
                    parse_mode="Markdown"
                )
            else:
                # Unknown callback data
                await query.edit_message_text(f"Unsupported button action: {callback_data}")
        except Exception as e:
            logger.error(f"Error handling button click: {str(e)}")
            await query.edit_message_text(f"Error processing your request: {str(e)}")
    
    async def _run_scrape_job(self, job_id: str, args: Dict[str, Any], update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run a scrape job asynchronously.
        
        Args:
            job_id (str): The job ID.
            args (dict): The scraper arguments.
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        try:
            # Update job status to running
            await update.message.reply_text(f"Running scrape job '{job_id}'...")
            self.running_jobs[job_id]["status"] = "running"
            
            import sys
            import subprocess
            
            # Build the command to run the scraper
            config_file = args.get("file")
            # Log scraper configuration
            config_path = os.path.join(self.config_dir, config_file)
            logger.info(f"Starting scrape with config from: {config_path}")
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    logger.info(f"Config file contents:\n{f.read()}")
            else:
                logger.error(f"Config file not found at: {config_path}")
                await update.message.reply_text(f"Error: Config file not found at {config_path}")
                return
            
            # Use full path to config file
            config_path = os.path.join(self.config_dir, config_file)
            
            # Get database and log file paths from environment variables
            db_file = os.environ.get('DB_FILE', '/app/data/workday_jobs.db')
            log_file = os.environ.get('LOG_FILE', '/app/logs/workday_scraper.log')
            
            # Build command with explicit paths
            cmd_parts = [
                sys.executable,
                "-m",
                "workday_scraper",
                "-f", config_path,
                "-db", db_file,
                "-l", log_file
            ]
            
            # Log command configuration
            logger.info(f"Python executable: {sys.executable}")
            logger.info(f"Working directory: {os.getcwd()}")
            logger.info(f"Database file: {db_file}")
            logger.info(f"Log file: {log_file}")
            
            # Add optional arguments
            if args.get("initial"):
                cmd_parts.append("-i")
            if args.get("json"):
                cmd_parts.append("-j")
            if args.get("rss"):
                cmd_parts.append("-rs")
            
            logger.info(f"Running command: {' '.join(cmd_parts)}")
            # Run the command with verbose output
            logger.info(f"Running command: {' '.join(cmd_parts)}")
            
            # Ensure all necessary environment variables are explicitly passed
            env_vars = {
                **os.environ,
                'PYTHONUNBUFFERED': '1',
                'LOG_LEVEL': 'DEBUG',
                'DB_FILE': os.environ.get('DB_FILE', '/app/data/workday_jobs.db'),
                'LOG_FILE': os.environ.get('LOG_FILE', '/app/logs/workday_scraper.log'),
                'PLAYWRIGHT_BROWSERS_PATH': '/ms-playwright',
                'DATA_DIR': os.environ.get('DATA_DIR', '/app/data'),
                'CONFIG_DIR': os.environ.get('CONFIG_DIR', '/app/configs'),
                'LOG_DIR': os.environ.get('LOG_DIR', '/app/logs')
            }
            
            logger.info(f"Environment variables: DB_FILE={env_vars['DB_FILE']}, LOG_FILE={env_vars['LOG_FILE']}, DATA_DIR={env_vars['DATA_DIR']}, CONFIG_DIR={env_vars['CONFIG_DIR']}, LOG_DIR={env_vars['LOG_DIR']}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env_vars,
                cwd='/app'  # Explicitly set working directory to /app
            )
            
            # Define callback functions with proper log level handling
            def log_stdout(text):
                logger.info(f"Scraper output: {text}")
                
            def log_stderr(text):
                # Parse the log level from the message if possible
                if "[INFO]" in text:
                    logger.info(f"Scraper: {text}")
                elif "[WARNING]" in text:
                    logger.warning(f"Scraper: {text}")
                elif "[DEBUG]" in text:
                    logger.debug(f"Scraper: {text}")
                else:
                    # Default to error for any other messages
                    logger.error(f"Scraper error: {text}")
            
            # Stream output in real-time
            async def read_stream(stream, callback):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode('utf-8').strip()
                    if text:
                        callback(text)
                        
            # Create tasks to read both stdout and stderr
            stdout_task = asyncio.create_task(read_stream(process.stdout, log_stdout))
            stderr_task = asyncio.create_task(read_stream(process.stderr, log_stderr))
            
            # Wait for the process and streams to complete
            await asyncio.gather(stdout_task, stderr_task)
            await process.wait()
            
            # Get the final output for summary
            stdout = await process.stdout.read()
            stderr = await process.stderr.read()
            
            # Check the result
            if process.returncode == 0:
                # Process succeeded
                stdout_text = stdout.decode('utf-8')
                
                # Try to extract the number of jobs found
                import re
                jobs_count = 0
                match = re.search(r"Found (\d+) jobs", stdout_text)
                if match:
                    jobs_count = int(match.group(1))
                
                # Update job status
                self.running_jobs[job_id]["status"] = "completed"
                self.running_jobs[job_id]["completed_at"] = datetime.now().isoformat()
                self.running_jobs[job_id]["result"] = {
                    "jobs_count": jobs_count,
                    "stdout": stdout_text[:1000] if len(stdout_text) > 1000 else stdout_text
                }
                
                # Send a completion message
                message = (
                    f"✅ Scrape job '{job_id}' completed successfully.\n"
                    f"Found {jobs_count} jobs."
                )
            else:
                # Process failed
                stderr_text = stderr.decode('utf-8')
                error_msg = stderr_text[:500] if len(stderr_text) > 500 else stderr_text
                
                # Update job status
                self.running_jobs[job_id]["status"] = "failed"
                self.running_jobs[job_id]["error"] = error_msg
                
                # Send an error message
                message = (
                    f"❌ Error running scrape job '{job_id}':\n{error_msg}"
                )
            
            await update.message.reply_text(message)
            
            # Clean up the job after a delay
            asyncio.create_task(self._cleanup_job(job_id, delay=3600))  # Clean up after 1 hour
        except Exception as e:
            logger.error(f"Error running scrape job {job_id}: {str(e)}")
            
            # Update job status
            self.running_jobs[job_id]["status"] = "failed"
            self.running_jobs[job_id]["error"] = str(e)
            
            # Send an error message
            await update.message.reply_text(
                f"❌ Error running scrape job '{job_id}':\n{str(e)}"
            )
            
            # Clean up the job after a delay
            asyncio.create_task(self._cleanup_job(job_id, delay=3600))  # Clean up after 1 hour
    
    async def _cleanup_job(self, job_id: str, delay: int = 0):
        """Clean up a completed job after a delay.
        
        Args:
            job_id (str): The job ID.
            delay (int): The delay in seconds before cleanup.
        """
        if delay > 0:
            await asyncio.sleep(delay)
        
        if job_id in self.running_jobs:
            del self.running_jobs[job_id]
            logger.info(f"Cleaned up job {job_id}")
    
    async def _get_jobs_by_location(self) -> Dict[str, Dict[str, int]]:
        """Get jobs grouped by location.
        
        Returns:
            dict: A dictionary mapping countries to dictionaries mapping states to counts.
        """
        try:
            # Get all jobs from the database
            all_jobs = self.db_manager.get_all_jobs()
            
            # Group by country and state
            location_stats = {}
            
            for job in all_jobs:
                location = job.get("location", "Unknown")
                if location == "Unknown":
                    continue
                    
                country, state = self._parse_location(location)
                # Clean up location string
                state = state.strip(" -")
                parts = [part.strip() for part in state.split("-")]
                # Remove AMER/APAC prefixes
                if parts and parts[0] in ["AMER", "APAC"]:
                    parts.pop(0)
                state = " - ".join(filter(None, parts))
                
                if country not in location_stats:
                    location_stats[country] = {}
                
                if state and state != "Unknown":
                    if state not in location_stats[country]:
                        location_stats[country][state] = 0
                    location_stats[country][state] += 1
            
            # Sort the dictionaries
            sorted_location_stats = {}
            for country, states in sorted(location_stats.items(), 
                                          key=lambda x: sum(x[1].values()), 
                                          reverse=True):
                sorted_location_stats[country] = dict(
                    sorted(states.items(), key=lambda x: x[1], reverse=True)
                )
            
            return sorted_location_stats
        except Exception as e:
            logger.error(f"Error getting jobs by location: {str(e)}")
            return {}
    
    async def _get_top_job_titles(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the top job titles by count.
        
        Args:
            limit (int): The maximum number of job titles to return.
            
        Returns:
            list: A list of (title, count) tuples.
        """
        try:
            # Get all jobs from the database
            all_jobs = self.db_manager.get_all_jobs()
            
            # Group by job title
            title_counts = {}
            
            for job in all_jobs:
                title = job.get("title", "Unknown")
                # Remove extra spaces and standardize case
                title = " ".join(title.strip().split()).title()
                
                if title not in title_counts:
                    title_counts[title] = 0
                
                title_counts[title] += 1
            
            # Sort and limit
            top_titles = sorted(title_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            return top_titles
        except Exception as e:
            logger.error(f"Error getting top job titles: {str(e)}")
            return []
    
    async def _search_job_titles(self, keyword: str) -> List[Tuple[str, int]]:
        """Search for job titles containing a keyword.
        
        Args:
            keyword (str): The keyword to search for.
            
        Returns:
            list: A list of (title, count) tuples.
        """
        try:
            # Use the database method
            return self.db_manager.search_job_titles_by_keyword(keyword)
        except Exception as e:
            logger.error(f"Error searching job titles by keyword '{keyword}': {str(e)}")
            return []
    
    async def _get_locations_for_job_title(self, job_title: str) -> List[Tuple[str, int]]:
        """Get locations where a specific job title is posted.
        
        Args:
            job_title (str): The job title to search for.
            
        Returns:
            list: A list of (location, count) tuples.
        """
        try:
            # Use the database method
            return self.db_manager.get_locations_for_job_title(job_title)
        except Exception as e:
            logger.error(f"Error getting locations for job title '{job_title}': {str(e)}")
            return []
    
    async def _get_locations_for_job_title_prefix(self, job_title_prefix: str) -> List[Tuple[str, int]]:
        """Get locations for job titles starting with a prefix.
        This is used when job titles are truncated in buttons.
        
        Args:
            job_title_prefix (str): The job title prefix to search for.
            
        Returns:
            list: A list of (location, count) tuples.
        """
        try:
            # Get all jobs from the database
            all_jobs = self.db_manager.get_all_jobs()
            
            # Filter jobs by title prefix
            matching_jobs = [job for job in all_jobs if job.get('title', '').startswith(job_title_prefix)]
            
            # Group by location
            location_counts = {}
            for job in matching_jobs:
                location = job.get('location', 'Unknown') or 'Unknown'
                if location not in location_counts:
                    location_counts[location] = 0
                location_counts[location] += 1
            
            # Convert to list of tuples and sort
            locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
            
            return locations
        except Exception as e:
            logger.error(f"Error getting locations for job title prefix '{job_title_prefix}': {str(e)}")
            return []
    
    def _simplify_location_for_search(self, location: str) -> str:
        """Simplify a location string to just country and state for search results.
        
        Args:
            location (str): The full location string.
            
        Returns:
            str: A simplified location string with just country and state.
        """
        if not location or location == "Unknown":
            return "Unknown"
        
        # Direct pattern matching for common formats
        
        # Pattern: "APAC - India - Bengaluru - Sunriver"
        if location.startswith("APAC - India"):
            return "India"
            
        # Pattern: "EMEA - Poland - Kraków - Lubomirskiego"
        if location.startswith("EMEA - Poland"):
            return "Poland"
            
        # Pattern: "AMER - Canada - Ontario - Toronto"
        if location.startswith("AMER - Canada"):
            return "Canada"
        
        # Pattern: "Canada - AMER - Ontario - Toronto"
        if location.startswith("Canada - AMER"):
            return "Canada"
        
        # General case - extract country from any format
        parts = [part.strip() for part in location.split("-")]
        
        # List of known countries
        known_countries = {
            "US": "United States", "USA": "United States", "United States": "United States",
            "CA": "Canada", "Canada": "Canada",
            "UK": "United Kingdom", "United Kingdom": "United Kingdom",
            "India": "India", "IN": "India",
            "Germany": "Germany", "DE": "Germany",
            "Australia": "Australia", "AU": "Australia",
            "Poland": "Poland", "PL": "Poland",
            "Japan": "Japan", "JP": "Japan",
            "France": "France", "FR": "France",
            "Spain": "Spain", "ES": "Spain",
            "Italy": "Italy", "IT": "Italy"
        }
        
        # First, check for exact country matches in parts
        for part in parts:
            if part in known_countries:
                return known_countries[part]
        
        # If no exact match, use the parsed country from our existing method
        country, state = self._parse_location(location)
        return country
    
    def _parse_location(self, location: str) -> Tuple[str, str]:
        """Parse a location string into country and state.
        
        Args:
            location (str): The location string.
            
        Returns:
            tuple: A (country, state) tuple.
        """
        if not location or location == "Unknown":
            return "Unknown", "Unknown"
        
        # Check for common formats
        # Format: "US-State" or "CA-Province"
        if "-" in location and len(location.split("-")) == 2:
            country, state = location.split("-", 1)
            return self._get_country_name(country), state
        
        # Format: "City, ST, Country"
        if "," in location:
            parts = [part.strip() for part in location.split(",")]
            if len(parts) >= 3:
                # Last part is likely the country
                country = parts[-1]
                state = parts[-2]
                if len(state) == 2:  # Likely a state code
                    return self._get_country_name(country), state
            
            if len(parts) == 2:
                # Second part is likely the state or country
                state = parts[1]
                if len(state) == 2:  # US state code
                    return "United States", state
                return state, parts[0]  # Assume state/country, city
        
        # Format: "Remote - United States" or "Remote - New York"
        if "Remote" in location and "-" in location:
            remote, location = location.split("-", 1)
            location = location.strip()
            
            # Check if it's a country or a state
            if location in {"United States", "USA", "US", "Canada", "UK", "Australia"}:
                country = self._get_country_name(location)
                return country, "Remote"
            
            # Assume it's a state in the US
            return "United States", location
        
        # If there's no clear format, do some guessing
        # Check for known country names or codes
        known_countries = {
            "US": "United States",
            "USA": "United States",
            "United States": "United States",
            "CA": "Canada",
            "Canada": "Canada",
            "UK": "United Kingdom",
            "United Kingdom": "United Kingdom",
            "AU": "Australia",
            "Australia": "Australia",
            "DE": "Germany",
            "Germany": "Germany",
            "FR": "France",
            "France": "France",
            "JP": "Japan",
            "Japan": "Japan",
        }
        
        for code, name in known_countries.items():
            if code in location or name in location:
                # Try to extract state
                for term in [code, name]:
                    if term in location:
                        remaining = location.replace(term, "").strip()
                        if remaining:
                            return name, remaining.strip(" ,-")
                return name, "Unknown"
        
        # Default to treating the whole string as a country
        return location, "Unknown"
    
    def _get_country_name(self, code: str) -> str:
        """Convert a country code to a country name.
        
        Args:
            code (str): The country code.
            
        Returns:
            str: The country name.
        """
        country_map = {
            "US": "United States",
            "USA": "United States",
            "CA": "Canada",
            "UK": "United Kingdom",
            "GB": "United Kingdom",
            "AU": "Australia",
            "DE": "Germany",
            "FR": "France",
            "JP": "Japan",
            "NZ": "New Zealand",
            "IN": "India",
            "BR": "Brazil",
            "MX": "Mexico",
            "ES": "Spain",
            "IT": "Italy",
        }
        
        return country_map.get(code, code)
    
    def _cleanup_job_title_mapping(self, search_id: str):
        """Clean up job title mappings after they are used.
        
        Args:
            search_id (str): The search ID to clean up.
        """
        if search_id in self.job_title_mappings:
            del self.job_title_mappings[search_id]
            logger.debug(f"Cleaned up job title mapping for search ID {search_id}")
    
# Global instance for easy access
_bot_instance = None

def get_bot_instance(db_manager=None) -> TelegramBot:
    """Get or create the global bot instance.
    
    Args:
        db_manager (DatabaseManager, optional): The database manager instance.
        
    Returns:
        TelegramBot: The bot instance.
    """
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot(db_manager)
    return _bot_instance

async def initialize_bot(db_manager=None):
    """Initialize the global bot instance.
    
    Args:
        db_manager (DatabaseManager, optional): The database manager instance.
    """
    bot = get_bot_instance(db_manager)
    await bot.initialize()
    return bot
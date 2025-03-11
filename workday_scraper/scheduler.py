"""
Scheduler module for Workday Scraper.

This module provides scheduling functionality for running the scraper
at configured intervals, with the ability to control scheduling through
the Telegram bot.
"""

import asyncio
import datetime
import logging
import os
from typing import Optional, Dict, Any
import pytz

from .logging_utils import get_logger
logger = get_logger()

from .logging_utils import get_logger
from .scraper_controller import run_scraper

logger = get_logger()

class ScraperScheduler:
    """Scheduler for running the scraper at configured times."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.schedule_hour = int(os.environ.get("SCHEDULE_HOUR", "0"))
        self.schedule_minute = int(os.environ.get("SCHEDULE_MINUTE", "0"))
        self.timezone = pytz.timezone(os.environ.get("SCHEDULE_TIMEZONE", "UTC"))
        self.is_running = False
        self.next_run = None
        self.task = None
        
    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Scheduler started. Next run at {self._get_next_run_time()}")
        
    async def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
        
    def update_schedule(self, hour: int = None, minute: int = None, timezone: str = None) -> Dict[str, Any]:
        """Update the schedule configuration.
        
        Args:
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            timezone: Timezone string (e.g., 'UTC', 'America/Los_Angeles')
            
        Returns:
            dict: Current schedule configuration
        """
        if hour is not None:
            if not 0 <= hour <= 23:
                raise ValueError("Hour must be between 0 and 23")
            self.schedule_hour = hour
            
        if minute is not None:
            if not 0 <= minute <= 59:
                raise ValueError("Minute must be between 0 and 59")
            self.schedule_minute = minute
            
        if timezone:
            try:
                self.timezone = pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f"Unknown timezone: {timezone}")
                
        self.next_run = self._get_next_run_time()
        logger.info(f"Schedule updated. Next run at {self.next_run}")
        
        return self.get_schedule()
        
    def get_schedule(self) -> Dict[str, Any]:
        """Get the current schedule configuration.
        
        Returns:
            dict: Current schedule configuration
        """
        return {
            "hour": self.schedule_hour,
            "minute": self.schedule_minute,
            "timezone": str(self.timezone),
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "is_running": self.is_running
        }
        
    def _get_next_run_time(self) -> datetime.datetime:
        """Calculate the next run time.
        
        Returns:
            datetime: Next scheduled run time
        """
        now = datetime.datetime.now(self.timezone)
        scheduled_time = now.replace(
            hour=self.schedule_hour,
            minute=self.schedule_minute,
            second=0,
            microsecond=0
        )
        
        if scheduled_time <= now:
            scheduled_time += datetime.timedelta(days=1)
            
        return scheduled_time
        
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                now = datetime.datetime.now(self.timezone)
                self.next_run = self._get_next_run_time()
                wait_seconds = (self.next_run - now).total_seconds()
                
                logger.info(f"Waiting {wait_seconds} seconds until next run at {self.next_run}")
                await asyncio.sleep(wait_seconds)
                
                if not self.is_running:
                    break
                    
                logger.info("Starting scheduled scraper run")
                try:
                    # Run the scraper with default config
                    config_file = os.environ.get("CONFIG_FILE", "autodesk.txt")
                    await run_scraper(config_file=config_file)
                    logger.info("Scheduled scraper run completed")
                except Exception as e:
                    logger.error(f"Error in scheduled scraper run: {str(e)}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(60)  # Wait a bit before retrying
                
        self.is_running = False
        logger.info("Scheduler loop ended")
        
# Global instance for easy access
_scheduler_instance = None

def get_scheduler() -> ScraperScheduler:
    """Get or create the global scheduler instance.
    
    Returns:
        ScraperScheduler: The scheduler instance
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ScraperScheduler()
    return _scheduler_instance
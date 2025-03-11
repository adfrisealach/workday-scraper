#!/usr/bin/env python
"""
Test script for the Telegram bot integration.

This script tests the database queries used by the Telegram bot
without actually running the bot or making Telegram API calls.
"""

import asyncio
import sys
from datetime import datetime

from workday_scraper.db_manager import DatabaseManager
from workday_scraper.telegram_bot import TelegramBot
from workday_scraper.logging_utils import configure_logger, get_logger


async def test_database_queries():
    """Test the database queries used by the Telegram bot."""
    # Configure logging
    configure_logger(log_file="test_telegram_bot.log", log_level="INFO")
    logger = get_logger()
    
    # Initialize database manager
    db_manager = DatabaseManager(db_file="workday_jobs.db")
    
    # Print database stats
    try:
        # Get all jobs
        all_jobs = db_manager.get_all_jobs()
        print(f"Database contains {len(all_jobs)} total jobs")
        
        # Companies
        company_counts = db_manager.get_jobs_count_by_company()
        print("\nJobs by Company:")
        for company, count in company_counts.items():
            print(f"  - {company}: {count}")
        
        # Locations
        location_counts = db_manager.get_jobs_by_location()
        print("\nJobs by Location:")
        for location, count in list(location_counts.items())[:10]:  # Show top 10
            print(f"  - {location}: {count}")
        if len(location_counts) > 10:
            print(f"  - ... and {len(location_counts) - 10} more locations")
        
        # Job Titles
        top_titles = db_manager.get_top_job_titles(limit=10)
        print("\nTop 10 Job Titles:")
        for title, count in top_titles:
            print(f"  - {title}: {count}")
        
        print("\nDatabase queries completed successfully")
    except Exception as e:
        print(f"Error testing database queries: {e}")
        logger.error(f"Error testing database queries: {e}")
    finally:
        # Close database connection
        db_manager.close()


async def test_location_parsing():
    """Test the location parsing used by the Telegram bot."""
    # Initialize Telegram bot without enabling it
    bot = TelegramBot()
    
    # Test locations
    test_locations = [
        "US-California",
        "San Francisco, CA, United States",
        "New York, NY",
        "Remote - United States",
        "London, United Kingdom",
        "Toronto, ON, Canada",
        "Sydney, Australia",
        "Berlin, Germany",
        "Unknown"
    ]
    
    print("\nLocation Parsing Test:")
    for location in test_locations:
        country, state = bot._parse_location(location)
        print(f"  - {location} -> {country}, {state}")


async def main():
    """Main entry point for the test script."""
    print("===== Telegram Bot Integration Test =====")
    print(f"Time: {datetime.now().isoformat()}")
    print("Testing database queries...")
    
    await test_database_queries()
    await test_location_parsing()
    
    print("\nTest completed")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
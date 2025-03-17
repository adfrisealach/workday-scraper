"""
Main entry point for the Workday Scraper.

This module provides the main entry point for the Workday Scraper, which
scrapes job postings from Workday sites and outputs them in various formats.
"""

import asyncio
import os
from .parse_args import parse_args
from .scraper_controller import run_scraper
from .logging_utils import configure_logger


async def async_main():
    """Async main entry point for the Workday Scraper."""
    # Parse command-line arguments
    args = parse_args()
    
    # Determine if running in Docker
    in_docker = os.path.exists("/.dockerenv")
    
    # Set base directory for logs and data
    base_dir = "/app" if in_docker else os.getcwd()
    
    # Configure logging with environment variable or fallback
    log_file = os.environ.get("LOG_FILE")
    if not log_file:
        log_dir = os.environ.get("LOG_DIR", os.path.join(base_dir, "logs"))
        log_file = os.path.join(log_dir, "workday_scraper.log")
    elif not os.path.isabs(log_file):
        log_dir = os.environ.get("LOG_DIR", os.path.join(base_dir, "logs"))
        log_file = os.path.join(log_dir, log_file)
    
    configure_logger(log_file=log_file)
    
    # Ensure DB_FILE is absolute
    if "db_file" in args and args["db_file"]:
        if not os.path.isabs(args["db_file"]):
            data_dir = os.environ.get("DATA_DIR", os.path.join(base_dir, "data"))
            args["db_file"] = os.path.join(data_dir, args["db_file"])
    
    # Run the scraper
    await run_scraper(args)


def main():
    """Main entry point for the Workday Scraper."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

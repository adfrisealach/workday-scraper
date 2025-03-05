"""
Main entry point for the Workday Scraper.

This module provides the main entry point for the Workday Scraper, which
scrapes job postings from Workday sites and outputs them in various formats.
"""

import asyncio
from .parse_args import parse_args
from .scraper_controller import run_scraper
from .logging_utils import configure_logger


async def async_main():
    """Async main entry point for the Workday Scraper."""
    # Parse command-line arguments
    args = parse_args()
    
    # Configure logging
    configure_logger(log_file="workday_scraper.log")
    
    # Run the scraper
    await run_scraper(args)


def main():
    """Main entry point for the Workday Scraper."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

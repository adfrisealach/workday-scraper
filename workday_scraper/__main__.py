"""
Main entry point for the Workday Scraper.

This module provides the main entry point for the Workday Scraper, which
scrapes job postings from Workday sites and outputs them in various formats.
"""

from .parse_args import parse_args
from .scraper_controller import run_scraper
from .logging_utils import configure_logger


def main():
    """Main entry point for the Workday Scraper."""
    # Parse command-line arguments
    args = parse_args()
    
    # Configure logging
    configure_logger(log_file="workday_scraper.log")
    
    # Run the scraper
    run_scraper(args)


if __name__ == "__main__":
    main()

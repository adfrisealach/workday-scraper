"""
Workday Scraper - A robust web scraper for Workday job postings.

This package provides tools for scraping job postings from Workday sites
and outputting them in various formats using the JSON-LD extraction approach.
"""

__version__ = "1.0.0"

# Import key components for easier access
from .logging_utils import configure_logger, get_logger
from .error_handling import safe_operation
from .jsonld_extractor import scrape_workday_jobs
from .scraper_controller import WorkdayScraper, run_scraper
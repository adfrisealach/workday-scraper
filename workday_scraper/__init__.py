"""
Workday Scraper - A robust web scraper for Workday job postings.

This package provides tools for scraping job postings from Workday sites
and outputting them in various formats.
"""

__version__ = "1.0.0"

# Import key components for easier access
from .logging_utils import configure_logger, get_logger
from .error_handling import safe_operation
from .element_selection import ElementSelector
from .rate_limiter import domain_rate_limiter, get_domain_from_url
from .session_manager import session_manager, SessionContext
from .parallel_processor import process_in_parallel, scrape_with_controlled_parallelism
from .scraper_controller import WorkdayScraper, run_scraper
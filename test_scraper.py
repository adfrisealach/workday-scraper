#!/usr/bin/env python3
"""
Test script for the Workday Scraper.

This script tests the basic functionality of the Workday Scraper without
actually scraping any job postings. It verifies that the components are
working correctly and can be imported and used.
"""

import os
import sys
import time
import argparse
import logging

# Add the current directory to the path so we can import the workday_scraper package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workday_scraper.logging_utils import configure_logger, get_logger
from workday_scraper.session_manager import session_manager, SessionContext, WebdriverSessionManager
from workday_scraper.element_selection import ElementSelector
from workday_scraper.rate_limiter import domain_rate_limiter, get_domain_from_url


def parse_args():
    """Parse command-line arguments for the test script.
    
    Returns:
        dict: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Test script for the Workday Scraper")
    
    parser.add_argument("-u", "--url", dest="url", type=str,
                      default="https://autodesk.wd1.myworkdayjobs.com/Ext",
                      help="URL to test")
    
    parser.add_argument("-nh", "--no-headless", dest="no_headless", action="store_true",
                      help="Run Chrome in visible mode (not headless)")
    
    parser.add_argument("-l", "--log-level", dest="log_level", type=str,
                      default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level")
    
    # Parse arguments
    args = vars(parser.parse_args())
    return args


def test_session_manager(url, headless=True):
    """Test the session manager.
    
    Args:
        url (str): URL to test.
        headless (bool): Whether to run the browser in headless mode.
    
    Returns:
        bool: True if the test passed, False otherwise.
    """
    logger = get_logger()
    logger.info("Testing session manager...")
    
    # Initialize session manager
    global session_manager
    session_manager = session_manager or WebdriverSessionManager(
        max_sessions=2,
        headless=headless
    )
    
    try:
        # Get a session
        logger.info("Getting a session...")
        with SessionContext() as driver:
            logger.info("Got a session, navigating to URL...")
            driver.get(url)
            
            logger.info("Waiting for page to load...")
            time.sleep(5)
            
            logger.info(f"Page title: {driver.title}")
            logger.info(f"Current URL: {driver.current_url}")
            
            # Try to find some elements
            logger.info("Looking for job listings...")
            selector = ElementSelector(driver)
            
            try:
                job_elements = selector.find_job_listings(min_elements=1)
                logger.info(f"Found {len(job_elements)} job listings")
                
                if job_elements:
                    # Try to extract job information from the first element
                    job_info = selector.extract_job_info(job_elements[0])
                    if job_info:
                        logger.info(f"Successfully extracted job information: {job_info}")
                    else:
                        logger.warning("Failed to extract job information")
            except Exception as e:
                logger.error(f"Error finding job listings: {str(e)}")
        
        logger.info("Session released")
        return True
    except Exception as e:
        logger.error(f"Error testing session manager: {str(e)}")
        return False


def test_rate_limiter(url):
    """Test the rate limiter.
    
    Args:
        url (str): URL to test.
    
    Returns:
        bool: True if the test passed, False otherwise.
    """
    logger = get_logger()
    logger.info("Testing rate limiter...")
    
    try:
        # Get domain from URL
        domain = get_domain_from_url(url)
        logger.info(f"Domain: {domain}")
        
        # Test rate limiting
        logger.info("Testing rate limiting...")
        for i in range(5):
            wait_time = domain_rate_limiter.wait(domain)
            logger.info(f"Wait time for request {i+1}: {wait_time:.2f}s")
            domain_rate_limiter.success(domain)
        
        # Test failure handling
        logger.info("Testing failure handling...")
        domain_rate_limiter.failure(domain)
        wait_time = domain_rate_limiter.wait(domain)
        logger.info(f"Wait time after failure: {wait_time:.2f}s")
        
        # Get stats
        stats = domain_rate_limiter.get_stats()
        logger.info(f"Rate limiter stats: {stats}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing rate limiter: {str(e)}")
        return False


def main():
    """Main entry point for the test script."""
    # Parse command-line arguments
    args = parse_args()
    url = args["url"]
    headless = not args["no_headless"]
    log_level = args["log_level"]
    
    # Configure logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    configure_logger(log_file="test_scraper.log", log_level=numeric_level)
    logger = get_logger()
    
    # Log startup information
    logger.info("Starting test script", extra={
        "url": url,
        "headless": headless,
        "log_level": log_level
    })
    
    # Run tests
    tests_passed = 0
    tests_failed = 0
    
    # Test session manager
    if test_session_manager(url, headless):
        logger.info("Session manager test passed")
        tests_passed += 1
    else:
        logger.error("Session manager test failed")
        tests_failed += 1
    
    # Test rate limiter
    if test_rate_limiter(url):
        logger.info("Rate limiter test passed")
        tests_passed += 1
    else:
        logger.error("Rate limiter test failed")
        tests_failed += 1
    
    # Log results
    logger.info(f"Tests completed: {tests_passed} passed, {tests_failed} failed")
    
    # Clean up
    try:
        session_manager.close_all()
        logger.info("Closed all sessions")
    except Exception as e:
        logger.error(f"Error closing sessions: {str(e)}")


if __name__ == "__main__":
    main()
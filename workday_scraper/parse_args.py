"""
Command-line argument parsing for the Workday Scraper.

This module provides functions for parsing command-line arguments for the
Workday Scraper.
"""

import argparse
import sys


def parse_args():
    """Parse command-line arguments.
    
    Returns:
        dict: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Workday Scraper - Available Options")
    
    # Required arguments
    parser.add_argument("-f", "--file", dest="file", type=str, required=True,
                      help="Config file name in the configs/ directory")
    
    # Email notification arguments
    parser.add_argument("-e", "--email", dest="email", type=str,
                      required="-r" in sys.argv or "--recipients" in sys.argv or 
                              "-pw" in sys.argv or "--password" in sys.argv,
                      help="Email address to send notifications from")
    
    parser.add_argument("-pw", "--password", dest="password", type=str,
                      required="-e" in sys.argv or "--email" in sys.argv or 
                              "-r" in sys.argv or "--recipients" in sys.argv,
                      help="Password for the email account")
    
    parser.add_argument("-r", "--recipients", dest="recipients", type=str,
                      required="-e" in sys.argv or "--email" in sys.argv or 
                              "-pw" in sys.argv or "--password" in sys.argv,
                      help="Comma-separated list of email recipients")
    
    # Output options
    parser.add_argument("-i", "--initial", dest="initial", action="store_true",
                      help="Scrape all job listings, not just today's")
    
    parser.add_argument("-nj", "--no-json", dest="no-json", action="store_true",
                      help="Skip JSON output")
    
    parser.add_argument("-nr", "--no-rss", dest="no-rss", action="store_true",
                      help="Skip RSS output")
    
    # Browser options
    parser.add_argument("-nh", "--no-headless", dest="no-headless", action="store_true",
                      help="Run Chrome in visible mode (not headless)")
    
    # Performance options
    parser.add_argument("-ms", "--max-sessions", dest="max_sessions", type=int, default=3,
                      help="Maximum number of concurrent browser sessions")
    
    parser.add_argument("-mw", "--max-workers", dest="max_workers", type=int, default=5,
                      help="Maximum number of concurrent workers for parallel processing")
    
    parser.add_argument("-cs", "--chunk-size", dest="chunk_size", type=int, default=10,
                      help="Number of jobs to process in each chunk")
    
    # Logging options
    parser.add_argument("-l", "--log-file", dest="log_file", type=str,
                      default="workday_scraper.log",
                      help="Path to the log file")
    
    parser.add_argument("-ll", "--log-level", dest="log_level", type=str,
                      default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Logging level")
    
    # Parse arguments
    args = vars(parser.parse_args())
    return args

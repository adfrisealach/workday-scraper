#!/usr/bin/env python3
"""
Test script for the JSON-LD extractor.

This script tests the JSON-LD extractor on a single Workday job site.
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import the workday_scraper package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workday_scraper.jsonld_extractor import scrape_workday_jobs
from workday_scraper.logging_utils import setup_logging, get_logger

logger = get_logger()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test JSON-LD Extractor')
    parser.add_argument('--url', '-u', type=str, required=True,
                        help='URL of the Workday job site')
    parser.add_argument('--output', '-o', type=str, default='jsonld_jobs.json',
                        help='Output JSON file path')
    parser.add_argument('--log', '-l', type=str, default='jsonld_extractor.log',
                        help='Log file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_file=args.log, log_level=log_level)
    
    logger.info(f"Testing JSON-LD extractor on {args.url}")
    
    # Record start time
    start_time = datetime.now()
    
    # Scrape jobs
    jobs = await scrape_workday_jobs(args.url)
    
    # Record end time
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(jobs, f, indent=2)
    
    # Print summary
    logger.info(f"Scraped {len(jobs)} jobs in {elapsed_time:.2f} seconds")
    logger.info(f"Average time per job: {elapsed_time / len(jobs):.2f} seconds")
    logger.info(f"Results saved to {args.output}")
    
    print(f"\nSummary:")
    print(f"- Scraped {len(jobs)} jobs in {elapsed_time:.2f} seconds")
    print(f"- Average time per job: {elapsed_time / len(jobs):.2f} seconds")
    print(f"- Results saved to {args.output}")


if __name__ == '__main__':
    asyncio.run(main())
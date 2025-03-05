#!/usr/bin/env python3
"""
Enhanced Workday Scraper using JSON-LD extraction.

This script provides a faster and more complete way to scrape job listings from Workday sites
by using JSON-LD data extraction instead of full browser automation for job details.
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the parent directory to the path so we can import the workday_scraper package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workday_scraper.jsonld_extractor import scrape_workday_jobs
from workday_scraper.logging_utils import get_logger, setup_logging
# Create our own RSS function to handle the new job format

logger = get_logger()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Enhanced Workday Job Scraper')
    parser.add_argument('--config', '-c', type=str, help='Path to config file')
    parser.add_argument('--output', '-o', type=str, default='job_postings.json',
                        help='Output JSON file path')
    parser.add_argument('--rss', '-r', type=str, default='rss.xml',
                        help='Output RSS file path')
    parser.add_argument('--log', '-l', type=str, default='workday_scraper.log',
                        help='Log file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file."""
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            
        logger.debug(f"Config file content: {content}")
        
        lines = content.splitlines()
        logger.debug(f"Config lines: {lines}")
        
        config = {}
        
        # Always treat the first line as comma-separated for this format
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Split only on the first comma to handle URLs with commas
                parts = line.split(',', 1)
                logger.debug(f"Parsed parts: {parts}")
                if len(parts) >= 2:
                    config['company'] = parts[0].strip()
                    config['company_url'] = parts[1].strip()
                    # Default to initial=true for testing
                    config['initial'] = 'true'
                    break  # Only process the first non-comment line
        
        logger.debug(f"Final config: {config}")
        return config
    except Exception as e:
        logger.error(f"Error loading config file: {str(e)}")
        sys.exit(1)


def load_job_ids(filename: str = 'job_ids.json') -> Dict[str, List[str]]:
    """Load previously scraped job IDs."""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading job IDs: {str(e)}")
        return {}


def save_job_ids(job_ids: Dict[str, List[str]], filename: str = 'job_ids.json'):
    """Save scraped job IDs."""
    try:
        with open(filename, 'w') as f:
            json.dump(job_ids, f)
        logger.info(f"Saved job IDs dictionary with {len(job_ids)} companies")
    except Exception as e:
        logger.error(f"Error saving job IDs: {str(e)}")


def generate_rss(jobs: List[Dict[str, Any]], filename: str):
    """Generate RSS feed from job data and save to file."""
    try:
        rss = """\
<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">

<channel>
<title>Workday Scraper - RSS Feed</title>
<link>https://github.com/christopherlam888/workday-scraper</link>
<description>An RSS feed for new Workday postings.</description>
"""

        for job in jobs:
            # Use description field from JSON-LD data
            job_description = job.get("description", "").replace("\n", "<br>")
            
            rss += """\
<item>
    <title><![CDATA[{}]]></title>
    <link><![CDATA[{}]]></link>
    <description><![CDATA[{}]]></description>
</item>
""".format(
                f"{job.get('company', '')}: {job.get('title', '')}",
                f"{job.get('url', '')}",
                f"{job_description}",
            )

        rss += "\n</channel>\n</rss>"
        
        # Write to file
        with open(filename, 'w') as f:
            f.write(rss)
            
        logger.info(f"Saved RSS feed to {filename}")
    except Exception as e:
        logger.error(f"Error generating RSS: {str(e)}")


def save_jobs(jobs: List[Dict[str, Any]], filename: str):
    """Save scraped jobs to JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(jobs, f, indent=2)
        logger.info(f"Saved {len(jobs)} jobs to {filename}")
    except Exception as e:
        logger.error(f"Error saving jobs: {str(e)}")


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_file=args.log, log_level=log_level)
    
    # Load config
    if not args.config:
        logger.error("No config file specified")
        sys.exit(1)
    
    config = load_config(args.config)
    
    # Load previously scraped job IDs
    job_ids = load_job_ids()
    
    # Get company name from config
    company = config.get('company', 'unknown')
    
    # Initialize job IDs for this company if not exists
    if company not in job_ids:
        job_ids[company] = []
    
    # Scrape jobs
    logger.info(f"Starting enhanced scraper for {company}")
    
    company_url = config.get('company_url')
    if not company_url:
        logger.error("No company URL specified in config")
        sys.exit(1)
    
    # Try different URL formats if needed
    jobs = []
    urls_to_try = [company_url]
    
    # Add alternative URL formats
    if 'en-US' not in company_url and '/en-US/' not in company_url:
        # Try adding en-US to the URL
        parsed_url = company_url.split('/')
        if len(parsed_url) >= 3:
            domain = '/'.join(parsed_url[:3])  # Get the domain part
            path = '/'.join(parsed_url[3:])    # Get the path part
            alt_url = f"{domain}/en-US/{path}"
            urls_to_try.append(alt_url)
    
    # Try removing query parameters
    if '?' in company_url:
        base_url = company_url.split('?')[0]
        if base_url not in urls_to_try:
            urls_to_try.append(base_url)
    
    # Try each URL until we get a good result
    for i, url in enumerate(urls_to_try):
        logger.info(f"Trying URL format {i+1}/{len(urls_to_try)}: {url}")
        try:
            current_jobs = await scrape_workday_jobs(url)
            if current_jobs and len(current_jobs) > 0:
                logger.info(f"Successfully scraped {len(current_jobs)} jobs with URL: {url}")
                jobs = current_jobs
                if len(jobs) > 20:  # If we got more than the default page size, this is probably good
                    break
            else:
                logger.warning(f"No jobs found with URL: {url}")
        except Exception as e:
            logger.error(f"Error scraping with URL {url}: {str(e)}")
    
    if not jobs:
        logger.error("Failed to scrape jobs with any URL format")
        sys.exit(1)
    
    # Filter for new jobs if needed
    if not config.get('initial', 'false').lower() == 'true':
        new_jobs = []
        for job in jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in job_ids[company]:
                new_jobs.append(job)
                job_ids[company].append(job_id)
        
        logger.info(f"Found {len(new_jobs)} new jobs out of {len(jobs)} total jobs")
        jobs = new_jobs
    else:
        # In initial mode, save all job IDs
        for job in jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in job_ids[company]:
                job_ids[company].append(job_id)
        
        logger.info(f"Initial mode: Saving all {len(jobs)} jobs")
    
    # Add company and timestamp to each job
    for job in jobs:
        job['company'] = company
        job['timestamp'] = datetime.now().isoformat()
    
    # Save results
    save_jobs(jobs, args.output)
    save_job_ids(job_ids)
    
    # Generate RSS
    if args.rss:
        generate_rss(jobs, args.rss)
    
    logger.info("Enhanced scraper completed successfully")


if __name__ == '__main__':
    asyncio.run(main())
"""
Scraper controller for the Workday Scraper.

This module provides the main controller class for scraping Workday job postings
and coordinating the various components of the scraper.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .db_manager import DatabaseManager
from .jsonld_extractor import scrape_workday_jobs
from .rss_funcs import generate_rss
from .email_funcs import compose_email, send_email
from .logging_utils import get_logger
from .path_utils import get_base_dir, get_data_dir, get_configs_dir

logger = get_logger()


class WorkdayScraper:
    """Main scraper controller class."""
    
    def __init__(self, config_file: str = None, initial: bool = False, 
                 max_workers: int = 5, max_sessions: int = 3, chunk_size: int = 10,
                 db_file: str = None):
        """Initialize the WorkdayScraper.
        
        Args:
            config_file (str): Path to the configuration file.
            initial (bool): Whether to perform an initial scrape of all jobs.
            max_workers (int): Maximum number of worker threads for scraping.
            max_sessions (int): Maximum number of concurrent browser sessions.
            chunk_size (int): Number of jobs to process in each chunk.
            db_file (str): Path to the SQLite database file.
        """
        # Get base directory using reliable path resolution
        base_dir = get_base_dir()
        
        self.config_file = config_file
        self.initial = initial
        self.max_workers = max_workers
        self.max_sessions = max_sessions
        self.chunk_size = chunk_size
        self.companies = []
        
        # Load configuration
        if config_file:
            self.load_config(config_file)
        
        # Initialize database manager with explicit file path
        logger.info(f"Initializing scraper with base directory: {base_dir}")
        
        # Get base directory using reliable path resolution  
        base_dir = get_base_dir()
        
        # Use environment variable for DB file or fallback to default
        self.db_file = db_file or os.environ.get("DB_FILE", os.path.join(get_data_dir(), "workday_jobs.db"))
        # Initialize database manager
        self.db_manager = DatabaseManager(db_file=self.db_file)
        
        # Initialize job IDs dictionary
        self.job_ids_dict = {}
        self.load_job_ids()
        
        logger.info(f"Initialized WorkdayScraper with JSON-LD extraction", 
                   extra={
                       "initial": initial,
                       "concurrency": max_workers,
                       "config_file": config_file,
                       "db_file": self.db_file
                   })
    
    def load_config(self, config_file: str):
        """Load companies from configuration file.
        
        Args:
            config_file (str): Path to the configuration file.
        """
        try:
            # Use reliable path resolution for config files
            if not os.path.isabs(config_file):
                config_path = os.path.join(get_configs_dir(), config_file)
            else:
                config_path = config_file
                
            logger.info(f"Loading config from: {config_path}")
            
            with open(config_path, 'r') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            self.companies = []
            for line in lines:
                if ',' in line:
                    # Old format: company_name,url
                    name, url = line.split(',', 1)
                    self.companies.append(url.strip())
                else:
                    # New format: just url
                    self.companies.append(line)
            
            logger.info(f"Loaded {len(self.companies)} companies from config", 
                       extra={"config_file": os.path.basename(config_file)})
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise
    
    def load_job_ids(self):
        """Load job IDs from the database or JSON file."""
        try:
            # First try to load from database
            self.job_ids_dict = self.db_manager.get_job_ids_by_company()
            
            if not self.job_ids_dict:
                logger.info("No job IDs found in database")
                
                # Try to load from JSON file as fallback
                json_path = os.path.join(get_data_dir(), "job_ids.json")
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        self.job_ids_dict = json.load(f)
                    logger.info(f"Loaded job IDs from JSON file with {len(self.job_ids_dict)} companies")
                else:
                    logger.info("No existing job IDs file found, starting fresh")
            else:
                logger.info(f"Loaded job IDs from database with {len(self.job_ids_dict)} companies")
                
        except Exception as e:
            logger.error(f"Error loading job IDs: {str(e)}")
            self.job_ids_dict = {}
    
    def save_job_ids(self):
        """Save job IDs dictionary to JSON file."""
        try:
            json_path = os.path.join(get_data_dir(), "job_ids.json")
            
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            with open(json_path, 'w') as f:
                json.dump(self.job_ids_dict, f, indent=2)
            
            logger.info(f"Saved job IDs dictionary with {len(self.job_ids_dict)} companies to {json_path}")
        except Exception as e:
            logger.error(f"Error saving job IDs: {str(e)}")

    async def scrape_company(self, company_name: str) -> List[Dict[str, Any]]:
        """Scrape jobs for a single company.
        
        Args:
            company_name (str): Name of the company to scrape.
            
        Returns:
            List[Dict[str, Any]]: List of job dictionaries.
        """
        logger.info(f"Scraping {company_name} at {company_name}")
        
        # Get existing job IDs for this company
        existing_job_ids = set(self.job_ids_dict.get(company_name, []))
        
        # Try different URL formats
        url_formats = [
            f"{company_name}?timeType=6d5ece62cf5a4f9f9e349b55f045b5e2",
            f"{company_name}?timeType=6d5ece62cf5a4f9f9e349b55f045b5e2&Location_Country=bc33aa3152ec42d4995f4791a106ed09",
            f"{company_name}"
        ]
        
        all_jobs = []
        
        for i, url in enumerate(url_formats, 1):
            try:
                logger.info(f"Trying URL format {i}/{len(url_formats)}: {url}")
                
                # Use the JSON-LD extractor
                jobs = await scrape_workday_jobs(url)
                
                if jobs:
                    # Add company info to each job
                    for job in jobs:
                        # Extract company name from URL domain
                        import re
                        match = re.search(r'https?://([^.]+)\.', url)
                        company_name_extracted = match.group(1) if match else 'unknown'
                        job['company'] = company_name_extracted
                        job['company_url'] = url
                    
                    all_jobs.extend(jobs)
                    logger.info(f"Successfully scraped {len(jobs)} jobs from {company_name} using format {i}")
                    break  # Success, no need to try other formats
                else:
                    logger.warning(f"No jobs found for {company_name} using format {i}")
                    
            except Exception as e:
                logger.error(f"Error scraping {company_name} with format {i}: {str(e)}")
                continue
        
        if not all_jobs:
            logger.warning(f"No jobs found for {company_name} using any URL format")
        
        return all_jobs
    
    async def scrape_all_companies(self) -> List[Dict[str, Any]]:
        """Scrape jobs from all configured companies.
        
        Returns:
            List[Dict[str, Any]]: List of all job dictionaries.
        """
        if not self.companies:
            logger.warning("No companies configured")
            return []
        
        logger.info(f"Starting to scrape {len(self.companies)} companies")
        
        all_jobs = []
        
        # Process companies sequentially to avoid overwhelming servers
        for company in self.companies:
            try:
                company_jobs = await self.scrape_company(company)
                all_jobs.extend(company_jobs)
                
                # Update job IDs dictionary
                if company_jobs:
                    company_name = company.split('.')[0]  # Extract company name from URL
                    job_ids = [job['job_id'] for job in company_jobs if 'job_id' in job]
                    self.job_ids_dict[company_name] = job_ids
                    
            except Exception as e:
                logger.error(f"Error scraping company {company}: {str(e)}")
                continue
        
        logger.info(f"Completed scraping all companies. Total jobs found: {len(all_jobs)}")
        return all_jobs
    
    def save_results(self, jobs: List[Dict[str, Any]]) -> tuple:
        """Save jobs to database.
        
        Args:
            jobs (List[Dict[str, Any]]): List of job dictionaries to save.
            
        Returns:
            tuple: (saved_count, failed_count)
        """
        if not jobs:
            logger.info("No jobs to save")
            return 0, 0
        
        logger.info(f"Saving {len(jobs)} jobs to database")
        saved, failed = self.db_manager.save_jobs(jobs)
        logger.info(f"Saved {saved} jobs to database, {failed} failed")
        return saved, failed
    
    async def run(self) -> Dict[str, Any]:
        """Run the scraper.
        
        Returns:
            Dict[str, Any]: Results summary.
        """
        start_time = time.time()
        
        try:
            # Scrape all companies
            jobs = await self.scrape_all_companies()
            
            # Save results to database
            saved, failed = self.save_results(jobs)
            
            # Save job IDs
            self.save_job_ids()
            
            end_time = time.time()
            duration = end_time - start_time
            
            results = {
                "total_jobs": len(jobs),
                "saved_jobs": saved,
                "failed_jobs": failed,
                "companies_scraped": len(self.companies),
                "duration_seconds": duration,
                "success": True
            }
            
            logger.info(f"Scraping completed successfully", extra=results)
            return results
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": time.time() - start_time
            }
    
    def cleanup(self):
        """Clean up resources."""
        if self.db_manager:
            self.db_manager.close()
        logger.info("Cleanup completed")


async def run_scraper(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run the scraper with the given arguments.
    
    Args:
        args (Dict[str, Any]): Arguments dictionary containing scraper configuration.
        
    Returns:
        Dict[str, Any]: Results summary.
    """
    scraper = None
    try:
        # Get base directory using reliable path resolution
        base_dir = get_base_dir()
        
        # Get environment-specific paths
        db_file = args.get("db_file") or os.environ.get("DB_FILE", os.path.join(get_data_dir(), "workday_jobs.db"))
        
        # Create scraper instance
        scraper = WorkdayScraper(
            config_file=args.get("file"),
            initial=args.get("initial", False),
            max_workers=args.get("max_workers", 5),
            max_sessions=args.get("max_sessions", 3),
            chunk_size=args.get("chunk_size", 10),
            db_file=db_file
        )
        
        # Run the scraper
        results = await scraper.run()
        
        # Handle output formats
        if args.get("json"):
            output_file = args.get("output", "workday_jobs.json")
            if not os.path.isabs(output_file):
                output_file = os.path.join(get_data_dir(), output_file)
            
            jobs = scraper.db_manager.get_all_jobs()
            import json
            with open(output_file, 'w') as f:
                json.dump(jobs, f, indent=2)
            logger.info(f"Exported {len(jobs)} jobs to JSON: {output_file}")
        
        if args.get("rss"):
            output_file = args.get("output", "workday_jobs.xml")
            if not os.path.isabs(output_file):
                output_file = os.path.join(get_data_dir(), output_file)
            
            jobs = scraper.db_manager.get_all_jobs()
            rss_content = generate_rss(jobs)
            with open(output_file, 'w') as f:
                f.write(rss_content)
            logger.info(f"Generated RSS feed with {len(jobs)} jobs: {output_file}")
        
        # Send email if configured
        email_sender = args.get("email")
        email_password = args.get("password")
        email_recipients = args.get("recipients")
        
        if email_sender and email_password and email_recipients:
            try:
                jobs = scraper.db_manager.get_all_jobs()
                recipients_list = email_recipients.split(',')
                email_body = compose_email(jobs)
                send_email("Workday Scraper - Job Postings", email_body, email_sender, recipients_list, email_password)
                logger.info(f"Sent email with {len(jobs)} jobs to {len(recipients_list)} recipients")
            except Exception as e:
                logger.error(f"Error sending email: {str(e)}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in run_scraper: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if scraper:
            scraper.cleanup()


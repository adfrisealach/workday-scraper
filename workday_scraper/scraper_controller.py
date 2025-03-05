"""
Main controller for the Workday Scraper.

This module integrates all the components of the Workday Scraper and provides
a clean interface for scraping job postings from Workday sites.
"""

import os
import time
import json
import pickle
import logging
from urllib.parse import urlparse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .logging_utils import get_logger, configure_logger
from .error_handling import safe_operation, ElementNotFoundError, PageLoadError
from .element_selection import ElementSelector
from .rate_limiter import get_domain_from_url, domain_rate_limiter
from .session_manager import session_manager, SessionContext, WebdriverSessionManager
from .parallel_processor import scrape_with_controlled_parallelism

logger = get_logger()


class WorkdayScraper:
    """Main controller for the Workday Scraper."""
    
    def __init__(self, config_file=None, initial=False, headless=True,
                max_sessions=5, max_workers=5, chunk_size=10,
                log_file=None, log_level="INFO"):
        """Initialize the WorkdayScraper.
        
        Args:
            config_file (str, optional): Path to the config file.
            initial (bool): Whether to scrape all listings or only today's.
            headless (bool): Whether to run browsers in headless mode.
            max_sessions (int): Maximum number of concurrent browser sessions.
            max_workers (int): Maximum number of concurrent workers for parallel processing.
            chunk_size (int): Number of jobs to process in each chunk.
            log_file (str, optional): Path to the log file.
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        # Configure logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
        
        configure_logger(log_file=log_file, log_level=numeric_level)
        
        # Initialize settings
        self.config_file = config_file
        self.initial = initial
        self.headless = headless
        self.max_sessions = max_sessions
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        
        # Initialize session manager
        global session_manager
        session_manager = session_manager or WebdriverSessionManager(
            max_sessions=max_sessions,
            headless=headless
        )
        
        # Initialize job IDs dictionary
        self.job_ids_dict = {}
        self.load_job_ids()
        
        # Initialize company URLs
        self.company_urls = {}
        if config_file:
            self.load_config(config_file)
        
        logger.info("Initialized WorkdayScraper", extra={
            "initial": initial,
            "headless": headless,
            "max_sessions": max_sessions,
            "max_workers": max_workers,
            "chunk_size": chunk_size,
            "config_file": config_file
        })
    
    def load_config(self, config_file):
        """Load company URLs from a config file.
        
        Args:
            config_file (str): Path to the config file.
        
        Returns:
            dict: Company URLs.
        """
        self.company_urls = {}
        
        try:
            config_path = os.path.join("configs", config_file)
            with open(config_path, "r") as inputfile:
                for line in inputfile:
                    if line.strip() and "," in line:
                        name, url = line.strip().split(",", 1)
                        self.company_urls[name] = url.strip()
            
            logger.info(f"Loaded {len(self.company_urls)} companies from config", 
                       extra={"config_file": config_file})
            
            # Initialize job IDs for new companies
            for company in self.company_urls:
                if self.company_urls[company] not in self.job_ids_dict:
                    self.job_ids_dict[self.company_urls[company]] = []
            
            return self.company_urls
        except Exception as e:
            logger.error(f"Error loading config file: {str(e)}", 
                        extra={"config_file": config_file})
            raise
    
    def load_job_ids(self):
        """Load job IDs from the pickle file."""
        try:
            with open("job_ids_dict.pkl", "rb") as f:
                self.job_ids_dict = pickle.load(f)
            
            logger.info(f"Loaded job IDs dictionary with {len(self.job_ids_dict)} companies")
        except FileNotFoundError:
            logger.info("No existing job IDs dictionary found, creating a new one")
            self.job_ids_dict = {}
    
    def save_job_ids(self):
        """Save job IDs to the pickle file."""
        try:
            with open("job_ids_dict.pkl", "wb") as f:
                pickle.dump(self.job_ids_dict, f)
            
            logger.info(f"Saved job IDs dictionary with {len(self.job_ids_dict)} companies")
        except Exception as e:
            logger.error(f"Error saving job IDs dictionary: {str(e)}")
    
    def scrape_company(self, company_name, company_url):
        """Scrape job listings for a company.
        
        Args:
            company_name (str): Name of the company.
            company_url (str): URL of the company's job listings.
        
        Returns:
            list: Job listings to scrape.
        """
        logger.info(f"Scraping {company_name} at {company_url}")
        
        jobs_to_scrape = []
        domain = get_domain_from_url(company_url)
        
        # Use a session context to automatically release the session
        with SessionContext() as driver:
            # Wait for rate limiting
            domain_rate_limiter.wait(domain)
            
            try:
                # Navigate to the company URL
                logger.info(f"Opening URL: {company_url}")
                driver.get(company_url)
                
                # Wait for page to load with dynamic waiting
                self.wait_for_page_load(max_wait_time=15)
                
                # Create element selector
                wait = WebDriverWait(driver, 20)
                selector = ElementSelector(driver, wait)
                
                # Process job listings
                today = True
                page_num = 1
                
                while today or self.initial:
                    logger.info(f"Processing page {page_num}")
                    
                    # Find job listings
                    try:
                        job_elements = selector.find_job_listings()
                        logger.info(f"Found {len(job_elements)} job listings on page {page_num}")
                        
                        # Process each job listing
                        for job_element in job_elements:
                            try:
                                # Extract job information
                                job_info = selector.extract_job_info(job_element)
                                
                                if not job_info:
                                    logger.warning("Failed to extract job information, skipping")
                                    continue
                                
                                # Get posted date
                                posted_date_element = selector.find_posted_date(job_element)
                                posted_date = posted_date_element.text
                                
                                logger.info(f"Found job: {job_info['job_title']}, ID: {job_info['job_id']}, Posted: {posted_date}")
                                
                                # Check if job is from today or we're in initial mode
                                if "posted today" in posted_date.lower() or self.initial:
                                    # Check if job is already in the dictionary
                                    if job_info['job_id'] not in self.job_ids_dict[company_url]:
                                        self.job_ids_dict[company_url].append(job_info['job_id'])
                                        jobs_to_scrape.append({
                                            'company': company_name,
                                            'company_url': company_url,
                                            'job_title': job_info['job_title'],
                                            'job_href': job_info['job_href'],
                                            'job_id': job_info['job_id']
                                        })
                                        logger.info(f"Added job to scrape list: {job_info['job_title']}")
                                    else:
                                        logger.info(f"Job ID {job_info['job_id']} already in job_ids_dict")
                                else:
                                    today = False
                                    if not self.initial:
                                        logger.info("Found job not posted today, skipping remaining jobs")
                                        break
                            except Exception as e:
                                logger.error(f"Error processing job element: {str(e)}")
                                continue
                        
                        # Try to go to next page if needed
                        if today or self.initial:
                            next_button = selector.find_next_page_button()
                            
                            if next_button:
                                logger.info("Clicking next page button")
                                next_button.click()
                                self.wait_for_page_load(max_wait_time=12)  # Dynamic waiting for next page
                                page_num += 1
                                
                                # Record successful navigation
                                domain_rate_limiter.success(domain)
                            else:
                                logger.info("No next page button found or it's disabled")
                                break
                        else:
                            break
                    
                    except ElementNotFoundError as e:
                        logger.error(f"Error finding job listings: {str(e)}")
                        
                        # Save page source for debugging
                        debug_file = f"{company_name}_error_page.html"
                        with open(debug_file, "w") as f:
                            f.write(driver.page_source)
                        logger.info(f"Page source saved to {debug_file}")
                        
                        # Record failure
                        domain_rate_limiter.failure(domain)
                        break
            
            except Exception as e:
                logger.error(f"Error scraping {company_name}: {str(e)}")
                domain_rate_limiter.failure(domain)
        
        logger.info(f"Found {len(jobs_to_scrape)} jobs to scrape for {company_name}")
        return jobs_to_scrape
    
    def scrape_job_details(self, job_info, max_retries=5):
        """Scrape details for a job posting.
        
        Args:
            job_info (dict): Information about the job posting.
            max_retries (int): Maximum number of retry attempts.
        
        Returns:
            dict: Complete job information including the job posting text.
        """
        company = job_info['company']
        company_url = job_info['company_url']
        job_title = job_info['job_title']
        job_href = job_info['job_href']
        job_id = job_info.get('job_id', 'unknown')
        
        logger.info(f"Scraping job details: {job_title} (ID: {job_id})")
        domain = get_domain_from_url(job_href)
        
        for attempt in range(max_retries + 1):
            # Use a session context to automatically release the session
            with SessionContext() as driver:
                # Wait for rate limiting
                domain_rate_limiter.wait(domain)
                
                try:
                    # Navigate to the job posting
                    logger.info(f"Opening job URL: {job_href}")
                    driver.get(job_href)
                    
                    # Use dynamic waiting with increasing max time for retries
                    max_wait = 8 + (attempt * 2)  # Start with 8s, add 2s per retry
                    self.wait_for_page_load(max_wait_time=max_wait)
                    
                    # Create element selector with longer wait time for retries
                    wait_time = 15 + (attempt * 5)
                    wait = WebDriverWait(driver, wait_time)
                    selector = ElementSelector(driver, wait)
                    
                    # Find job details
                    job_details_element = selector.find_job_details()
                    job_posting_text = job_details_element.text
                    
                    # Record successful scraping
                    domain_rate_limiter.success(domain)
                    
                    # Return complete job information
                    return {
                        "company": company,
                        "company_url": company_url,
                        "job_title": job_title,
                        "job_href": job_href,
                        "job_id": job_id,
                        "job_posting_text": job_posting_text
                    }
                
                except ElementNotFoundError as e:
                    logger.warning(f"Element not found when scraping job details (attempt {attempt+1}/{max_retries+1}): {str(e)}")
                    domain_rate_limiter.failure(domain)
                    
                    if attempt < max_retries:
                        # Wait before retrying with exponential backoff
                        backoff_time = 5 * (2 ** attempt)
                        logger.info(f"Retrying in {backoff_time} seconds...")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"Failed to scrape job details after {max_retries+1} attempts")
                        return None
                
                except Exception as e:
                    logger.error(f"Error scraping job details: {str(e)}")
                    domain_rate_limiter.failure(domain)
                    
                    if attempt < max_retries:
                        # Wait before retrying with exponential backoff
                        backoff_time = 5 * (2 ** attempt)
                        logger.info(f"Retrying in {backoff_time} seconds...")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"Failed to scrape job details after {max_retries+1} attempts")
                        return None
    
    def scrape_all_companies(self):
        """Scrape job listings for all companies in the config.
        
        Returns:
            list: Complete job information for all scraped jobs.
        """
        all_jobs_to_scrape = []
        
        # Scrape job listings for each company
        for company_name, company_url in self.company_urls.items():
            jobs_to_scrape = self.scrape_company(company_name, company_url)
            all_jobs_to_scrape.extend(jobs_to_scrape)
        
        logger.info(f"Found {len(all_jobs_to_scrape)} total jobs to scrape")
        
        # Scrape job details in parallel
        if all_jobs_to_scrape:
            jobs = scrape_with_controlled_parallelism(
                all_jobs_to_scrape,
                self.scrape_job_details,
                max_workers=self.max_workers,
                chunk_size=self.chunk_size
            )
            
            # Filter out None results
            jobs = [job for job in jobs if job is not None]
            
            logger.info(f"Successfully scraped {len(jobs)} jobs")
            return jobs
        else:
            logger.info("No jobs to scrape")
            return []
    
    def save_results(self, jobs, output_json=True, output_rss=True):
        """Save the scraped jobs to output files.
        
        Args:
            jobs (list): Scraped job information.
            output_json (bool): Whether to output JSON.
            output_rss (bool): Whether to output RSS.
        """
        if not jobs:
            logger.warning("No jobs to save")
            return
        
        # Save to JSON
        if output_json:
            try:
                jsondata = json.dumps(jobs, indent=4)
                with open("job_postings.json", "w") as jsonfile:
                    jsonfile.write(jsondata)
                logger.info(f"Saved {len(jobs)} jobs to job_postings.json")
            except Exception as e:
                logger.error(f"Error saving JSON: {str(e)}")
        
        # Save to RSS
        if output_rss:
            try:
                from .rss_funcs import generate_rss
                with open("rss.xml", "w") as rssfile:
                    rssfile.write(generate_rss(jobs))
                logger.info(f"Saved {len(jobs)} jobs to rss.xml")
            except Exception as e:
                logger.error(f"Error saving RSS: {str(e)}")
        
        # Save job IDs
        self.save_job_ids()
    
    def send_email_notification(self, jobs, sender, recipients, password):
        """Send an email notification with the scraped jobs.
        
        Args:
            jobs (list): Scraped job information.
            sender (str): Sender email address.
            recipients (list): Recipient email addresses.
            password (str): Sender email password.
        
        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        if not jobs:
            logger.warning("No jobs to send email for")
            return False
        
        try:
            from .email_funcs import compose_email, send_email
            
            subject = "Workday Scraper: Today's Jobs"
            body = compose_email(jobs)
            
            send_email(subject, body, sender, recipients, password)
            logger.info(f"Sent email notification to {len(recipients)} recipients")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def wait_for_page_load(self, max_wait_time=10, poll_interval=0.5):
        """Wait for the page to load using dynamic waiting instead of fixed sleeps.
        
        Args:
            max_wait_time: Maximum time to wait in seconds.
            poll_interval: How often to check for page load completion in seconds.
        """
        logger.info(f"Waiting up to {max_wait_time} seconds for page to load")
        
        # This method is called within a context where driver is already available
        # Get the driver from the current context
        driver = None
        
        # Find the driver in the current stack frame
        import inspect
        frame = inspect.currentframe()
        try:
            # Look for 'driver' in the local variables of the calling function
            if frame.f_back and 'driver' in frame.f_back.f_locals:
                driver = frame.f_back.f_locals['driver']
        finally:
            del frame  # Avoid reference cycles
        
        if not driver:
            logger.warning("Could not find driver in current context, skipping dynamic wait")
            return
        
        start_time = time.time()
        page_ready = False
        
        while time.time() - start_time < max_wait_time and not page_ready:
            try:
                # Check if document is ready
                ready_state = driver.execute_script("return document.readyState")
                
                # Check if we can find any job elements
                try:
                    elements = driver.find_elements_by_xpath(
                        "//div[contains(@class, 'job')] | //li[contains(@class, 'css-')] | //h2 | //h3"
                    )
                    elements_found = len(elements) > 0
                except Exception:
                    elements_found = False
                
                # Consider the page ready if document is complete and we found elements
                # or if we've been waiting for at least 5 seconds
                min_wait_satisfied = (time.time() - start_time) >= min(5, max_wait_time/2)
                page_ready = (ready_state == "complete" and elements_found) or (ready_state == "complete" and min_wait_satisfied)
                
                if page_ready:
                    elapsed = time.time() - start_time
                    logger.info(f"Page load complete after {elapsed:.2f} seconds")
                    if elements_found:
                        logger.info(f"Found {len(elements)} potential job elements")
                    break
                
                time.sleep(poll_interval)
            except Exception as e:
                logger.warning(f"Error checking page load status: {str(e)}")
                # Wait a bit before retrying
                time.sleep(poll_interval)
        
        # If we timed out, log a warning but continue
        if not page_ready:
            logger.warning(f"Page load timed out after {max_wait_time} seconds")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            # Close all browser sessions
            session_manager.close_all()
            logger.info("Closed all browser sessions")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


def run_scraper(args):
    """Run the scraper with the given arguments.
    
    Args:
        args (dict): Command-line arguments.
    
    Returns:
        list: Scraped job information.
    """
    # Extract arguments
    config_file = args["file"]
    initial = args["initial"]
    no_json = args.get("no-json", False)
    no_rss = args.get("no-rss", False)
    headless = not args.get("no-headless", False)
    
    # Email arguments
    sender = args.get("email")
    password = args.get("password")
    recipients_str = args.get("recipients")
    recipients = recipients_str.split(",") if recipients_str else []
    
    # Create and run the scraper
    scraper = WorkdayScraper(
        config_file=config_file,
        initial=initial,
        headless=headless
    )
    
    try:
        # Scrape all companies
        jobs = scraper.scrape_all_companies()
        
        # Save results
        scraper.save_results(jobs, output_json=not no_json, output_rss=not no_rss)
        
        # Send email notification if requested
        if sender and recipients and password and jobs:
            scraper.send_email_notification(jobs, sender, recipients, password)
        
        return jobs
    finally:
        # Clean up resources
        scraper.cleanup()


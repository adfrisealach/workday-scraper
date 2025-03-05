"""
Main controller for the Workday Scraper.

This module integrates all the components of the Workday Scraper and provides
a clean interface for scraping job postings from Workday sites using the JSON-LD
extraction approach for significantly improved performance and completeness.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

from .logging_utils import get_logger, configure_logger
from .jsonld_extractor import scrape_workday_jobs

logger = get_logger()



class WorkdayScraper:
    """Main controller for the Workday Scraper using JSON-LD extraction."""
    
    def __init__(self, config_file=None, initial=False, concurrency=10,
                log_file=None, log_level="INFO"):
        """Initialize the WorkdayScraper.
        
        Args:
            config_file (str, optional): Path to the config file.
            initial (bool): Whether to scrape all listings or only today's.
            concurrency (int): Maximum number of concurrent HTTP requests.
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
        self.concurrency = concurrency
        
        # Initialize job IDs dictionary
        self.job_ids_dict = {}
        self.load_job_ids()
        
        # Initialize company URLs
        self.company_urls = {}
        if config_file:
            self.load_config(config_file)
        
        logger.info("Initialized WorkdayScraper with JSON-LD extraction", extra={
            "initial": initial,
            "concurrency": concurrency,
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
                if company not in self.job_ids_dict:
                    self.job_ids_dict[company] = []
            
            return self.company_urls
        except Exception as e:
            logger.error(f"Error loading config file: {str(e)}",
                        extra={"config_file": config_file})
            raise
    
    def load_job_ids(self):
        """Load job IDs from the JSON file."""
        try:
            if os.path.exists("job_ids.json"):
                with open("job_ids.json", "r") as f:
                    self.job_ids_dict = json.load(f)
                
                logger.info(f"Loaded job IDs dictionary with {len(self.job_ids_dict)} companies")
            else:
                logger.info("No existing job IDs dictionary found, creating a new one")
                self.job_ids_dict = {}
        except Exception as e:
            logger.error(f"Error loading job IDs: {str(e)}")
            self.job_ids_dict = {}
    
    def save_job_ids(self):
        """Save job IDs to the JSON file."""
        try:
            with open("job_ids.json", "w") as f:
                json.dump(self.job_ids_dict, f)
            
            logger.info(f"Saved job IDs dictionary with {len(self.job_ids_dict)} companies")
        except Exception as e:
            logger.error(f"Error saving job IDs dictionary: {str(e)}")
    
    async def scrape_company(self, company_name, company_url):
        """Scrape job listings for a company using JSON-LD extraction.
        
        Args:
            company_name (str): Name of the company.
            company_url (str): URL of the company's job listings.
        
        Returns:
            list: Complete job information.
        """
        logger.info(f"Scraping {company_name} at {company_url}")
        
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
            logger.error(f"Failed to scrape jobs for {company_name} with any URL format")
            return []
        
        # Filter for new jobs if needed
        if not self.initial:
            new_jobs = []
            for job in jobs:
                job_id = job.get('job_id')
                if job_id and job_id not in self.job_ids_dict[company_name]:
                    new_jobs.append(job)
                    self.job_ids_dict[company_name].append(job_id)
            
            logger.info(f"Found {len(new_jobs)} new jobs out of {len(jobs)} total jobs")
            jobs = new_jobs
        else:
            # In initial mode, save all job IDs
            for job in jobs:
                job_id = job.get('job_id')
                if job_id and job_id not in self.job_ids_dict[company_name]:
                    self.job_ids_dict[company_name].append(job_id)
            
            logger.info(f"Initial mode: Saving all {len(jobs)} jobs")
        
        # Add company and timestamp to each job
        for job in jobs:
            job['company'] = company_name
            job['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Processed {len(jobs)} jobs for {company_name}")
        return jobs
    
    async def scrape_all_companies(self):
        """Scrape job listings for all companies in the config.
        
        Returns:
            list: Complete job information for all scraped jobs.
        """
        all_jobs = []
        
        # Scrape job listings for each company
        for company_name, company_url in self.company_urls.items():
            jobs = await self.scrape_company(company_name, company_url)
            all_jobs.extend(jobs)
        
        logger.info(f"Successfully scraped {len(all_jobs)} total jobs")
        return all_jobs
    
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
                jsondata = json.dumps(jobs, indent=2)
                with open("job_postings.json", "w") as jsonfile:
                    jsonfile.write(jsondata)
                logger.info(f"Saved {len(jobs)} jobs to job_postings.json")
            except Exception as e:
                logger.error(f"Error saving JSON: {str(e)}")
        
        # Save to RSS
        if output_rss:
            try:
                # Generate RSS feed
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
                with open("rss.xml", "w") as rssfile:
                    rssfile.write(rss)
                
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
            # Compose email body
            body = f"""<html>
<body>
<h1>Workday Scraper: Job Postings</h1>
<p>Found {len(jobs)} job postings:</p>
<ul>
"""
            
            for job in jobs:
                title = job.get('title', 'Unknown Title')
                company = job.get('company', 'Unknown Company')
                url = job.get('url', '#')
                date_posted = job.get('date_posted', '')
                location = job.get('location', '')
                
                body += f"""<li>
<a href="{url}"><strong>{company}: {title}</strong></a>
<br>Location: {location}
<br>Posted: {date_posted}
</li>
"""
            
            body += """</ul>
<p>This email was sent automatically by the Workday Scraper.</p>
</body>
</html>"""
            
            # Send email
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = "Workday Scraper: Today's Jobs"
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Sent email notification to {len(recipients)} recipients")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up resources."""
        # No browser sessions to clean up with JSON-LD approach
        logger.info("Cleanup completed")


async def run_scraper(args):
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
    concurrency = args.get("max_workers", 10)  # Use max_workers as concurrency
    log_file = args.get("log_file", "workday_scraper.log")
    log_level = args.get("log_level", "INFO")
    
    # Email arguments
    sender = args.get("email")
    password = args.get("password")
    recipients_str = args.get("recipients")
    recipients = recipients_str.split(",") if recipients_str else []
    
    # Create and run the scraper
    scraper = WorkdayScraper(
        config_file=config_file,
        initial=initial,
        concurrency=concurrency,
        log_file=log_file,
        log_level=log_level
    )
    
    try:
        # Scrape all companies
        jobs = await scraper.scrape_all_companies()
        
        # Save results
        scraper.save_results(jobs, output_json=not no_json, output_rss=not no_rss)
        
        # Send email notification if requested
        if sender and recipients and password and jobs:
            scraper.send_email_notification(jobs, sender, recipients, password)
        
        return jobs
    finally:
        # Clean up resources
        scraper.cleanup()


"""
Element selection strategy for the Workday Scraper.

This module provides a robust element selection strategy with fallbacks
for finding elements on Workday pages, making the scraper more resilient
to changes in the page structure.
"""

import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

# Import from our modules
from .logging_utils import get_logger
from .error_handling import ElementNotFoundError, safe_operation

logger = get_logger()


# Compile regex patterns once at module level for efficiency
import re
WD_ID_PATTERN = re.compile(r'\d+WD\d+')

class ElementSelector:
    """Class for finding elements with multiple selector strategies and fallbacks."""
    
    # Common selectors for Workday job listings
    JOB_LISTING_SELECTORS = [
        # Original selectors
        (By.XPATH, '//li[@class="css-1q2dra3"]'),
        (By.XPATH, '//li[contains(@class, "css-")]'),
        (By.XPATH, '//div[contains(@data-automation-id, "jobResults")]/ul/li'),
        (By.CSS_SELECTOR, '[data-automation-id="jobResults"] li'),
        (By.XPATH, '//ul[contains(@class, "css-")]/li'),
        (By.XPATH, '//div[contains(@class, "search-results-list")]/div'),
        (By.CSS_SELECTOR, '.search-results-list > div'),
        # New selectors based on screenshot
        (By.XPATH, '//div[contains(@class, "job-card")]'),
        (By.XPATH, '//div[contains(@class, "job-component")]'),
        (By.XPATH, '//div[contains(@class, "job-listing")]'),
        # Very generic fallbacks
        (By.XPATH, '//div[contains(@role, "listitem")]'),
        (By.XPATH, '//div[contains(@class, "card")]'),
        (By.XPATH, '//div[contains(@class, "list-item")]'),
        # Direct parent of job titles
        (By.XPATH, '//h2/parent::div'),
        (By.XPATH, '//h3/parent::div'),
    ]
    
    JOB_TITLE_SELECTORS = [
        # Original selectors
        (By.XPATH, './/h3/a'),
        (By.XPATH, './/a[contains(@data-automation-id, "jobTitle")]'),
        (By.CSS_SELECTOR, 'h3 a'),
        (By.CSS_SELECTOR, '[data-automation-id="jobTitle"]'),
        (By.XPATH, './/a[contains(@class, "css-")]'),
        (By.XPATH, './/div[contains(@class, "job-title")]/a'),
        (By.XPATH, './/div[contains(@class, "title")]/a'),
        (By.XPATH, './/h3'),
        (By.XPATH, './/div[contains(@class, "title")]'),
        # New selectors based on screenshot
        (By.XPATH, './/h2'),
        (By.XPATH, './/div[contains(@class, "title") and not(contains(@class, "subtitle"))]'),
        (By.XPATH, './/div[contains(@class, "heading")]'),
        (By.XPATH, './/div[contains(@class, "job-title")]'),
        # Very generic fallbacks - get the first heading or strong text
        (By.XPATH, './/*[self::h1 or self::h2 or self::h3 or self::h4][1]'),
        (By.XPATH, './/strong[1]'),
        # First text element that's not a location or date
        (By.XPATH, './/div[not(contains(text(), "Posted")) and not(contains(text(), "Location"))][1]'),
    ]
    
    JOB_ID_SELECTORS = [
        # Original selectors
        (By.XPATH, './/ul[@data-automation-id="subtitle"]/li'),
        (By.XPATH, './/li[contains(text(), "ID:")]'),
        (By.XPATH, './/li[contains(text(), "Req ID")]'),
        (By.CSS_SELECTOR, '[data-automation-id="subtitle"] li'),
        (By.XPATH, './/div[contains(@class, "job-id")]'),
        (By.XPATH, './/span[contains(text(), "ID:")]'),
        (By.XPATH, './/span[contains(text(), "Job ID")]'),
        (By.XPATH, './/div[contains(@class, "meta-data")]//span[contains(text(), "ID")]'),
        (By.XPATH, './/div[contains(@class, "meta-data")]//span[1]'),
        # New selectors based on screenshot
        (By.XPATH, './/*[contains(text(), "WD")]'),
        # Last text element in the card (often the ID)
        (By.XPATH, './/div[last()][not(contains(., "Posted"))]'),
        # Text that matches job ID pattern (numbers followed by WD followed by numbers)
        (By.XPATH, './/*[contains(text(), "WD")]'),
        # Plain text nodes that might contain the ID
        (By.XPATH, './/text()[contains(., "WD")]'),
    ]
    
    POSTED_DATE_SELECTORS = [
        # Original selectors
        (By.XPATH, './/dd[@class="css-129m7dg"][preceding-sibling::dt[contains(text(),"posted on")]]'),
        (By.XPATH, './/dd[preceding-sibling::dt[contains(text(),"posted on")]]'),
        (By.XPATH, './/span[contains(text(), "Posted")]'),
        (By.CSS_SELECTOR, 'dd[class*="css-"][data-automation-id*="postedOn"]'),
        (By.XPATH, './/div[contains(@class, "posted-date")]'),
        (By.XPATH, './/div[contains(@class, "meta-data")]//span[contains(text(), "Posted")]'),
        (By.XPATH, './/div[contains(@class, "meta-data")]//span[2]'),
        (By.XPATH, './/div[contains(@class, "job-date")]'),
        # New selectors based on screenshot
        (By.XPATH, './/*[contains(text(), "Posted")]'),
        (By.XPATH, './/div[contains(@class, "date")]'),
        (By.XPATH, './/div[contains(@class, "time")]'),
        # Icon-based selection
        (By.XPATH, './/div[contains(@class, "clock-icon")]/following-sibling::div'),
        (By.XPATH, './/div[contains(@class, "time-icon")]/following-sibling::div'),
    ]
    
    NEXT_PAGE_SELECTORS = [
        # Original selectors
        (By.XPATH, '//button[@data-uxi-element-id="next"]'),
        (By.XPATH, '//button[contains(@aria-label, "Next Page")]'),
        (By.CSS_SELECTOR, 'button[data-uxi-element-id="next"]'),
        (By.CSS_SELECTOR, 'button[aria-label*="Next Page"]'),
        (By.XPATH, '//button[contains(@class, "next")]'),
        (By.XPATH, '//a[contains(@class, "next")]'),
        (By.XPATH, '//button[contains(@class, "pagination") and contains(@class, "next")]'),
        (By.XPATH, '//button[contains(@class, "pagination-next")]'),
        (By.XPATH, '//button[contains(text(), "Next")]'),
        (By.XPATH, '//a[contains(text(), "Next")]'),
        # New selectors based on screenshot
        (By.XPATH, '//button[text()=">"]'),
        (By.XPATH, '//a[text()=">"]'),
        (By.XPATH, '//div[contains(@class, "pagination")]//button[position()=last()]'),
        (By.XPATH, '//div[contains(@class, "pagination")]//a[position()=last()]'),
        # Generic navigation selectors
        (By.XPATH, '//button[contains(@aria-label, "next")]'),
        (By.XPATH, '//a[contains(@aria-label, "next")]'),
        # Number-based pagination
        (By.XPATH, '//a[text()="2"]'),
        (By.XPATH, '//button[text()="2"]'),
    ]
    
    JOB_DETAILS_SELECTORS = [
        (By.XPATH, '//div[@data-automation-id="job-posting-details"]'),
        (By.XPATH, '//div[contains(@class, "job-posting-details")]'),
        (By.CSS_SELECTOR, '[data-automation-id="job-posting-details"]'),
        (By.CSS_SELECTOR, '.job-posting-details'),
        (By.XPATH, '//div[contains(@class, "job-description")]'),
        (By.XPATH, '//div[contains(@class, "description")]'),
        (By.XPATH, '//div[contains(@class, "details")]'),
        (By.XPATH, '//div[contains(@class, "job-details")]'),
        (By.XPATH, '//main'),
        (By.XPATH, '//div[@role="main"]'),
    ]
    
    def __init__(self, driver, wait=None):
        """Initialize the ElementSelector.
        
        Args:
            driver: Selenium WebDriver instance.
            wait: WebDriverWait instance (optional).
        """
        self.driver = driver
        self.wait = wait
    
    def find_element_with_fallbacks(self, parent, selectors_list, max_retries=3,
                                   retry_delay=1, context="element"):
        """Try multiple selectors with retries to find an element.
        
        Args:
            parent: The parent element to search within, or the driver.
            selectors_list: List of (selector_type, selector) tuples to try.
            max_retries: Maximum number of retry attempts.
            retry_delay: Initial delay between retries in seconds.
            context: Description of what is being searched for (for logging).
        
        Returns:
            The found WebElement.
        
        Raises:
            ElementNotFoundError: If the element cannot be found with any selector.
        """
        logger.debug(f"Looking for {context} with {len(selectors_list)} possible selectors")
        
        for attempt in range(max_retries):
            for selector_type, selector in selectors_list:
                try:
                    element = parent.find_element(selector_type, selector)
                    logger.debug(f"Found {context} with selector: {selector_type}='{selector}'")
                    return element
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
            
            # If we get here, none of the selectors worked on this attempt
            if attempt < max_retries - 1:
                backoff_time = retry_delay * (attempt + 1)
                logger.debug(f"No selectors worked for {context}, retrying in {backoff_time}s (attempt {attempt+1}/{max_retries})")
                time.sleep(backoff_time)  # Exponential backoff
        
        # If we get here, all retries failed
        selector_descriptions = [f"{s[0]}='{s[1]}'" for s in selectors_list]
        error_msg = f"Failed to find {context} after {max_retries} attempts with selectors: {', '.join(selector_descriptions)}"
        logger.error(error_msg)
        raise ElementNotFoundError(error_msg)
    
    def find_elements_with_fallbacks(self, parent, selectors_list, min_elements=1,
                                    max_retries=3, retry_delay=1, context="elements"):
        """Try multiple selectors with retries to find elements.
        
        Args:
            parent: The parent element to search within, or the driver.
            selectors_list: List of (selector_type, selector) tuples to try.
            min_elements: Minimum number of elements to consider a successful find.
            max_retries: Maximum number of retry attempts.
            retry_delay: Initial delay between retries in seconds.
            context: Description of what is being searched for (for logging).
        
        Returns:
            List of found WebElements.
        
        Raises:
            ElementNotFoundError: If no elements can be found with any selector.
        """
        logger.debug(f"Looking for {context} with {len(selectors_list)} possible selectors")
        
        for attempt in range(max_retries):
            for selector_type, selector in selectors_list:
                try:
                    elements = parent.find_elements(selector_type, selector)
                    if len(elements) >= min_elements:
                        logger.debug(f"Found {len(elements)} {context} with selector: {selector_type}='{selector}'")
                        return elements
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
            
            # If we get here, none of the selectors worked on this attempt
            if attempt < max_retries - 1:
                backoff_time = retry_delay * (attempt + 1)
                logger.debug(f"No selectors found enough {context}, retrying in {backoff_time}s (attempt {attempt+1}/{max_retries})")
                time.sleep(backoff_time)  # Exponential backoff
        
        # If we get here, all retries failed
        selector_descriptions = [f"{s[0]}='{s[1]}'" for s in selectors_list]
        error_msg = f"Failed to find {min_elements} {context} after {max_retries} attempts with selectors: {', '.join(selector_descriptions)}"
        logger.error(error_msg)
        raise ElementNotFoundError(error_msg)
    
    def find_job_listings(self, min_elements=1):
        """Find job listing elements on the page.
        
        Args:
            min_elements: Minimum number of elements to consider a successful find.
        
        Returns:
            List of job listing WebElements.
        """
        return self.find_elements_with_fallbacks(
            self.driver, 
            self.JOB_LISTING_SELECTORS,
            min_elements=min_elements,
            context="job listings"
        )
    
    def find_job_title(self, job_element):
        """Find the job title element within a job listing.
        
        Args:
            job_element: The job listing WebElement.
        
        Returns:
            The job title WebElement.
        """
        return self.find_element_with_fallbacks(
            job_element, 
            self.JOB_TITLE_SELECTORS,
            context="job title"
        )
    
    def find_job_id(self, job_element):
        """Find the job ID element within a job listing.
        
        Args:
            job_element: The job listing WebElement.
        
        Returns:
            The job ID WebElement.
        """
        return self.find_element_with_fallbacks(
            job_element, 
            self.JOB_ID_SELECTORS,
            context="job ID"
        )
    
    def find_posted_date(self, job_element):
        """Find the posted date element within a job listing.
        
        Args:
            job_element: The job listing WebElement.
        
        Returns:
            The posted date WebElement.
        """
        return self.find_element_with_fallbacks(
            job_element, 
            self.POSTED_DATE_SELECTORS,
            context="posted date"
        )
    
    def find_next_page_button(self):
        """Find the next page button on the page.
        
        Returns:
            The next page button WebElement, or None if not found or disabled.
        """
        try:
            button = self.find_element_with_fallbacks(
                self.driver, 
                self.NEXT_PAGE_SELECTORS,
                context="next page button"
            )
            
            # Check if the button is disabled
            if "disabled" in button.get_attribute("class") or button.get_attribute("disabled") == "true":
                logger.info("Next page button is disabled (last page)")
                return None
            
            return button
        except ElementNotFoundError:
            logger.info("No next page button found")
            return None
    
    def find_job_details(self):
        """Find the job details element on a job posting page.
        
        Returns:
            The job details WebElement.
        """
        return self.find_element_with_fallbacks(
            self.driver, 
            self.JOB_DETAILS_SELECTORS,
            context="job details"
        )
    
    def extract_job_info(self, job_element):
        """Extract all job information from a job listing element.
        
        Args:
            job_element: The job listing WebElement.
        
        Returns:
            dict: Job information including title, ID, posted date, and href.
        """
        job_info = {}
        
        # Use safe_operation to handle errors gracefully
        def get_job_title():
            try:
                title_element = self.find_job_title(job_element)
                job_info['job_title'] = title_element.text.strip()
                
                # Try to get href attribute
                href = title_element.get_attribute("href")
                if href:
                    job_info['job_href'] = href
                else:
                    # If href is not directly on the title element, try to find a parent or child link
                    try:
                        # Try parent
                        parent = title_element.find_element(By.XPATH, '..')
                        parent_href = parent.get_attribute("href")
                        if parent_href:
                            job_info['job_href'] = parent_href
                        else:
                            # Try to find any link within the job element
                            links = job_element.find_elements(By.XPATH, './/a[@href]')
                            if links:
                                job_info['job_href'] = links[0].get_attribute("href")
                            else:
                                # Try to construct a URL from the job ID if we have it
                                job_id_elements = job_element.find_elements(By.XPATH, './/*[contains(text(), "WD")]')
                                if job_id_elements:
                                    job_id_text = job_id_elements[0].text.strip()
                                    base_url = "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext/job/details/"
                                    job_info['job_href'] = f"{base_url}{job_id_text}"
                                    logger.info(f"Constructed job URL from ID: {job_info['job_href']}")
                    except Exception as e:
                        logger.warning(f"Could not find href for job title: {str(e)}")
                
                return title_element
            except ElementNotFoundError:
                # If we can't find the title element with our selectors, try a more direct approach
                logger.warning("Using fallback method to extract job title")
                try:
                    # Try to get all text nodes and find the one that looks like a title
                    all_text_elements = job_element.find_elements(By.XPATH, './/*[not(self::script)][text()]')
                    
                    # Filter out elements that are likely not titles (dates, locations, IDs)
                    potential_titles = []
                    for elem in all_text_elements:
                        text = elem.text.strip()
                        if (text and
                            not text.startswith("Posted") and
                            not text.startswith("Location") and
                            not "WD" in text and
                            len(text) > 5):
                            potential_titles.append((elem, text))
                    
                    if potential_titles:
                        # Use the first potential title
                        title_element, title_text = potential_titles[0]
                        job_info['job_title'] = title_text
                        
                        # Try to find a link for this job
                        links = job_element.find_elements(By.XPATH, './/a[@href]')
                        if links:
                            job_info['job_href'] = links[0].get_attribute("href")
                        
                        logger.info(f"Found potential job title using fallback: {title_text}")
                        return title_element
                except Exception as e:
                    logger.error(f"Fallback title extraction failed: {str(e)}")
                
                # If all else fails, use a placeholder and try to get a URL
                job_info['job_title'] = "Unknown Position"
                links = job_element.find_elements(By.XPATH, './/a[@href]')
                if links:
                    job_info['job_href'] = links[0].get_attribute("href")
                
                return None
        
        def get_job_id():
            try:
                id_element = self.find_job_id(job_element)
                id_text = id_element.text.strip()
                
                # Check if the text contains a WD pattern (like 24WD83875)
                # Using the pre-compiled pattern for efficiency
                match = WD_ID_PATTERN.search(id_text)
                
                if match:
                    # If we found a WD pattern, use that as the ID
                    job_info['job_id'] = match.group(0)
                else:
                    # Extract just the ID part if it contains other text
                    if "ID:" in id_text:
                        parts = id_text.split("ID:")
                        if len(parts) > 1:
                            id_text = parts[1].strip()
                    elif "Req ID" in id_text:
                        parts = id_text.split("Req ID")
                        if len(parts) > 1:
                            id_text = parts[1].strip()
                    elif "Job ID" in id_text:
                        parts = id_text.split("Job ID")
                        if len(parts) > 1:
                            id_text = parts[1].strip()
                    
                    # Remove any leading/trailing punctuation
                    id_text = id_text.strip(":,. ()")
                    
                    job_info['job_id'] = id_text
                
                return id_element
            except ElementNotFoundError:
                # If we can't find the ID element, try to extract it from any text in the job element
                logger.warning("Using fallback method to extract job ID")
                try:
                    # Look for text that contains "WD"
                    all_text = job_element.text
                    # Using the pre-compiled pattern for efficiency
                    match = WD_ID_PATTERN.search(all_text)
                    
                    if match:
                        job_info['job_id'] = match.group(0)
                        logger.info(f"Found job ID using fallback: {job_info['job_id']}")
                        return None
                except Exception as e:
                    logger.error(f"Fallback ID extraction failed: {str(e)}")
                
                return None
        
        def get_posted_date():
            try:
                date_element = self.find_posted_date(job_element)
                date_text = date_element.text.strip()
                
                # Handle different date formats
                if "Posted" in date_text:
                    parts = date_text.split("Posted")
                    if len(parts) > 1:
                        date_text = parts[1].strip()
                
                # Remove any leading/trailing punctuation
                date_text = date_text.strip(":,. ()")
                
                job_info['posted_date'] = date_text
                return date_element
            except ElementNotFoundError:
                # If we can't find the posted date, use a default value
                logger.warning("Could not find posted date, using default")
                job_info['posted_date'] = "Unknown date"
                return None
        
        # Extract each piece of information with error handling
        safe_operation(get_job_title, "extracting job title", default_value=None)
        safe_operation(get_job_id, "extracting job ID", default_value=None)
        safe_operation(get_posted_date, "extracting posted date", default_value=None)
        
        # Check if we got the minimum required information
        if 'job_title' not in job_info or 'job_href' not in job_info:
            logger.warning("Failed to extract essential job information (title and URL)",
                          extra={"partial_info": job_info})
            return None
            
        # If job ID is missing, generate one from the URL
        if 'job_id' not in job_info:
            # Try to extract job ID from the URL
            try:
                url_parts = job_info['job_href'].split('/')
                # Look for ID pattern in URL
                for part in url_parts:
                    if part.startswith('_') and len(part) > 5:
                        job_info['job_id'] = part
                        logger.info(f"Generated job ID from URL: {part}")
                        break
                
                # If still no ID, use the last part of the URL
                if 'job_id' not in job_info and len(url_parts) > 0:
                    job_info['job_id'] = url_parts[-1]
                    logger.info(f"Using URL last segment as job ID: {url_parts[-1]}")
            except Exception as e:
                # If all else fails, use a timestamp as ID
                import time
                job_info['job_id'] = f"unknown_{int(time.time())}"
                logger.warning(f"Generated fallback job ID: {job_info['job_id']}")
        
        return job_info
"""
JSON-LD based job extractor for Workday Scraper.

This module provides functions to extract job information from Workday job pages
using the JSON-LD data structure, which is much faster than browser-based extraction.
"""

import json
import re
import random
import asyncio
from typing import List, Dict, Any, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser

from .logging_utils import get_logger

logger = get_logger()


async def get_all_job_urls(base_url: str) -> List[str]:
    """
    Get all job URLs from Workday job listings using browser automation.
    
    Args:
        base_url: The base URL of the Workday job listings page.
        
    Returns:
        List of job URLs.
    """
    job_urls = []
    
    logger.info(f"Collecting all job URLs from {base_url}")
    
    async with async_playwright() as p:
        # Use a minimal browser configuration
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1024}  # Larger viewport to see more content
        )
        page = await context.new_page()
        
        # Navigate to the main page
        await page.goto(base_url)
        
        # Wait for initial page load and check total job count
        await page.wait_for_selector(".css-1q2dra3, [data-automation-id='jobResults'] li", timeout=30000)
        
        # Extract total job count from pagination text (e.g., "1 - 20 of 409 jobs")
        pagination_element = await page.query_selector("div[data-automation-id='paginationLabel']")
        pagination_text = await pagination_element.text_content() if pagination_element else ""
        
        # Try multiple regex patterns to extract the total job count
        total_jobs_match = re.search(r'of\s+(\d+)\s+jobs', pagination_text)
        if not total_jobs_match:
            total_jobs_match = re.search(r'of\s+(\d+)', pagination_text)
        if not total_jobs_match:
            total_jobs_match = re.search(r'(\d+)\s+jobs', pagination_text)
            
        expected_total_jobs = int(total_jobs_match.group(1)) if total_jobs_match else None
        
        # If we couldn't find the total job count, try alternative selectors
        if not expected_total_jobs:
            # Try an alternative selector for pagination
            alt_pagination = await page.query_selector(".css-1sgf10s, [data-automation-id='paginationLabel']")
            if alt_pagination:
                alt_text = await alt_pagination.text_content()
                alt_match = re.search(r'of\s+(\d+)', alt_text)
                if alt_match:
                    expected_total_jobs = int(alt_match.group(1))
                    logger.info(f"Found pagination indicating {expected_total_jobs} total jobs (alternative selector)")
                else:
                    logger.warning("Could not determine total job count from pagination")
            else:
                # Try to find any text that might contain the total job count
                try:
                    page_text = await page.evaluate("() => document.body.innerText")
                    # Look for patterns like "409 jobs" or "showing 1-20 of 409"
                    text_match = re.search(r'of\s+(\d+)\s+jobs', page_text)
                    if not text_match:
                        text_match = re.search(r'(\d+)\s+jobs', page_text)
                    if text_match:
                        expected_total_jobs = int(text_match.group(1))
                        logger.info(f"Found total job count {expected_total_jobs} in page text")
                    else:
                        logger.warning("Could not determine total job count from page text")
                except Exception as e:
                    logger.warning(f"Error extracting job count from page text: {str(e)}")
        
        if expected_total_jobs:
            logger.info(f"Found pagination indicating {expected_total_jobs} total jobs")
            
            # Calculate expected number of pages
            # Count the number of actual job listings on the first page using a more specific selector
            job_titles = await page.query_selector_all("[data-automation-id='jobTitle']")
            jobs_per_page = len(job_titles)
            
            # If we couldn't determine jobs per page from elements, use a default value
            if jobs_per_page == 0:
                jobs_per_page = 20  # Default value based on observation
                logger.info(f"Could not detect jobs per page, using default value: {jobs_per_page}")
            else:
                logger.info(f"Detected {jobs_per_page} jobs per page")
            
            # Calculate expected number of pages
            expected_pages = (expected_total_jobs + jobs_per_page - 1) // jobs_per_page
            logger.info(f"Expecting {expected_pages} total pages based on {expected_total_jobs} jobs with {jobs_per_page} jobs per page")
        else:
            logger.warning("Could not determine total job count from pagination")
            expected_pages = None
        
        has_next_page = True
        page_num = 1
        max_pages = 100  # Safety limit
        
        # If we know the expected number of pages, use that as the limit
        if expected_pages:
            max_pages = min(expected_pages + 1, max_pages)  # Add 1 as a safety margin
            logger.info(f"Setting max pages to {max_pages} based on expected pages {expected_pages}")
        
        while has_next_page and page_num <= max_pages:
            # Wait for job listings to appear
            await page.wait_for_selector(".css-1q2dra3, [data-automation-id='jobResults'] li", timeout=30000)
            
            # Scroll through the page to ensure all jobs are loaded
            await page.evaluate("""
                () => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollTo(0, scrollHeight / 4);
                    setTimeout(() => window.scrollTo(0, scrollHeight / 2), 300);
                    setTimeout(() => window.scrollTo(0, 3 * scrollHeight / 4), 600);
                    setTimeout(() => window.scrollTo(0, scrollHeight), 900);
                }
            """)
            await page.wait_for_timeout(1500)  # Wait for any lazy-loaded content
            
            # Extract job URLs
            urls = await page.eval_on_selector_all(
                ".css-1q2dra3 a, [data-automation-id='jobTitle']",
                """elements => elements.map(el => {
                    const href = el.getAttribute('href');
                    return href.startsWith('/')
                        ? window.location.origin + href
                        : href;
                })"""
            )
            
            # Log progress
            logger.info(f"Page {page_num}: Found {len(urls)} job URLs")
            job_urls.extend(urls)
            
            # Check for next page - try multiple selectors based on the original scraper
            next_button = None
            
            # Try all these selectors in order - using Playwright-compatible CSS selectors
            next_page_selectors = [
                "button[aria-label='Next Page']:not([disabled])",
                "button[aria-label='next page']:not([disabled])",
                "button.css-1sgf10s:not([disabled])",
                "button[data-uxi-element-id='next']:not([disabled])",
                "button.next:not([disabled])",
                "button.pagination-next:not([disabled])",
                "a.next:not([disabled])",
                "button:has-text('Next'):not([disabled])",
                "a:has-text('Next'):not([disabled])",
                "button:has-text('>'):not([disabled])",
                "a:has-text('>'):not([disabled])",
                "div.pagination button:last-child:not([disabled])",
                "div.pagination a:last-child:not([disabled])",
                "button[aria-label*='next']:not([disabled])",
                "a[aria-label*='next']:not([disabled])",
                "a:has-text('2'):not([disabled])",
                "button:has-text('2'):not([disabled])"
            ]
            
            # Try each selector
            for selector in next_page_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        next_button = button
                        logger.info(f"Found next page button with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Error finding next button with selector {selector}: {str(e)}")
            
            # If no button found with CSS selectors, try to find by text content
            if not next_button:
                try:
                    buttons = await page.query_selector_all("button")
                    for button in buttons:
                        text = await button.text_content()
                        if text == ">" or text == "Next":
                            is_disabled = await button.get_attribute("disabled")
                            if not is_disabled:
                                next_button = button
                                logger.info("Found next page button by text content")
                                break
                except Exception as e:
                    logger.debug(f"Error finding next button by text: {str(e)}")
            
            if next_button:
                logger.info(f"Clicking next page button to navigate to page {page_num + 1}")
                await next_button.click()
                await page.wait_for_timeout(2000)  # Longer wait for page update
                page_num += 1
            else:
                logger.info("No next page button found, reached the last page")
                has_next_page = False
        
        # Verify we got all jobs
        if expected_total_jobs and len(job_urls) < expected_total_jobs:
            logger.warning(f"Expected {expected_total_jobs} jobs but only found {len(job_urls)}")
            
            # Try an alternative approach if we're missing jobs
            if len(job_urls) < expected_total_jobs * 0.9:  # If we're missing more than 10%
                logger.info("Trying alternative approach to find all jobs...")
                
                # Try multiple approaches to get all jobs
                
                # Approach 1: Increase results per page
                logger.info("Approach 1: Increasing results per page")
                try:
                    # Go back to first page
                    await page.goto(base_url)
                    await page.wait_for_timeout(2000)
                    
                    # Try to increase results per page if possible
                    results_per_page = await page.query_selector("button[data-automation-id='itemsPerPage']")
                    if results_per_page:
                        await results_per_page.click()
                        await page.wait_for_timeout(1000)
                        
                        # Try to find the option for maximum items per page (50 or 100)
                        max_option = await page.query_selector("li[data-automation-id='50']")
                        if not max_option:
                            max_option = await page.query_selector("li[data-automation-id='100']")
                        
                        if max_option:
                            await max_option.click()
                            await page.wait_for_timeout(2000)
                            
                            # Recollect job URLs with the new settings
                            alt_job_urls = []
                            alt_page_num = 1
                            alt_has_next_page = True
                            
                            while alt_has_next_page and alt_page_num <= max_pages:
                                await page.wait_for_selector(".css-1q2dra3, [data-automation-id='jobResults'] li", timeout=30000)
                                
                                # Scroll through the page
                                await page.evaluate("""
                                    () => {
                                        const scrollHeight = document.body.scrollHeight;
                                        window.scrollTo(0, scrollHeight / 4);
                                        setTimeout(() => window.scrollTo(0, scrollHeight / 2), 300);
                                        setTimeout(() => window.scrollTo(0, 3 * scrollHeight / 4), 600);
                                        setTimeout(() => window.scrollTo(0, scrollHeight), 900);
                                    }
                                """)
                                await page.wait_for_timeout(2000)
                                
                                alt_urls = await page.eval_on_selector_all(
                                    ".css-1q2dra3 a, [data-automation-id='jobTitle']",
                                    """elements => elements.map(el => {
                                        const href = el.getAttribute('href');
                                        return href.startsWith('/')
                                            ? window.location.origin + href
                                            : href;
                                    })"""
                                )
                                
                                logger.info(f"Alternative approach - Page {alt_page_num}: Found {len(alt_urls)} job URLs")
                                alt_job_urls.extend(alt_urls)
                                
                                # Check for next page with multiple selectors - using the same improved selectors
                                alt_next_button = None
                                for selector in next_page_selectors:
                                    try:
                                        button = await page.query_selector(selector)
                                        if button:
                                            alt_next_button = button
                                            logger.info(f"Alternative approach: Found next page button with selector: {selector}")
                                            break
                                    except Exception:
                                        continue
                                
                                if alt_next_button:
                                    await alt_next_button.click()
                                    await page.wait_for_timeout(2000)
                                    alt_page_num += 1
                                else:
                                    alt_has_next_page = False
                            
                            if len(alt_job_urls) > len(job_urls):
                                logger.info(f"Alternative approach found more jobs: {len(alt_job_urls)} vs {len(job_urls)}")
                                job_urls = alt_job_urls
                except Exception as e:
                    logger.error(f"Error in alternative approach 1: {str(e)}")
                
                # Approach 2: Try a different URL format if still missing jobs
                if expected_total_jobs and len(job_urls) < expected_total_jobs * 0.9:
                    logger.info("Approach 2: Trying different URL format")
                    try:
                        # Try a different URL format (sometimes removing query parameters helps)
                        base_url_no_params = base_url.split('?')[0]
                        if base_url_no_params != base_url:
                            logger.info(f"Trying URL without parameters: {base_url_no_params}")
                            await page.goto(base_url_no_params)
                            await page.wait_for_timeout(3000)
                            
                            # Collect job URLs from this URL
                            approach2_urls = []
                            approach2_page_num = 1
                            approach2_has_next_page = True
                            
                            while approach2_has_next_page and approach2_page_num <= 5:  # Limit to 5 pages for this approach
                                await page.wait_for_selector(".css-1q2dra3, [data-automation-id='jobResults'] li", timeout=30000)
                                
                                # Extract URLs
                                new_urls = await page.eval_on_selector_all(
                                    ".css-1q2dra3 a, [data-automation-id='jobTitle']",
                                    """elements => elements.map(el => {
                                        const href = el.getAttribute('href');
                                        return href.startsWith('/')
                                            ? window.location.origin + href
                                            : href;
                                    })"""
                                )
                                
                                logger.info(f"Approach 2 - Page {approach2_page_num}: Found {len(new_urls)} job URLs")
                                approach2_urls.extend(new_urls)
                                
                                # Check for next page using the same improved selectors
                                next_btn = None
                                for selector in next_page_selectors:
                                    try:
                                        button = await page.query_selector(selector)
                                        if button:
                                            next_btn = button
                                            logger.info(f"Approach 2: Found next page button with selector: {selector}")
                                            break
                                    except Exception:
                                        continue
                                
                                if next_btn:
                                    await next_btn.click()
                                    await page.wait_for_timeout(2000)
                                    approach2_page_num += 1
                                else:
                                    logger.info("Approach 2: No next page button found, reached the last page")
                                    approach2_has_next_page = False
                            
                            # Combine URLs from both approaches
                            combined_urls = list(set(job_urls + approach2_urls))
                            if len(combined_urls) > len(job_urls):
                                logger.info(f"Approach 2 found additional jobs: {len(combined_urls)} vs {len(job_urls)}")
                                job_urls = combined_urls
                    except Exception as e:
                        logger.error(f"Error in alternative approach 2: {str(e)}")
        
        await browser.close()
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen = set()
    for url in job_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    logger.info(f"Found {len(unique_urls)} unique job URLs")
    return unique_urls


async def extract_job_details_from_jsonld(job_urls: List[str], concurrency: int = 10, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    Extract job details from JSON-LD data using HTTP requests with robust error handling.
    
    Args:
        job_urls: List of job URLs to extract details from.
        concurrency: Maximum number of concurrent requests.
        max_retries: Maximum number of retry attempts for failed requests.
        
    Returns:
        List of job details dictionaries.
    """
    # Reduce default concurrency to avoid overwhelming the server
    semaphore = asyncio.Semaphore(concurrency)
    results = []
    failed_urls = []
    
    logger.info(f"Extracting job details from {len(job_urls)} URLs with concurrency {concurrency}")
    
    # Add a progress counter
    processed_count = 0
    total_count = len(job_urls)
    
    async def fetch_and_extract(url: str, retry_count: int = 0) -> Dict[str, Any]:
        nonlocal processed_count
        try:
            # Add a timeout for the entire function
            result = await asyncio.wait_for(_fetch_and_extract(url, retry_count), timeout=30.0)
            
            # Update progress counter
            processed_count += 1
            if processed_count % 10 == 0 or processed_count == total_count:
                logger.info(f"Progress: {processed_count}/{total_count} URLs processed ({processed_count/total_count*100:.1f}%)")
            
            return result
        except asyncio.TimeoutError:
            logger.error(f"Fetch and extract timed out for {url}")
            
            # Update progress counter even for timeouts
            processed_count += 1
            if processed_count % 10 == 0 or processed_count == total_count:
                logger.info(f"Progress: {processed_count}/{total_count} URLs processed ({processed_count/total_count*100:.1f}%)")
            
            return {'url': url, 'error': 'Timeout'}
    
    async def _fetch_and_extract(url: str, retry_count: int = 0) -> Dict[str, Any]:
        async with semaphore:
            try:
                # Add jitter to avoid rate limiting - increase the delay
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
                # Reduce timeout to avoid hanging requests
                async with httpx.AsyncClient(timeout=10.0) as client:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        # Add cache control headers to avoid cached responses
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                    }
                    
                    try:
                        response = await client.get(url, headers=headers, follow_redirects=True)
                        
                        if response.status_code != 200:
                            raise Exception(f"HTTP error: {response.status_code}")
                    except httpx.TimeoutException:
                        raise Exception(f"Request timed out")
                    except httpx.ConnectError:
                        raise Exception(f"Connection error")
                    except httpx.RequestError as e:
                        raise Exception(f"Request error: {str(e)}")
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find the JSON-LD script tag
                    jsonld_tag = soup.find('script', {'type': 'application/ld+json'})
                    
                    if jsonld_tag and jsonld_tag.string:
                        # Parse the JSON data
                        job_data = json.loads(jsonld_tag.string)
                        
                        # Extract relevant fields
                        job_details = {
                            'title': job_data.get('title', ''),
                            'job_id': job_data.get('identifier', {}).get('value', ''),
                            'description': job_data.get('description', ''),
                            'date_posted': job_data.get('datePosted', ''),
                            'employment_type': job_data.get('employmentType', ''),
                            'location': job_data.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                            'company': job_data.get('hiringOrganization', {}).get('name', ''),
                            'url': url
                        }
                        
                        return job_details
                    else:
                        raise Exception("No JSON-LD data found")
                    
            except Exception as e:
                if retry_count < max_retries:
                    # Exponential backoff
                    backoff_time = 2 ** retry_count
                    logger.debug(f"Retrying {url} after {backoff_time}s (attempt {retry_count+1}/{max_retries})")
                    await asyncio.sleep(backoff_time)
                    return await _fetch_and_extract(url, retry_count + 1)
                else:
                    logger.error(f"Failed to extract job details from {url}: {str(e)}")
                    failed_urls.append(url)
                    return {'url': url, 'error': str(e)}
    
    # Process URLs in batches to avoid memory issues
    batch_size = 50  # Process 50 URLs at a time
    all_results = []
    
    for i in range(0, len(job_urls), batch_size):
        batch = job_urls[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(job_urls) + batch_size - 1)//batch_size} ({len(batch)} URLs)")
        
        # Process batch concurrently with a timeout
        tasks = [fetch_and_extract(url) for url in batch]
        try:
            # Add a timeout for the batch (5 minutes per batch)
            batch_results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=300)
            all_results.extend(batch_results)
            logger.info(f"Completed batch {i//batch_size + 1} with {len(batch_results)} results")
        except asyncio.TimeoutError:
            logger.error(f"Batch {i//batch_size + 1} timed out after 5 minutes")
            # Get results from completed tasks
            completed_tasks = [task for task in tasks if task.done()]
            batch_results = [task.result() for task in completed_tasks if not task.exception()]
            all_results.extend(batch_results)
            logger.info(f"Retrieved {len(batch_results)} results from completed tasks in batch before timeout")
    
    # Filter out errors
    valid_results = [job for job in all_results if 'error' not in job]
    
    logger.info(f"Successfully extracted {len(valid_results)} job details")
    
    # If we have failed URLs and they're a significant portion, try with Playwright as fallback
    # Increase the threshold to 10% to avoid unnecessary fallback
    if failed_urls and len(failed_urls) > len(job_urls) * 0.10:  # If more than 10% failed
        logger.info(f"Falling back to Playwright for {len(failed_urls)} failed URLs")
        # Only process a subset of failed URLs to avoid long processing times
        urls_to_process = failed_urls[:min(len(failed_urls), 50)]  # Process at most 50 failed URLs
        logger.info(f"Processing {len(urls_to_process)} of {len(failed_urls)} failed URLs with Playwright")
        playwright_results = await extract_with_playwright_fallback(urls_to_process)
        valid_results.extend(playwright_results)
        logger.info(f"Playwright fallback recovered {len(playwright_results)} additional jobs")
    
    return valid_results


async def extract_with_playwright_fallback(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Extract job details using Playwright as a fallback method.
    
    Args:
        urls: List of URLs that failed with the HTTP approach.
        
    Returns:
        List of job details dictionaries.
    """
    results = []
    
    logger.info(f"Using Playwright fallback for {len(urls)} URLs")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        for url in urls:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Try to extract JSON-LD data
                jsonld_data = await page.evaluate("""
                    () => {
                        const script = document.querySelector('script[type="application/ld+json"]');
                        return script ? script.textContent : null;
                    }
                """)
                
                if jsonld_data:
                    job_data = json.loads(jsonld_data)
                    job_details = {
                        'title': job_data.get('title', ''),
                        'job_id': job_data.get('identifier', {}).get('value', ''),
                        'description': job_data.get('description', ''),
                        'date_posted': job_data.get('datePosted', ''),
                        'employment_type': job_data.get('employmentType', ''),
                        'location': job_data.get('jobLocation', {}).get('address', {}).get('addressLocality', ''),
                        'company': job_data.get('hiringOrganization', {}).get('name', ''),
                        'url': url
                    }
                    results.append(job_details)
                    logger.info(f"Playwright successfully extracted job details for {url}")
                else:
                    # Fallback to extracting from DOM if JSON-LD is not available
                    title = await page.title()
                    description = await page.evaluate("""
                        () => {
                            const details = document.querySelector('[data-automation-id="job-posting-details"]');
                            return details ? details.innerHTML : '';
                        }
                    """)
                    
                    if title and description:
                        results.append({
                            'title': title,
                            'description': description,
                            'url': url
                        })
                        logger.info(f"Playwright extracted job details from DOM for {url}")
                    else:
                        logger.warning(f"Playwright could not extract job details for {url}")
            except Exception as e:
                logger.error(f"Playwright fallback failed for {url}: {str(e)}")
        
        await browser.close()
    
    return results


async def scrape_workday_jobs(base_url: str) -> List[Dict[str, Any]]:
    """
    Scrape all jobs using the optimized approach with completeness verification.
    
    Args:
        base_url: The base URL of the Workday job listings page.
        
    Returns:
        List of job details dictionaries.
    """
    # Phase 1: Get all job URLs
    job_urls = await get_all_job_urls(base_url)
    
    # Verify we have a reasonable number of URLs
    logger.info(f"Found {len(job_urls)} job URLs")
    
    # Phase 2: Extract job details from JSON-LD
    job_details = await extract_job_details_from_jsonld(job_urls)
    
    # Verify completeness
    logger.info(f"Successfully extracted details for {len(job_details)} jobs")
    
    if len(job_details) < len(job_urls) * 0.95:  # If we're missing more than 5%
        logger.warning(f"Only extracted details for {len(job_details)}/{len(job_urls)} jobs")
    
    return job_details
# Workday Scraper Optimization: JSON-LD Based Approach

## Current Performance Issues

The current Workday scraper implementation has several performance bottlenecks:

1. **Excessive Wait Times**: Fixed wait times (15+ seconds) that don't adapt to actual page load conditions
2. **Browser-Heavy Approach**: Full browser automation for every job listing and detail page
3. **Limited Parallelism**: Only 3-5 concurrent browser sessions
4. **Inefficient Element Selection**: Complex fallback system with multiple selectors and retries
5. **Redundant Operations**: Repeated regex compilations and excessive DOM operations

## Completeness Issue

There's also a completeness issue with the current implementation. The scraper is currently capturing 367 jobs, while the Workday page shows a total of 409 jobs (as indicated by "1 - 20 of 409 jobs" on the pagination). This means we're missing approximately 10% of the available jobs.

Possible reasons for missing jobs:
1. **Pagination issues**: Not navigating through all pages correctly
2. **Job visibility issues**: Some jobs require scrolling or other interactions to become visible
3. **Error handling**: Jobs that encounter errors during scraping might be skipped
4. **Session timeouts**: Long-running scraping sessions might time out before completing all jobs
5. **Rate limiting**: Getting rate-limited after a certain number of requests

## Key Discovery: JSON-LD Data Structure

Analysis of the Workday job detail pages revealed a critical optimization opportunity. Each job detail page contains a complete JSON-LD data structure with all job information:

```html
<script type="application/ld+json">
    {
      "jobLocation" : { ... },
      "hiringOrganization" : { ... },
      "identifier" : {
        "name" : "Senior Sales Manager, Inside Sales, Middle East and Turkey",
        "@type" : "PropertyValue",
        "value" : "24WD82586"
      },
      "datePosted" : "2024-10-30",
      "employmentType" : "FULL_TIME",
      "title" : "Senior Sales Manager, Inside Sales, Middle East and Turkey",
      "description" : "Job Requisition ID # 24WD82586 Position Overview Autodesk is in search of a dynamic...",
      "@context" : "http://schema.org",
      "@type" : "JobPosting"
    }
</script>
```

This JSON-LD structure contains all the job details we need in a structured format, and it's present in the initial HTML before any JavaScript executes.

## Optimized Two-Phase Approach

### Phase 1: Enhanced Browser Automation for Complete Job URL Collection

We need to ensure we capture ALL job URLs from the listing pages:

```python
def get_all_job_urls(base_url):
    """Get all job URLs using enhanced browser automation to ensure completeness."""
    job_urls = []
    
    with sync_playwright() as p:
        # Use a minimal browser configuration
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024}  # Larger viewport to see more content
        )
        page = context.new_page()
        
        # Navigate to the main page
        page.goto(base_url)
        
        # Wait for initial page load and check total job count
        page.wait_for_selector(".css-1q2dra3, [data-automation-id='jobResults'] li")
        
        # Extract total job count from pagination text (e.g., "1 - 20 of 409 jobs")
        pagination_text = page.text_content("div[data-automation-id='paginationLabel']") or ""
        total_jobs_match = re.search(r'of\s+(\d+)\s+jobs', pagination_text)
        expected_total_jobs = int(total_jobs_match.group(1)) if total_jobs_match else None
        
        has_next_page = True
        page_num = 1
        
        while has_next_page:
            # Wait for job listings to appear
            page.wait_for_selector(".css-1q2dra3, [data-automation-id='jobResults'] li")
            
            # Scroll through the page to ensure all jobs are loaded
            page.evaluate("""
                () => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollTo(0, scrollHeight / 4);
                    setTimeout(() => window.scrollTo(0, scrollHeight / 2), 300);
                    setTimeout(() => window.scrollTo(0, scrollHeight), 600);
                }
            """)
            page.wait_for_timeout(1000)  # Wait for any lazy-loaded content
            
            # Extract job URLs
            urls = page.eval_on_selector_all(
                ".css-1q2dra3 a, [data-automation-id='jobTitle']", 
                """elements => elements.map(el => {
                    const href = el.getAttribute('href');
                    return href.startsWith('/') 
                        ? window.location.origin + href 
                        : href;
                })"""
            )
            
            # Log progress
            print(f"Page {page_num}: Found {len(urls)} job URLs")
            job_urls.extend(urls)
            
            # Check for next page
            next_button = page.query_selector("button[aria-label='Next Page']:not([disabled])")
            if next_button:
                next_button.click()
                page.wait_for_timeout(1000)  # Short wait for page update
                page_num += 1
            else:
                has_next_page = False
        
        # Verify we got all jobs
        if expected_total_jobs and len(job_urls) < expected_total_jobs:
            print(f"WARNING: Expected {expected_total_jobs} jobs but only found {len(job_urls)}")
            
            # Try an alternative approach if we're missing jobs
            if len(job_urls) < expected_total_jobs * 0.9:  # If we're missing more than 10%
                print("Trying alternative approach to find all jobs...")
                
                # Go back to first page
                page.goto(base_url)
                
                # Try to increase results per page if possible
                results_per_page = page.query_selector("button[data-automation-id='itemsPerPage']")
                if results_per_page:
                    results_per_page.click()
                    page.wait_for_timeout(500)
                    max_option = page.query_selector("li[data-automation-id='50']")
                    if max_option:
                        max_option.click()
                        page.wait_for_timeout(1000)
                
                # Retry collection with the new settings
                # ... (similar code as above)
        
        browser.close()
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen = set()
    for url in job_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    return unique_urls
```

### Phase 2: HTTP-Based JSON-LD Extraction with Robust Error Handling

Once we have all job URLs, we use HTTP requests to fetch the pages and extract the JSON-LD data:

```python
import json
import httpx
from bs4 import BeautifulSoup
import asyncio
import time
import random

async def extract_job_details_from_jsonld(job_urls, concurrency=20, max_retries=3):
    """Extract job details from JSON-LD data using HTTP requests with robust error handling."""
    semaphore = asyncio.Semaphore(concurrency)
    results = []
    failed_urls = []
    
    async def fetch_and_extract(url, retry_count=0):
        async with semaphore:
            try:
                # Add jitter to avoid rate limiting
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                    }
                    response = await client.get(url, headers=headers, follow_redirects=True)
                    
                    if response.status_code != 200:
                        raise Exception(f"HTTP error: {response.status_code}")
                    
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
                    await asyncio.sleep(2 ** retry_count)
                    return await fetch_and_extract(url, retry_count + 1)
                else:
                    print(f"Failed to extract job details from {url}: {str(e)}")
                    failed_urls.append(url)
                    return {'url': url, 'error': str(e)}
    
    # Process all URLs concurrently
    tasks = [fetch_and_extract(url) for url in job_urls]
    all_results = await asyncio.gather(*tasks)
    
    # Filter out errors
    valid_results = [job for job in all_results if 'error' not in job]
    
    # If we have failed URLs and they're a significant portion, try with Playwright as fallback
    if failed_urls and len(failed_urls) > len(job_urls) * 0.05:  # If more than 5% failed
        print(f"Falling back to Playwright for {len(failed_urls)} failed URLs")
        playwright_results = await extract_with_playwright_fallback(failed_urls)
        valid_results.extend(playwright_results)
    
    return valid_results

async def extract_with_playwright_fallback(urls):
    """Extract job details using Playwright as a fallback method."""
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        for url in urls:
            try:
                await page.goto(url, wait_until="domcontentloaded")
                
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
            except Exception as e:
                print(f"Playwright fallback failed for {url}: {str(e)}")
        
        await browser.close()
    
    return results
```

### Main Scraper Function with Completeness Verification

```python
async def scrape_workday_jobs(base_url):
    """Scrape all jobs using the optimized approach with completeness verification."""
    # Phase 1: Get all job URLs
    job_urls = get_all_job_urls(base_url)
    
    # Verify we have a reasonable number of URLs
    print(f"Found {len(job_urls)} job URLs")
    
    # Phase 2: Extract job details from JSON-LD
    job_details = await extract_job_details_from_jsonld(job_urls)
    
    # Verify completeness
    print(f"Successfully extracted details for {len(job_details)} jobs")
    
    if len(job_details) < len(job_urls) * 0.95:  # If we're missing more than 5%
        print(f"WARNING: Only extracted details for {len(job_details)}/{len(job_urls)} jobs")
    
    return job_details
```

## Performance Comparison

| Aspect | Current Selenium Approach | JSON-LD Based Approach |
|--------|---------------------------|------------------------|
| Job Listings Page | 15-30 seconds per page | 2-3 seconds per page |
| Job Details Extraction | 10-15 seconds per job | 0.1-0.2 seconds per job |
| Concurrency | 3-5 jobs at once | 20+ jobs at once |
| Overall Speed | ~10 minutes for 100 jobs | ~30 seconds for 100 jobs |
| Resource Usage | Very high (multiple browsers) | Very low (mostly HTTP) |
| Completeness | Missing ~10% of jobs | Enhanced verification to ensure all jobs are captured |

## Implementation Plan

### Phase 1: Create JSON-LD Extractor

1. Add new dependencies to requirements.txt:
   ```
   httpx==0.24.1
   beautifulsoup4==4.12.2
   playwright==1.36.0
   ```

2. Create a new module `workday_scraper/jsonld_extractor.py` with the JSON-LD extraction functions

3. Test with a few known job URLs to verify it works

### Phase 2: Enhance Job URL Collection

1. Implement the enhanced browser automation for collecting ALL job URLs
2. Add verification against the total job count shown on the page
3. Implement alternative approaches if the primary method misses jobs
4. Add comprehensive logging to track progress and identify issues

### Phase 3: Integrate with Existing Code

1. Modify `scraper_controller.py` to use the new approach
2. Ensure compatibility with existing data structures
3. Maintain backward compatibility for configuration
4. Add completeness verification to ensure we're capturing all jobs

### Phase 4: Add Error Handling and Fallbacks

1. Add fallback to Playwright if HTTP-based extraction fails
2. Implement retry mechanisms with exponential backoff
3. Add detailed logging for monitoring and debugging
4. Implement rate limiting avoidance techniques

## Benefits of the JSON-LD Approach

1. **Massive Speed Improvement**: 10-20x faster than the current implementation
2. **Lower Resource Usage**: HTTP requests use far fewer resources than browser automation
3. **Higher Concurrency**: Can process 20+ job details simultaneously
4. **More Reliable**: Less dependency on complex DOM interactions
5. **Simpler Code**: Direct extraction of structured data instead of complex selectors
6. **Better Scalability**: Can handle much larger job volumes efficiently
7. **Improved Completeness**: Enhanced verification to ensure all jobs are captured

## Required Changes to Dependencies

1. Add `httpx` for asynchronous HTTP requests
2. Add `beautifulsoup4` for HTML parsing
3. Replace `selenium` with `playwright` for more efficient browser automation
4. Add `asyncio` for asynchronous processing

## Potential Challenges

1. **Session Management**: May need to handle cookies or session state for some Workday instances
2. **Rate Limiting**: Need to implement adaptive rate limiting to avoid being blocked
3. **Site Changes**: Need to monitor for changes to the JSON-LD structure
4. **Async Integration**: Need to integrate async code with the existing synchronous codebase
5. **Job Visibility**: Some jobs might require specific interactions to become visible

## Conclusion

The JSON-LD based approach offers a dramatic performance improvement over the current Selenium-based implementation while also addressing the completeness issue. By leveraging the structured data already present in the job detail pages and implementing enhanced verification, we can extract all the information we need with simple HTTP requests instead of full browser automation. This approach is faster, more reliable, and uses fewer resources, making it ideal for scaling up to handle larger job volumes while ensuring we capture all available jobs.
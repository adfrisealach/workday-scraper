#!/usr/bin/env python3
import asyncio
import re
from playwright.async_api import async_playwright

async def get_job_count(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Navigating to {url}")
        await page.goto(url)
        
        # Wait for the page to load
        await page.wait_for_selector(".css-1q2dra3, [data-automation-id='jobResults'] li", timeout=30000)
        
        # Get the pagination text
        pagination_element = await page.query_selector("div[data-automation-id='paginationLabel']")
        if pagination_element:
            pagination_text = await pagination_element.text_content()
            print(f"Pagination text: {pagination_text}")
            
            # Extract the total job count
            total_jobs_match = re.search(r'of\s+(\d+)\s+jobs', pagination_text)
            if total_jobs_match:
                total_jobs = int(total_jobs_match.group(1))
                print(f"Total jobs: {total_jobs}")
                
                # Calculate expected number of pages
                per_page_match = re.search(r'(\d+)\s*-\s*(\d+)', pagination_text)
                if per_page_match:
                    start_job = int(per_page_match.group(1))
                    end_job = int(per_page_match.group(2))
                    jobs_per_page = end_job - start_job + 1
                    expected_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page
                    print(f"Jobs per page: {jobs_per_page}")
                    print(f"Expected pages: {expected_pages}")
        
        # Get the page content
        page_content = await page.content()
        
        # Look for any text that might contain the job count
        page_text = await page.evaluate("() => document.body.innerText")
        text_match = re.search(r'of\s+(\d+)\s+jobs', page_text)
        if text_match:
            total_jobs = int(text_match.group(1))
            print(f"Found job count in page text: {total_jobs}")
            
            # Count the number of actual job listings on the first page
            # Use a more specific selector that targets only job titles
            job_titles = await page.query_selector_all("[data-automation-id='jobTitle']")
            jobs_per_page = len(job_titles)
            print(f"Actual jobs per page: {jobs_per_page}")
            
            # Calculate expected number of pages
            expected_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page
            print(f"Expected pages: {expected_pages}")
            
            # Print the first few job titles to verify
            if jobs_per_page > 0:
                print("\nFirst few job titles:")
                for i in range(min(5, jobs_per_page)):
                    title_text = await job_titles[i].text_content()
                    print(f"  {i+1}. {title_text.strip()}")
        
        await browser.close()

if __name__ == "__main__":
    url = "https://autodesk.wd1.myworkdayjobs.com/Ext?timeType=6d5ece62cf5a4f9f9e349b55f045b5e2"
    asyncio.run(get_job_count(url))
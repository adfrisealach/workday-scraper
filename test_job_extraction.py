#!/usr/bin/env python3
import asyncio
import json
import httpx
from bs4 import BeautifulSoup

async def extract_job_details(url):
    """Extract job details from a single URL."""
    print(f"Extracting job details from {url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            response = await client.get(url, headers=headers, follow_redirects=True)
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"HTTP error: {response.status_code}")
                return None
            
            # Save the response content to a file for inspection
            with open("job_page.html", "w") as f:
                f.write(response.text)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the JSON-LD script tag
            jsonld_tag = soup.find('script', {'type': 'application/ld+json'})
            
            if jsonld_tag and jsonld_tag.string:
                # Parse the JSON data
                job_data = json.loads(jsonld_tag.string)
                
                # Save the JSON-LD data to a file for inspection
                with open("job_data.json", "w") as f:
                    json.dump(job_data, f, indent=2)
                
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
                
                print(f"Successfully extracted job details: {job_details['title']}")
                return job_details
            else:
                print("No JSON-LD data found")
                
                # Try to extract basic information from the page
                title = soup.title.text if soup.title else "Unknown Title"
                print(f"Page title: {title}")
                
                # Look for job details in the DOM
                job_details_element = soup.find('div', {'data-automation-id': 'job-posting-details'})
                if job_details_element:
                    print("Found job details element in the DOM")
                else:
                    print("Could not find job details element in the DOM")
                
                return None
                
    except Exception as e:
        print(f"Error extracting job details: {str(e)}")
        return None

async def main():
    # Test with a URL that was failing in the logs
    url = "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext/job/Montreal-QC-CAN/Senior-Industry-Strategy-Manager---Content-Creation_24WD81528?timeType=6d5ece62cf5a4f9f9e349b55f045b5e2"
    
    job_details = await extract_job_details(url)
    
    if job_details:
        print("\nExtracted Job Details:")
        for key, value in job_details.items():
            if key != 'description':  # Skip the long description
                print(f"{key}: {value}")
        print("Description length:", len(job_details.get('description', '')))
    else:
        print("\nFailed to extract job details")

if __name__ == "__main__":
    asyncio.run(main())
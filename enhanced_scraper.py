import json
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
try:
    from webdriver_manager.chrome import ChromeDriverManager
    webdriver_manager_available = True
except ImportError:
    webdriver_manager_available = False
import time
import traceback
import sys
import os

def read_file(file):
    company_urls = {}
    with open(f"configs/{file}", "r") as inputfile:
        for line in inputfile:
            name, url = line.strip().split(",")
            company_urls[name] = url
    return company_urls

def get_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    # Add additional options that might help
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Use WebDriverManager if available, otherwise use default ChromeDriver
    if webdriver_manager_available:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    else:
        driver = webdriver.Chrome(options=options)
    return driver

def main():
    if len(sys.argv) < 2:
        print("Usage: python enhanced_scraper.py <config_file>")
        return
        
    file = sys.argv[1]
    
    # Check if config file exists
    if not os.path.exists(f"configs/{file}"):
        print(f"Config file 'configs/{file}' not found!")
        return
        
    company_urls = read_file(file)
    
    # Try with different configurations
    configurations = [
        {"headless": True, "wait_time": 5},
        {"headless": False, "wait_time": 5},
        {"headless": True, "wait_time": 10},
        {"headless": False, "wait_time": 10}
    ]
    
    for config in configurations:
        print(f"\nTrying with configuration: {config}")
        driver = None
        try:
            driver = get_driver(headless=config["headless"])
            wait = WebDriverWait(driver, 15)  # Longer wait timeout
            
            for company in company_urls:
                print(f"Scraping {company}...")
                company_url = company_urls[company]
                
                print(f"Opening URL: {company_url}")
                driver.get(company_url)
                print(f"Waiting for {config['wait_time']} seconds...")
                time.sleep(config["wait_time"])
                
                try:
                    print("Looking for job elements...")
                    # Try different XPaths
                    xpaths = [
                        '//li[@class="css-1q2dra3"]',
                        '//li[contains(@class, "css-")]',
                        '//div[contains(@data-automation-id, "jobResults")]/ul/li'
                    ]
                    
                    elements_found = False
                    for xpath in xpaths:
                        print(f"Trying XPath: {xpath}")
                        try:
                            elements = driver.find_elements(By.XPATH, xpath)
                            if elements:
                                print(f"Found {len(elements)} elements with XPath: {xpath}")
                                print(f"First element text: {elements[0].text}")
                                
                                # Try to find job details within the first element
                                try:
                                    job_title = elements[0].find_element(By.XPATH, ".//h3/a").text
                                    print(f"Job title: {job_title}")
                                    
                                    job_id = elements[0].find_element(By.XPATH, './/ul[@data-automation-id="subtitle"]/li').text
                                    print(f"Job ID: {job_id}")
                                    
                                    posted_on = elements[0].find_element(By.XPATH, './/dd[@class="css-129m7dg"][preceding-sibling::dt[contains(text(),"posted on")]]').text
                                    print(f"Posted on: {posted_on}")
                                    
                                    print("All job details found successfully!")
                                except Exception as e:
                                    print(f"Error finding job details: {str(e)}")
                                
                                elements_found = True
                                break
                        except Exception as e:
                            print(f"Error with XPath {xpath}: {str(e)}")
                    
                    if not elements_found:
                        print("No job elements found with any XPath!")
                        # Save page source for inspection
                        with open(f"{company}_page.html", "w") as f:
                            f.write(driver.page_source)
                        print(f"Page source saved to {company}_page.html")
                
                except Exception as e:
                    print(f"Error processing {company_url}:")
                    print(traceback.format_exc())
            
            if driver:
                driver.quit()
            print("\nTest completed successfully!")
            return
            
        except Exception as e:
            print("Error during test:")
            print(traceback.format_exc())
            if driver:
                try:
                    driver.quit()
                except:
                    pass

if __name__ == "__main__":
    main()
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

url = "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext"

options = Options()
# Comment out headless mode for debugging
# options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

print(f"Opening {url}...")
driver.get(url)
time.sleep(5)  # Wait for page to load

# Save the page source for inspection
with open("autodesk_page.html", "w") as f:
    f.write(driver.page_source)

print("Page source saved to autodesk_page.html")

# Try to find job elements with different XPaths
possible_xpaths = [
    '//li[@class="css-1q2dra3"]',  # Original
    '//li[contains(@class, "css-")]',  # Any li with css- class
    '//div[contains(@data-automation-id, "job")]',  # Job automation IDs
    '//h3/a',  # Job title links
    '//ul[@data-automation-id="subtitle"]'  # Job subtitle
]

for xpath in possible_xpaths:
    elements = driver.find_elements("xpath", xpath)
    print(f"XPath '{xpath}': {len(elements)} elements found")
    if elements:
        print(f"First element text: {elements[0].text}")

input("Press Enter to close the browser...")
driver.quit()
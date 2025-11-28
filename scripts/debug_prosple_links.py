import asyncio
import sys
import os

# Add project root to path to ensure imports work
sys.path.append(os.getcwd())

from playwright.async_api import async_playwright
from jobly.scrapers.prosple_scraper import ProspleScraper

async def get_first_page_links():
    # Initialize scraper (this will also init the DB connection, which is fine)
    scraper = ProspleScraper()
    
    # Construct the first page URL manually as per the scraper logic
    url = f"{scraper.search_url_base}&start=0"
    print(f"Target URL: {url}")
    
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Navigating and extracting links...")
        # Reuse the extraction logic from the scraper class
        job_links_data = await scraper._get_job_links(page, url)
        
        print(f"\nFound {len(job_links_data)} jobs on the first page:\n")
        for item in job_links_data:
            print(f"URL: {item['url']}")
            print(f"Salary: {item['salary']}")
            print("-" * 40)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_first_page_links())

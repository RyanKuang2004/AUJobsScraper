import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from playwright.async_api import async_playwright
from jobly.scrapers.prosple_scraper import ProspleScraper

async def fetch_links():
    scraper = ProspleScraper()
    url = f"{scraper.search_url_base}&start=320"
    print(f"Fetching links from: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Use the scraper's extraction logic
        job_links = await scraper._get_job_links(page, url)
        
        print(f"\nFound {len(job_links)} job links:\n")
        
        for link in job_links:
            print(link)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_links())

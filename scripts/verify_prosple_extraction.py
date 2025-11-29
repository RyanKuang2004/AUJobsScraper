import asyncio
from playwright.async_api import async_playwright
from unittest.mock import MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jobly.scrapers.prosple_scraper import ProspleScraper

async def verify_live():
    #url = "https://au.prosple.com/graduate-employers/macquarie-technology-group/jobs-internships/graduate-program-customer-service-professional-technology"
    # url = "https://au.prosple.com/graduate-employers/capgemini-australia-and-new-zealand/jobs-internships/graduate-program-early-2026-it-information-systems-cloud-applications"
    #url = "https://au.prosple.com/graduate-employers/jane-street/jobs-internships/quantitative-trader-3"
    url = "https://au.prosple.com/graduate-employers/amazon-australia-new-zealand/jobs-internships/software-dev-engineer-graduate-sydney-aws"
    
    print(f"Scraping live URL: {url}")
    
    scraper = ProspleScraper()
    # Mock DB and save_job
    scraper.db = MagicMock()
    scraper.save_job = lambda data: print(f"\nSAVED DATA:\n{data}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create context with user agent to match scraper
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        job_data = {"url": url}
        await scraper._process_job(page, job_data)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_live())

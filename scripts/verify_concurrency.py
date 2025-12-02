import asyncio
import logging
import time
from jobly.scrapers.base_scraper import BaseScraper
from jobly.config import settings
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class MockScraper(BaseScraper):
    def __init__(self):
        super().__init__("mock")
        
    async def _process_job(self, page, url):
        self.logger.info(f"Starting {url}")
        await asyncio.sleep(1)
        self.logger.info(f"Finished {url}")

async def main():
    # Set concurrency to 5
    settings.scraper.concurrency = 5
    
    scraper = MockScraper()
    urls = [f"job_{i}" for i in range(10)]
    
    print(f"Testing with {len(urls)} jobs and concurrency limit {settings.scraper.concurrency}")
    
    async with async_playwright() as p:
        browser, context = await scraper._setup_browser_context(p)
        
        start_time = time.time()
        await scraper.process_jobs_concurrently(context, urls)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"Total duration: {duration:.2f} seconds")
        
        # If sequential, it would take 10 seconds.
        # With concurrency 5, it should take approx 2 seconds.
        if duration < 3.5:
            print("SUCCESS: Jobs processed concurrently.")
        else:
            print("FAILURE: Jobs processed sequentially.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

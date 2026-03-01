"""Temp script: fetch and print one job from the Seek scraper."""
import asyncio
import json
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from aujobsscraper.scrapers.seek_scraper import SeekScraper


async def main():
    scraper = SeekScraper()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Grab first job link from the first search term
        url = "https://www.seek.com.au/software-engineer-jobs?page=1&daterange=7"
        print(f"Fetching job list: {url}")
        job_links = await scraper._get_job_links(page, url)

        if not job_links:
            print("No job links found.")
            await browser.close()
            return

        job_url = job_links[0]
        print(f"Scraping job: {job_url}\n")

        job_page = await context.new_page()
        await scraper._process_job(job_page, job_url)
        await job_page.close()
        await browser.close()

    if scraper._results:
        job = scraper._results[0]
        data = job.to_dict()
        # Truncate description for readability
        if len(data.get("description", "")) > 500:
            data["description"] = data["description"][:500] + "... [truncated]"
        print(json.dumps(data, indent=2, default=str))
    else:
        print("No job collected.")


if __name__ == "__main__":
    asyncio.run(main())

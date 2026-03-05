"""Temp script: fetch and print one job from the Seek scraper."""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright
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

        # job_url = job_links[0]
        job_url = "https://www.seek.com.au/job/90681332?ref=recom-homepage&pos=1&sp=3&origin=jobTitle#sol=b65f5a5d653d897ccd53e0309af963854b6685b7"
        print(f"Scraping job: {job_url}\n")

        job_page = await context.new_page()
        await scraper._process_job(job_page, job_url)
        await job_page.close()
        await browser.close()

    if not scraper._results:
        print("No job collected.")
        return

    jobs_data = [job.to_dict() for job in scraper._results]

    output_dir = Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "temp_seek_jobs.json"

    output_path.write_text(json.dumps(jobs_data, indent=2, default=str), encoding="utf-8")
    print(f"Saved {len(jobs_data)} job(s) to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())

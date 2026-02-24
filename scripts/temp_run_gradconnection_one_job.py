"""Temporarily run GradConnectionScraper for one job URL."""

import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper


async def run_one_job(url: str) -> None:
    scraper = GradConnectionScraper()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await scraper._process_job(page, {"url": url})
        finally:
            await page.close()
            await context.close()
            await browser.close()

    print(f"Processed jobs: {len(scraper._results)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Temporarily run one GradConnection job URL")
    parser.add_argument("url", help="GradConnection job URL")
    args = parser.parse_args()

    asyncio.run(run_one_job(args.url))


if __name__ == "__main__":
    main()

import argparse
import asyncio
import json

from playwright.async_api import async_playwright

from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper


async def run_one_job(url: str) -> None:
    scraper = GradConnectionScraper()
    scraper._results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
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
    if scraper._results:
        print(json.dumps(scraper._results[0].to_dict(), indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Temporarily run GradConnection scraper on one job URL."
    )
    parser.add_argument("url", help="GradConnection job detail URL")
    args = parser.parse_args()
    asyncio.run(run_one_job(args.url))


if __name__ == "__main__":
    main()

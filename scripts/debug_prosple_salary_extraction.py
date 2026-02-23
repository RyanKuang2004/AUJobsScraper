import argparse
import asyncio
import json
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from aujobsscraper.scrapers.prosple_scraper import ProspleScraper


def _print_json(label: str, value: Any) -> None:
    print(f"\n=== {label} ===")
    try:
        print(json.dumps(value, indent=2, default=str))
    except TypeError:
        print(str(value))


async def debug_url(url: str) -> None:
    scraper = ProspleScraper()

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
            print(f"Loading: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            content = await page.content()
            soup = BeautifulSoup(content, "lxml")

            json_data = scraper._extract_json_ld(soup)
            _print_json("JSON-LD JobPosting", json_data)

            base_salary = json_data.get("baseSalary") if isinstance(json_data, dict) else None
            _print_json("JSON-LD baseSalary", base_salary)

            extracted_salary = scraper._extract_salary(soup, json_data)
            _print_json("Prosple _extract_salary output", extracted_salary)
            print(f"Extracted salary Python type: {type(extracted_salary).__name__}")

            extracted_locations = scraper._extract_locations(soup, json_data)
            extracted_title = scraper._extract_title(soup, json_data)
            extracted_company = scraper._extract_company(soup, json_data)
            extracted_description = scraper._extract_description(soup, json_data)
            extracted_posted = scraper._extract_posted_date(json_data)
            extracted_closing = scraper._extract_closing_date(json_data)

            _print_json("Prosple extracted payload", {
                "title": extracted_title,
                "company": extracted_company,
                "locations": extracted_locations,
                "salary": extracted_salary,
                "posted_at": extracted_posted,
                "closing_date": extracted_closing,
            })

            print("\n=== JobPosting build check ===")
            try:
                job_posting = scraper._build_job_posting(
                    job_title=extracted_title,
                    company=extracted_company,
                    raw_locations=extracted_locations,
                    source_url=url,
                    description=extracted_description,
                    salary=extracted_salary,
                    posted_at=extracted_posted,
                    closing_date=extracted_closing,
                )
                print("JobPosting build succeeded.")
                _print_json("JobPosting.salary", job_posting.salary)
            except Exception as exc:
                print("JobPosting build failed.")
                print(exc)
        finally:
            await page.close()
            await context.close()
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Debug Prosple salary extraction and JobPosting validation for a specific URL."
    )
    parser.add_argument("url", help="Prosple job detail URL")
    args = parser.parse_args()
    asyncio.run(debug_url(args.url))


if __name__ == "__main__":
    main()

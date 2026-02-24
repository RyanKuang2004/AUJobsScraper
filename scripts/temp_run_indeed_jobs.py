"""Temporarily run IndeedScraper and print a small sample payload."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aujobsscraper.config import settings
from aujobsscraper.scrapers.indeed_scraper import IndeedScraper


async def run_jobs(search_term: Optional[str], results_wanted: int) -> None:
    if search_term:
        scraper = IndeedScraper(
            search_term=search_term,
            results_wanted=results_wanted,
            results_wanted_total=results_wanted,
        )
    else:
        scraper = IndeedScraper(
            search_terms=settings.search_keywords,
            results_wanted=results_wanted,
            results_wanted_total=results_wanted,
        )

    jobs = await scraper.scrape()
    print(f"Processed jobs: {len(jobs)}")

    if jobs:
        print(json.dumps(jobs[0].to_dict(), indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Temporarily run IndeedScraper")
    parser.add_argument("--search-term", default=None, help="Single Indeed search term")
    parser.add_argument("--results-wanted", type=int, default=5, help="Number of jobs to fetch")
    args = parser.parse_args()

    asyncio.run(run_jobs(search_term=args.search_term, results_wanted=args.results_wanted))


if __name__ == "__main__":
    main()

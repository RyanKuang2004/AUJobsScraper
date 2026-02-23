import argparse
import asyncio
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aujobsscraper.scrapers.indeedscraper import IndeedScraper


async def run_jobs(
    search_term: str = "software engineer",
    results_wanted: int = 5,
    output_path: str | None = None,
) -> None:
    scraper = IndeedScraper(
        search_term=search_term,
        google_search_term=search_term,
        results_wanted=results_wanted,
    )

    jobs = await scraper.scrape()
    job_dicts = [job.to_dict() for job in jobs]

    print(f"Processed jobs: {len(job_dicts)}")
    if job_dicts:
        print("Sample job:")
        print(json.dumps(job_dicts[0], indent=2, default=str))

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(job_dicts, indent=2, default=str), encoding="utf-8")
        print(f"Saved output to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Temporarily run IndeedScraper and print a sample JobPosting."
    )
    parser.add_argument(
        "--search-term",
        default="software engineer",
        help="Indeed search term (default: software engineer)",
    )
    parser.add_argument(
        "--results-wanted",
        type=int,
        default=5,
        help="Maximum number of results to request from Indeed (default: 5)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save all scraped jobs as JSON",
    )
    args = parser.parse_args()

    asyncio.run(
        run_jobs(
            search_term=args.search_term,
            results_wanted=args.results_wanted,
            output_path=args.output,
        )
    )


if __name__ == "__main__":
    main()

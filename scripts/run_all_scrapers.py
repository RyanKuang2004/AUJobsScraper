"""Run all four job scrapers and collect results."""
import argparse
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aujobsscraper.config import settings
from aujobsscraper.scrapers.seek_scraper import SeekScraper
from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper
from aujobsscraper.scrapers.prosple_scraper import ProspleScraper
from aujobsscraper.scrapers.indeed_scraper import IndeedScraper


async def run_scraper(scraper_name: str, skip_urls: Optional[set] = None) -> dict:
    """Run a single scraper and return results."""
    print(f"\n{'=' * 60}")
    print(f"Starting {scraper_name} scraper...")
    print(f"{'=' * 60}")

    if scraper_name == "seek":
        scraper = SeekScraper()
    elif scraper_name == "gradconnection":
        scraper = GradConnectionScraper()
    elif scraper_name == "prosple":
        scraper = ProspleScraper()
    elif scraper_name == "indeed":
        scraper = IndeedScraper()
    else:
        raise ValueError(f"Unknown scraper: {scraper_name}")

    results = []
    async for batch in scraper.scrape(skip_urls=skip_urls):
        results.extend(batch)
    print(f"\n{scraper_name.title()} scraper finished. Collected {len(results)} jobs.")

    return {
        "scraper": scraper_name,
        "count": len(results),
        "jobs": [job.to_dict() for job in results],
    }


async def run_all_scrapers(output_path: Optional[str] = None) -> None:
    """Run all four scrapers and combine results."""
    start_time = datetime.now()

    # Track all seen URLs to avoid duplicates across scrapers
    seen_urls = set()

    scrapers = ["prosple"]
    all_results = []

    for scraper_name in scrapers:
        try:
            result = await run_scraper(scraper_name, skip_urls=seen_urls)

            # Track URLs from this scraper
            for job in result["jobs"]:
                for url in job.get("source_urls", []):
                    seen_urls.add(url)

            all_results.append(result)
        except Exception as e:
            print(f"\n⚠️  Error running {scraper_name} scraper: {e}")
            all_results.append({
                "scraper": scraper_name,
                "count": 0,
                "jobs": [],
                "error": str(e),
            })

    # Combine all results
    combined_jobs = []
    for result in all_results:
        combined_jobs.extend(result["jobs"])

    # Print summary
    total_jobs = len(combined_jobs)
    duration = (datetime.now() - start_time).total_seconds()
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    for result in all_results:
        scraper_name = result["scraper"].title()
        count = result["count"]
        error = result.get("error", "")
        if error:
            print(f"{scraper_name}: ❌ {count} jobs ({error})")
        else:
            print(f"{scraper_name}: ✅ {count} jobs")
    print(f"\nTotal unique jobs: {total_jobs}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"{'=' * 60}")

    # Save results if output path provided
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "timestamp": datetime.now().isoformat(),
            "total_jobs": total_jobs,
            "duration_seconds": duration,
            "scraper_results": all_results,
        }

        path.write_text(json.dumps(output_data, indent=2, default=str), encoding="utf-8")
        print(f"\n✅ Results saved to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all four job scrapers (Seek, GradConnection, Prosple, Indeed)."
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Path to save combined results as JSON",
    )
    args = parser.parse_args()

    asyncio.run(run_all_scrapers(output_path=args.output))


if __name__ == "__main__":
    main()

"""Run each scraper in a lightweight first-iteration preview mode."""
import argparse
import asyncio
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aujobsscraper.config import settings
from aujobsscraper.scrapers.seek_scraper import SeekScraper
from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper
from aujobsscraper.scrapers.prosple_scraper import ProspleScraper
from aujobsscraper.scrapers.indeed_scraper import IndeedScraper

DEFAULT_SCRAPERS = ("seek", "gradconnection", "prosple", "indeed")
INDEED_PREVIEW_RESULTS = 5


@contextmanager
def _temporary_preview_settings():
    """Limit search terms/pages while this context is active."""
    original_search = list(settings.search_keywords)
    original_grad = list(settings.gradconnection_keywords)
    original_max_pages = settings.max_pages

    try:
        if settings.search_keywords:
            settings.search_keywords = [settings.search_keywords[0]]
        if settings.gradconnection_keywords:
            settings.gradconnection_keywords = [settings.gradconnection_keywords[0]]
        settings.max_pages = 1
        yield
    finally:
        settings.search_keywords = original_search
        settings.gradconnection_keywords = original_grad
        settings.max_pages = original_max_pages


def _limit_prosple_to_first_page(scraper: ProspleScraper) -> None:
    """Patch Prosple pagination so only the first listing page is fetched."""
    original_get_job_links = scraper._get_job_links
    first_page_seen = False

    async def _first_page_only(page, url):
        nonlocal first_page_seen
        if first_page_seen:
            return []
        first_page_seen = True
        return await original_get_job_links(page, url)

    scraper._get_job_links = _first_page_only


def _build_scraper(scraper_name: str):
    if scraper_name == "seek":
        return SeekScraper()
    if scraper_name == "gradconnection":
        return GradConnectionScraper()
    if scraper_name == "prosple":
        scraper = ProspleScraper()
        _limit_prosple_to_first_page(scraper)
        return scraper
    if scraper_name == "indeed":
        first_term = settings.search_keywords[0] if settings.search_keywords else None
        return IndeedScraper(
            search_terms=[first_term] if first_term else None,
            results_wanted=INDEED_PREVIEW_RESULTS,
            results_wanted_total=INDEED_PREVIEW_RESULTS,
        )
    raise ValueError(f"Unknown scraper: {scraper_name}")


async def run_scraper(scraper_name: str, skip_urls: Optional[set] = None) -> dict:
    print(f"\n{'=' * 60}")
    print(f"Starting {scraper_name} scraper (first-iteration preview)...")
    print(f"{'=' * 60}")

    with _temporary_preview_settings():
        scraper = _build_scraper(scraper_name)
        results = await scraper.scrape(skip_urls=skip_urls)

    print(f"\n{scraper_name.title()} scraper finished. Collected {len(results)} jobs.")
    return {
        "scraper": scraper_name,
        "count": len(results),
        "jobs": [job.to_dict() for job in results],
    }


async def run_all_scrapers(
    output_path: Optional[str] = None,
    scrapers: Iterable[str] = DEFAULT_SCRAPERS,
) -> None:
    start_time = datetime.now()
    seen_urls = set()
    all_results = []

    for scraper_name in scrapers:
        try:
            result = await run_scraper(scraper_name, skip_urls=seen_urls)
            for job in result["jobs"]:
                for url in job.get("source_urls", []):
                    seen_urls.add(url)
            all_results.append(result)
        except Exception as exc:
            print(f"\nError running {scraper_name} scraper: {exc}")
            all_results.append(
                {"scraper": scraper_name, "count": 0, "jobs": [], "error": str(exc)}
            )

    combined_jobs = []
    for result in all_results:
        combined_jobs.extend(result["jobs"])

    total_jobs = len(combined_jobs)
    duration = (datetime.now() - start_time).total_seconds()

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for result in all_results:
        scraper_name = result["scraper"].title()
        count = result["count"]
        error = result.get("error", "")
        if error:
            print(f"{scraper_name}: FAIL {count} jobs ({error})")
        else:
            print(f"{scraper_name}: OK {count} jobs")
    print(f"\nTotal unique jobs: {total_jobs}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"{'=' * 60}")

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
        print(f"\nResults saved to: {path}")


def _parse_scrapers(raw_scrapers: str) -> list[str]:
    values = [value.strip().lower() for value in raw_scrapers.split(",") if value.strip()]
    if not values:
        return list(DEFAULT_SCRAPERS)
    invalid = [value for value in values if value not in DEFAULT_SCRAPERS]
    if invalid:
        raise ValueError(
            f"Unsupported scraper(s): {', '.join(invalid)}. Valid options: {', '.join(DEFAULT_SCRAPERS)}"
        )
    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run all scrapers in first-iteration preview mode so output formatting can be inspected quickly."
        )
    )
    parser.add_argument("--output", "-o", default=None, help="Path to save combined results as JSON")
    parser.add_argument(
        "--scrapers",
        default=",".join(DEFAULT_SCRAPERS),
        help=f"Comma-separated scraper list. Options: {', '.join(DEFAULT_SCRAPERS)}",
    )
    args = parser.parse_args()

    selected_scrapers = _parse_scrapers(args.scrapers)
    asyncio.run(run_all_scrapers(output_path=args.output, scrapers=selected_scrapers))


if __name__ == "__main__":
    main()

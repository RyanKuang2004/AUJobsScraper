# aujobsscraper/scrapers/base_scraper.py
import logging
import asyncio
from typing import AsyncGenerator, List, Optional, Set
from aujobsscraper.config import settings
from aujobsscraper.models.job import JobPosting
from aujobsscraper.models.location import Location
from aujobsscraper.utils.scraper_utils import normalize_locations

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class BaseScraper:
    def __init__(self, platform_name: str):
        self.platform = platform_name
        self.logger = logging.getLogger(f"Scraper-{platform_name}")
        self._results: List[JobPosting] = []

    def _build_job_posting(
        self,
        job_title: str,
        company: str,
        raw_locations: List[str],
        source_url: str,
        description: str,
        **optional_fields
    ) -> JobPosting:
        """Build a JobPosting from extracted data. Handles location normalization."""
        normalized_locs = normalize_locations(raw_locations)
        location_objs = [Location(**loc) for loc in normalized_locs]
        return JobPosting(
            job_title=job_title,
            company=company,
            description=description,
            locations=location_objs,
            source_urls=[source_url],
            platforms=[self.platform],
            salary=optional_fields.get("salary"),
            posted_at=optional_fields.get("posted_at"),
            closing_date=optional_fields.get("closing_date"),
        )

    def _collect_job(self, job_posting: JobPosting) -> None:
        """Validate and add a job posting to the results list."""
        errors = job_posting.validate()
        if errors:
            self.logger.error(f"Validation errors for {job_posting.job_title}: {', '.join(errors)}")
            return
        self._results.append(job_posting)
        self.logger.info(f"Collected job: {job_posting.job_title} ({job_posting.company})")

    async def _setup_browser_context(self, playwright):
        """Create browser context with standard configuration."""
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        return browser, context

    async def process_jobs_concurrently(self, context, job_urls: List[str]) -> None:
        """Process multiple jobs concurrently using a semaphore."""
        semaphore = asyncio.Semaphore(settings.concurrency)
        self.logger.info(f"Processing {len(job_urls)} jobs with concurrency {settings.concurrency}")

        async def worker(url: str):
            async with semaphore:
                page = await context.new_page()
                try:
                    await self._process_job(page, url)
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {e}")
                finally:
                    await page.close()

        await asyncio.gather(*[worker(url) for url in job_urls])

    async def scrape(
        self, skip_urls: Optional[Set[str]] = None
    ) -> AsyncGenerator[List[JobPosting], None]:
        """
        Yield batches of JobPosting objects as they are collected.
        Each yield corresponds to one listing page worth of jobs.
        Subclasses must implement this as an async generator.
        """
        raise NotImplementedError("Subclasses must implement scrape()")
        yield  # makes this an async generator

    async def _run_async(self) -> None:
        """Consume the scrape generator, discarding results (used by run())."""
        async for _ in self.scrape():
            pass

    def run(self) -> None:
        asyncio.run(self._run_async())

    async def _process_job(self, page, url: str) -> None:
        """Process a single job posting page."""
        raise NotImplementedError("Subclasses must implement _process_job()")

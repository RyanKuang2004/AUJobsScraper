import logging
import asyncio
from jobly.config import settings
from typing import List, Dict, Any, Optional
from jobly.db import JobDatabase
from jobly.models import JobPosting, Location
from jobly.utils.scraper_utils import (
    extract_job_role,
    determine_seniority,
    normalize_locations,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class BaseScraper:
    def __init__(self, platform_name: str):
        self.platform = platform_name
        self.db = JobDatabase()
        self.logger = logging.getLogger(f"Scraper-{platform_name}")

    def _build_job_posting(
        self,
        job_title: str,
        company: str,
        raw_locations: List[str],
        source_url: str,
        description: str,
        **optional_fields
    ) -> JobPosting:
        """
        Build a JobPosting from extracted data.
        Handles common transformations like job_role extraction and location normalization.
        
        Args:
            job_title: Original job title (for fingerprinting)
            company: Company name
            raw_locations: List of location strings to normalize
            source_url: Job posting URL
            description: Job description text
            **optional_fields: salary, seniority, posted_at, closing_date
        
        Returns:
            Validated JobPosting object
        """
        # Extract job role from title
        job_role = extract_job_role(job_title)
        
        # Normalize locations
        normalized_locs = normalize_locations(raw_locations)
        location_objs = [Location(**loc) for loc in normalized_locs]
        
        # Determine seniority if not provided
        seniority = optional_fields.get("seniority")
        if not seniority:
            seniority = determine_seniority(job_title)
        
        return JobPosting(
            job_title=job_title,
            job_role=job_role,
            company=company,
            locations=location_objs,
            source_urls=[source_url],
            platforms=[self.platform],
            description=description,
            salary=optional_fields.get("salary"),
            seniority=seniority,
            posted_at=optional_fields.get("posted_at"),
            closing_date=optional_fields.get("closing_date"),
        )
    
    async def _setup_browser_context(self, playwright):
        """
        Create browser context with standard configuration.
        
        Args:
            playwright: Playwright instance from async_playwright()
        
        Returns:
            Tuple of (browser, context)
        """
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
        )
        return browser, context

    async def process_jobs_concurrently(self, context, job_urls: List[str]):
        """
        Process multiple jobs concurrently using a semaphore.
        
        Args:
            context: Playwright browser context
            job_urls: List of job URLs to process
        """
        concurrency_limit = settings.scraper.concurrency
        semaphore = asyncio.Semaphore( settings.scraper.concurrency)
        self.logger.info(f"Processing {len(job_urls)} jobs with concurrency limit of {concurrency_limit}")
        
        async def worker(url):
            async with semaphore:
                page = await context.new_page()
                try:
                    # Subclasses must implement _process_job
                    if hasattr(self, '_process_job'):
                        await self._process_job(page, url)
                    else:
                        self.logger.error(f"Scraper {self.platform} does not implement _process_job")
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {e}")
                finally:
                    await page.close()

        tasks = [worker(url) for url in job_urls]
        await asyncio.gather(*tasks)

    def save_job(self, job_data: Any) -> Optional[Dict[str, Any]]:
        """
        Saves a job to the database using the smart upsert logic.
        Supports both JobPosting objects and legacy dictionaries.
        
        Args:
            job_data: JobPosting object or dictionary
        
        Returns:
            Database result or None if save failed
        """
        # Convert JobPosting to dict if needed
        if isinstance(job_data, JobPosting):
            # Validate before saving
            errors = job_data.validate()
            if errors:
                self.logger.error(f"Validation errors: {', '.join(errors)}")
                return None
            data_dict = job_data.to_dict()
            title = job_data.job_role
            company = job_data.company
        else:
            # Legacy dictionary support
            data_dict = job_data
            title = job_data.get('job_role') or job_data.get('job_title') or job_data.get('title')
            company = job_data.get('company')
        
        try:
            # Ensure platform is set
            if "platforms" not in data_dict:
                data_dict["platforms"] = [self.platform]
            elif self.platform not in data_dict["platforms"]:
                data_dict["platforms"].append(self.platform)
                
            result = self.db.upsert_job(data_dict)
            self.logger.info(f"Saved job: {title} ({company})")
            return result
        except Exception as e:
            self.logger.error(f"Failed to save job: {e}")
            return None

    def run(self):
        """Main entry point for the scraper."""
        raise NotImplementedError("Subclasses must implement run()")

    def _process_job(self, page, url):
        """Process a single job posting."""
        raise NotImplementedError("Subclasses must implement _process_job()")
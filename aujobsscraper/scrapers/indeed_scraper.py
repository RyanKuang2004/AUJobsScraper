import asyncio
from datetime import date, datetime
from typing import Any, Optional, Set, List

from aujobsscraper.config import settings
from aujobsscraper.models.job import JobPosting
from aujobsscraper.models.location import Location
from aujobsscraper.scrapers.base_scraper import BaseScraper
from aujobsscraper.utils.salary_parser import SalaryParser
from aujobsscraper.utils.scraper_utils import normalize_locations


class IndeedScraper(BaseScraper):
    """Indeed scraper powered by JobSpy with output mapped to JobPosting."""

    def __init__(
        self,
        search_term: Optional[str] = None,
        search_terms: Optional[List[str]] = None,
        google_search_term: Optional[str] = None,
        location: Optional[str] = None,
        results_wanted: Optional[int] = None,
        results_wanted_total: Optional[int] = None,
        hours_old: Optional[int] = None,
        country_indeed: Optional[str] = None,
        term_concurrency: Optional[int] = None,
    ):
        super().__init__("indeed")
        self.search_term = (search_term or "").strip()
        self.search_terms = self._resolve_search_terms(search_terms, self.search_term)
        self.google_search_term = google_search_term
        self.location = settings.indeed_location if location is None else location
        self.results_wanted = (
            settings.indeed_results_wanted if results_wanted is None else results_wanted
        )
        self.results_wanted_total = (
            settings.indeed_results_wanted_total
            if results_wanted_total is None
            else results_wanted_total
        )
        self.hours_old = settings.indeed_hours_old if hours_old is None else hours_old
        self.country_indeed = (
            settings.indeed_country if country_indeed is None else country_indeed
        )
        resolved_term_concurrency = (
            settings.indeed_term_concurrency
            if term_concurrency is None
            else term_concurrency
        )
        self.term_concurrency = max(1, resolved_term_concurrency)

    async def scrape(self, skip_urls: Optional[Set[str]] = None) -> List[JobPosting]:
        self._results = []
        skip_urls = skip_urls or set()
        seen_urls: set[str] = set()

        semaphore = asyncio.Semaphore(self.term_concurrency)
        tasks = [
            asyncio.create_task(self._scrape_term_with_limit(term, semaphore))
            for term in self.search_terms
        ]
        term_results = await asyncio.gather(*tasks, return_exceptions=True)

        for term, rows in zip(self.search_terms, term_results):
            if isinstance(rows, Exception):
                self.logger.error(f"Indeed term '{term}' failed: {rows}")
                continue

            records = self._rows_to_records(rows)

            for job_post in records:
                posting = self.format_jobpost(job_post)
                if posting is None:
                    continue

                urls = [url for url in posting.source_urls if url]
                if any(url in skip_urls for url in urls):
                    continue

                if urls and any(url in seen_urls for url in urls):
                    continue

                if urls:
                    seen_urls.update(urls)

                self._collect_job(posting)

                if (
                    self.results_wanted_total is not None
                    and len(self._results) >= self.results_wanted_total
                ):
                    return self._results

        return self._results

    def format_jobpost(self, job_post: dict[str, Any]) -> Optional[JobPosting]:
        if not isinstance(job_post, dict):
            return None

        title = str(job_post.get("title") or "Unknown Title").strip()
        company = str(job_post.get("company") or "Unknown Company").strip()
        description = str(job_post.get("description") or "").strip()

        source_url = (
            str(job_post.get("job_url") or "").strip()
            or str(job_post.get("company_url") or "").strip()
        )

        locations = self._extract_locations(job_post.get("location"))
        salary = self._extract_salary(job_post)
        posted_at = self._normalize_posted_date(job_post.get("date_posted"))

        return JobPosting(
            job_title=title,
            company=company,
            description=description,
            locations=locations,
            source_urls=[source_url] if source_url else [],
            platforms=[self.platform],
            salary=salary,
            posted_at=posted_at,
        )

    async def _scrape_term_with_limit(self, term: str, semaphore: asyncio.Semaphore):
        async with semaphore:
            return await asyncio.to_thread(self._scrape_jobs_for_term, term)

    def _resolve_search_terms(
        self, search_terms: Optional[List[str]], search_term: str
    ) -> List[str]:
        if search_terms:
            cleaned = [term.strip() for term in search_terms if isinstance(term, str) and term.strip()]
            if cleaned:
                return cleaned

        if search_term:
            return [search_term]

        return [term for term in settings.search_keywords if isinstance(term, str) and term.strip()]

    def _scrape_jobs(self):
        return self._scrape_jobs_for_term(self.search_terms[0])

    def _scrape_jobs_for_term(self, term: str):
        try:
            from jobspy import scrape_jobs
        except ImportError as exc:
            raise ImportError(
                "jobspy is required for IndeedScraper. Install it with `pip install python-jobspy`."
            ) from exc

        return scrape_jobs(
            site_name=["indeed"],
            search_term=term,
            google_search_term=self.google_search_term or term,
            location=self.location,
            results_wanted=self.results_wanted,
            hours_old=self.hours_old,
            country_indeed=self.country_indeed,
        )

    def _rows_to_records(self, rows: Any) -> list[dict[str, Any]]:
        if rows is None:
            return []

        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]

        to_dict = getattr(rows, "to_dict", None)
        if callable(to_dict):
            try:
                records = to_dict(orient="records")
                return [row for row in records if isinstance(row, dict)]
            except TypeError:
                return []

        return []

    def _extract_locations(self, raw_location: Any) -> list[Location]:
        location_strings = []

        if isinstance(raw_location, dict):
            city = str(raw_location.get("city") or "").strip()
            state = str(raw_location.get("state") or "").strip()
            country = str(raw_location.get("country") or "").strip()

            if city and state:
                location_strings.append(f"{city}, {state}")
            elif city:
                location_strings.append(city)
            elif country:
                location_strings.append(country)
        elif isinstance(raw_location, str) and raw_location.strip():
            location_strings.append(raw_location.strip())

        if not location_strings:
            location_strings.append("Australia")

        normalized = normalize_locations(location_strings)
        if not normalized:
            return [Location(city="Australia", state="")]

        return [Location(**loc) for loc in normalized]

    def _extract_salary(self, job_post: dict[str, Any]) -> Optional[dict[str, float]]:
        min_amount = self._to_float(job_post.get("min_amount"))
        max_amount = self._to_float(job_post.get("max_amount"))

        # If jobspy has salary data, use it
        if min_amount is not None or max_amount is not None:
            low = min_amount if min_amount is not None else max_amount
            high = max_amount if max_amount is not None else min_amount
            if low is None or high is None:
                return None

            multiplier = self._interval_multiplier(job_post.get("interval"))
            annual_min = float(low) * multiplier
            annual_max = float(high) * multiplier

            return {
                "annual_min": min(annual_min, annual_max),
                "annual_max": max(annual_min, annual_max),
            }

        # Fallback: try parsing from description
        description = job_post.get("description")
        if description:
            return SalaryParser.extract_salary(description)

        return None

    def _interval_multiplier(self, interval: Any) -> int:
        interval_text = str(interval or "yearly").strip().lower()
        if interval_text == "hourly":
            return 2080
        if interval_text == "daily":
            return 260
        if interval_text == "weekly":
            return 52
        if interval_text == "monthly":
            return 12
        return 1

    def _normalize_posted_date(self, raw_value: Any) -> Optional[str]:
        if raw_value is None:
            return None

        if isinstance(raw_value, datetime):
            return raw_value.date().isoformat()
        if isinstance(raw_value, date):
            return raw_value.isoformat()

        if isinstance(raw_value, str):
            text = raw_value.strip()
            if not text:
                return None
            if len(text) >= 10:
                candidate = text[:10]
                try:
                    return date.fromisoformat(candidate).isoformat()
                except ValueError:
                    return None
        return None

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if not cleaned:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def run(self):
        import asyncio
        return asyncio.run(self.scrape())

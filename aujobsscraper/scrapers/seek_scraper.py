# aujobsscraper/scrapers/seek_scraper.py
import asyncio
import random
from typing import Optional, Set, List
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from aujobsscraper.scrapers.base_scraper import BaseScraper
from aujobsscraper.config import settings
from aujobsscraper.utils.scraper_utils import (
    remove_html_tags,
    calculate_posted_date,
    normalize_locations,
    normalize_salary
)
from aujobsscraper.models.job import JobPosting


class SeekScraper(BaseScraper):
    def __init__(self):
        super().__init__("seek")
        self.base_url = "https://www.seek.com.au"

    async def scrape(self, skip_urls: Optional[Set[str]] = None) -> List[JobPosting]:
        self._results = []
        skip_urls = skip_urls or set()
        self.logger.info("Starting Seek Scraper...")

        initial_run = settings.initial_run
        terms = settings.search_keywords
        limit = settings.max_pages
        days_ago = settings.initial_days_from_posted if initial_run else settings.days_from_posted

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                for term in terms:
                    self.logger.info(f"Searching for: {term}")
                    encoded_term = term.replace(" ", "-")

                    for page_num in range(1, limit + 1):
                        url = f"{self.base_url}/{encoded_term}-jobs?page={page_num}&daterange={days_ago}"
                        self.logger.info(f"Visiting List Page: {url}")

                        try:
                            job_links = await self._get_job_links(page, url)
                            if not job_links:
                                self.logger.info("No more results found.")
                                break

                            new_links = [link for link in job_links if link not in skip_urls]
                            skipped = len(job_links) - len(new_links)
                            if skipped > 0:
                                self.logger.info(f"Skipping {skipped} already-known URLs.")

                            self.logger.info(f"Found {len(new_links)} new jobs on page {page_num}")
                            await self.process_jobs_concurrently(context, new_links)

                        except Exception as e:
                            self.logger.error(f"Error processing page {page_num}: {e}")
            finally:
                await browser.close()

        self.logger.info(f"Seek Scraper finished. Collected {len(self._results)} jobs.")
        return self._results

    async def _get_job_links(self, page, url: str) -> list:
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 4))
            content = await page.content()
            if "No matching search results" in content:
                return []
            soup = BeautifulSoup(content, 'lxml')
            job_links = []
            for elem in soup.find_all("a", attrs={"data-automation": "jobTitle"}):
                link = elem['href']
                if not link.startswith("http"):
                    link = self.base_url + link.split("?")[0]
                job_links.append(link)
            return job_links
        except Exception as e:
            self.logger.error(f"Error getting job links from {url}: {e}")
            return []

    async def _process_job(self, page, job_url: str) -> None:
        try:
            self.logger.info(f"Scraping Job: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 3))
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            job_posting = self._build_job_posting(
                job_title=self._extract_title(soup),
                company=self._extract_company(soup),
                raw_locations=[self._extract_location(soup)],
                source_url=job_url,
                description=self._extract_description(soup),
                salary=normalize_salary(self._extract_salary(soup)),
                posted_at=self._extract_posted_date(soup),
            )
            self._collect_job(job_posting)

        except Exception as e:
            self.logger.error(f"Error scraping job {job_url}: {e}")

    def _extract_title(self, soup) -> str:
        elem = soup.find("h1", attrs={"data-automation": "job-detail-title"})
        return elem.text.strip() if elem else "Unknown Title"

    def _extract_company(self, soup) -> str:
        elem = soup.find("span", attrs={"data-automation": "advertiser-name"})
        return elem.text.strip() if elem else "Unknown Company"

    def _extract_location(self, soup) -> str:
        elem = soup.find("span", attrs={"data-automation": "job-detail-location"})
        return elem.text.strip() if elem else "Australia"

    def _extract_salary(self, soup):
        elem = soup.find("span", attrs={"data-automation": "job-detail-salary"})
        return elem.text.strip() if elem else None

    def _extract_description(self, soup) -> str:
        elem = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        raw = str(elem) if elem else str(soup.find("body"))
        return remove_html_tags(raw)

    def _extract_posted_date(self, soup):
        meta_elements = soup.find_all(
            "span",
            class_="_1ybl4650 _6wfnkx4x losivq0 losivq1 losivq1u losivq6 _1rtxcgx4"
        )
        for elem in meta_elements:
            if "Posted" in elem.text:
                return calculate_posted_date(elem.text.strip())
        return None

    def run(self):
        import asyncio
        return asyncio.run(self.scrape())

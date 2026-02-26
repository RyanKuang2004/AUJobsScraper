import asyncio
import random
import json
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from aujobsscraper.scrapers.base_scraper import BaseScraper
from aujobsscraper.config import settings
from aujobsscraper.utils.scraper_utils import (
    remove_html_tags,
    extract_salary_from_text,
    normalize_salary,
    normalize_locations,
)

class ProspleScraper(BaseScraper):
    def __init__(self):
        super().__init__("prosple")
        self.base_url = "https://au.prosple.com"
        self.search_url_base = "https://au.prosple.com/search-jobs?locations=9692&defaults_applied=1"

    async def scrape(self, skip_urls=None) -> list:
        self.logger.info("Starting Prosple Scraper...")
        self._results = []
        skip_urls = skip_urls or set()
        seen_urls = set(skip_urls)

        items_per_page = settings.prosple_items_per_page
        max_pages = settings.max_pages if settings.initial_run else settings.prosple_regular_max_pages
        keywords = settings.search_keywords or []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = await context.new_page()

                    for raw_keyword in keywords:
                        encoded_keyword = "+".join(raw_keyword.split())
                        if not encoded_keyword:
                            continue

                        start = 0
                        page_count = 0
                        sort_suffix = "&sort=newest_opportunities%7Cdesc" if not settings.initial_run else ""

                        while page_count < max_pages:
                            url = f"{self.search_url_base}&keywords={encoded_keyword}&start={start}{sort_suffix}"
                            self.logger.info(f"Visiting List Page: {url}")

                            try:
                                job_links_data = await self._get_job_links(page, url)
                                if not job_links_data:
                                    self.logger.info(f"No more results found for keyword '{raw_keyword}'.")
                                    break

                                new_jobs_data = [d for d in job_links_data if d['url'] not in seen_urls]

                                skipped_count = len(job_links_data) - len(new_jobs_data)
                                if skipped_count > 0:
                                    self.logger.info(f"Skipping {skipped_count} existing jobs.")

                                self.logger.info(
                                    f"Found {len(new_jobs_data)} NEW jobs for keyword '{raw_keyword}' on page start={start}"
                                )

                                new_links = [d['url'] for d in new_jobs_data]
                                seen_urls.update(new_links)
                                await self.process_jobs_concurrently(context, new_links)

                                page_count += 1
                                start += items_per_page

                            except Exception as e:
                                self.logger.error(
                                    f"Error processing keyword '{raw_keyword}' page start={start}: {e}"
                                )
                                break
                finally:
                    await browser.close()

            return self._results
        except Exception as e:
            self.logger.error(f"Unhandled error in scrape(): {e}")
            return self._results
        finally:
            self.logger.info("Prosple Scraper Finished.")

    async def _get_job_links(self, page: Page, url: str) -> List[Dict[str, Any]]:
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 4))

            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            job_cards = soup.find_all(
                "a",
                target="_blank",
                href=lambda href: href and href.startswith("/graduate-employers/"),
            )

            if not job_cards:
                if "No matching search results" in content:
                    return []
                return []

            jobs_data = []
            for link_elem in job_cards:
                link = link_elem['href']
                if not link.startswith("http"):
                    base = self.base_url.rstrip('/')
                    path = link.lstrip('/')
                    link = f"{base}/{path}"

                jobs_data.append({"url": link})

            return jobs_data
        except Exception as e:
            self.logger.error(f"Error getting job links from {url}: {e}")
            return []

    async def _process_job(self, page: Page, job_data: Dict[str, Any]):
        job_url = job_data['url'] if isinstance(job_data, dict) else job_data

        try:
            self.logger.info(f"Scraping Job: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 3))

            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            json_data = self._extract_json_ld(soup)

            title = self._extract_title(soup, json_data)
            company = self._extract_company(soup, json_data)

            # NEW JOB: Extract all fields
            extracted = {
                "title": title,
                "company": company,
                "locations": self._extract_locations(soup, json_data),
                "description": self._extract_description(soup, json_data),
                "salary": self._extract_salary(soup, json_data),
                "posted_at": self._extract_posted_date(json_data),
                "closing_date": self._extract_closing_date(json_data),
            }

            job_posting = self._build_job_posting(
                job_title=extracted["title"],
                company=extracted["company"],
                raw_locations=extracted["locations"],
                source_url=job_url,
                description=extracted["description"],
                salary=extracted.get("salary"),
                posted_at=extracted.get("posted_at"),
                closing_date=extracted.get("closing_date"),
            )

            self._collect_job(job_posting)

        except Exception as e:
            self.logger.error(f"Error scraping job {job_url}: {e}")


    def _extract_json_ld(self, soup) -> Optional[Dict]:
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    return data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            return item
            except (json.JSONDecodeError, AttributeError):
                continue
        return None

    def _extract_title(self, soup, json_data: Optional[Dict]) -> str:
        if json_data:
            title = json_data.get('title')
            if title:
                return title
        h1_elem = soup.find("h1")
        if h1_elem:
            return h1_elem.text.strip()
        return "Unknown Title"

    def _extract_company(self, soup, json_data: Optional[Dict]) -> str:
        if json_data:
            hiring_org = json_data.get('hiringOrganization')
            if isinstance(hiring_org, dict):
                company = hiring_org.get('name')
                if company:
                    return company
            elif isinstance(hiring_org, str):
                return hiring_org
        return "Unknown Company"

    def _extract_locations(self, soup, json_data: Optional[Dict]) -> list:
        if json_data:
            job_loc = json_data.get('jobLocation')
            if isinstance(job_loc, list):
                locations = []
                for loc in job_loc:
                    if isinstance(loc, dict):
                        address = loc.get('address')
                        if isinstance(address, dict):
                            city = address.get('addressLocality')
                            if city:
                                locations.append(city)
                        elif isinstance(address, str):
                            locations.append(address)
                if locations:
                    return locations
        return ["Australia"]

    def _extract_salary(self, soup, json_data: Optional[Dict]) -> Optional[Dict[str, float]]:
        if json_data:
            base_salary = json_data.get('baseSalary')
            if base_salary:
                if isinstance(base_salary, dict):
                    value = base_salary.get('value')
                    if isinstance(value, dict):
                        min_value = value.get('minValue')
                        max_value = value.get('maxValue')
                        if min_value is not None or max_value is not None:
                            def _safe_float(v) -> Optional[float]:
                                if v is None:
                                    return None
                                try:
                                    return float(str(v).replace(",", "").strip())
                                except (ValueError, TypeError):
                                    return None

                            low = _safe_float(min_value)
                            high = _safe_float(max_value)
                            if low is not None and high is not None:
                                return {"annual_min": min(low, high), "annual_max": max(low, high)}
                            if low is not None:
                                return {"annual_min": low, "annual_max": low}
                            if high is not None:
                                return {"annual_min": high, "annual_max": high}
                    if isinstance(value, (int, float)):
                        amount = float(value)
                        return {"annual_min": amount, "annual_max": amount}
                    if isinstance(value, str):
                        normalized = normalize_salary(value)
                        if normalized:
                            return normalized
                elif isinstance(base_salary, str):
                    normalized = normalize_salary(base_salary)
                    if normalized:
                        return normalized
        description = self._extract_description(soup, json_data)
        if description:
            raw_salary = extract_salary_from_text(description)
            if raw_salary:
                normalized = normalize_salary(raw_salary)
                if normalized:
                    return normalized
        return None

    def _extract_description(self, soup, json_data: Optional[Dict]) -> str:
        if json_data:
            description_html = json_data.get('description', "")
            if description_html:
                return remove_html_tags(description_html)
        return remove_html_tags(str(soup.body)) if soup.body else ""

    def _extract_posted_date(self, json_data: Optional[Dict]) -> Optional[str]:
        if json_data:
            posted_at = json_data.get('datePosted')
            if posted_at:
                return posted_at
        return None

    def _extract_closing_date(self, json_data: Optional[Dict]) -> Optional[str]:
        if json_data:
            closing_date = json_data.get('validThrough')
            if closing_date:
                return closing_date
        return None

    def run(self):
        asyncio.run(self.scrape())


if __name__ == "__main__":
    scraper = ProspleScraper()
    scraper.run()

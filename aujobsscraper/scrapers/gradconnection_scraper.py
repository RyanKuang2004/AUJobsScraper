import asyncio
import random
import re
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from datetime import datetime
from aujobsscraper.scrapers.base_scraper import BaseScraper
from aujobsscraper.config import settings
from aujobsscraper.utils.scraper_utils import (
    remove_html_tags,
    extract_salary_from_text,
    normalize_salary,
    normalize_locations,
)


class GradConnectionScraper(BaseScraper):
    def __init__(self):
        super().__init__("gradconnection")
        self.base_url = "https://au.gradconnection.com"

    async def scrape(self, skip_urls=None) -> list:
        self.logger.info("Starting GradConnection Scraper...")
        self._results = []
        skip_urls = skip_urls or set()

        terms = settings.gradconnection_keywords
        limit = settings.max_pages

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                for term in terms:
                    self.logger.info(f"Searching for: {term}")
                    encoded_term = term.replace(" ", "+")

                    for page_num in range(1, limit + 1):
                        url = f"{self.base_url}/jobs/australia/?title={encoded_term}&page={page_num}"
                        self.logger.info(f"Visiting List Page: {url}")

                        try:
                            job_links = await self._get_job_links(page, url)

                            if job_links is None:
                                self.logger.info("Hit 'notify-me' link, stopping pagination.")
                                break

                            if not job_links:
                                self.logger.info("No more results found or error fetching links.")
                                break

                            new_links = [link for link in job_links if link not in skip_urls]

                            skipped_count = len(job_links) - len(new_links)
                            if skipped_count > 0:
                                self.logger.info(f"Skipping {skipped_count} existing jobs.")

                            self.logger.info(f"Found {len(new_links)} NEW jobs on page {page_num}")

                            await self.process_jobs_concurrently(context, new_links)

                        except Exception as e:
                            self.logger.error(f"Error processing page {page_num}: {e}")
                            break
            finally:
                await browser.close()

        self.logger.info("GradConnection Scraper Finished.")
        return self._results

    async def _get_job_links(self, page: Page, url: str) -> List[str] | None:
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 4))
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            job_links = []
            title_elements = soup.find_all("a", class_="box-header-title")
            if not title_elements:
                return []
            for elem in title_elements:
                href = elem.get('href')
                if not href:
                    continue
                if "notifyme" in href or "notify-me" in href:
                    self.logger.info(f"Found notify-me link: {href}")
                    return None
                if not href.startswith("http"):
                    base = self.base_url.rstrip('/')
                    path = href if href.startswith('/') else '/' + href
                    href = f"{base}{path}"
                job_links.append(href)
            return job_links
        except Exception as e:
            self.logger.error(f"Error getting job links from {url}: {e}")
            return []

    async def _process_job(self, page: Page, job_url: str | Dict[str, Any]):
        if isinstance(job_url, dict):
            job_url = job_url.get("url", "")

        try:
            self.logger.info(f"Scraping Job: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector("h1.employers-profile-h1", timeout=10000)
                await asyncio.sleep(2)
            except Exception:
                self.logger.warning(f"Timeout waiting for h1 on {job_url}")
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            if self._is_event_posting(soup):
                self.logger.info(f"Skipping event posting: {job_url}")
                return None

            title = self._extract_title(soup)
            company = self._extract_company(soup)

            # Extract all fields for new job
            json_data = await self._extract_json_data(page)
            extracted = {
                "title": title,
                "company": company,
                "locations": self._extract_locations(soup, json_data),
                "description": self._extract_description(soup),
                "salary": self._extract_salary(soup, json_data),
                "posted_at": self._extract_posted_date(soup),
                "closing_date": self._extract_closing_date(soup, json_data),
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

    def _is_event_posting(self, soup) -> bool:
        event_button = soup.find("button", string=lambda s: s and "sign up to event" in s.lower())
        if event_button:
            return True
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and "job type" in strong.text.strip().lower():
                    value = li.text.replace(strong.text, "").strip()
                    if "event" in value.lower():
                        return True
        overview = soup.select_one("div.job-overview-container")
        if overview:
            dt = overview.find("dt", string=lambda text: text and "Job Type" in text)
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd and "event" in dd.text.strip().lower():
                    return True
        return False

    async def _extract_json_data(self, page: Page) -> Optional[Dict]:
        try:
            json_data = await page.evaluate("() => window.__initialState__")
            if json_data:
                self.logger.info("Successfully extracted window.__initialState__")
                return json_data
        except Exception as e:
            self.logger.warning(f"Failed to extract JSON data: {e}")
        return None

    def _extract_title(self, soup) -> str:
        elem = soup.select_one("h1.employers-profile-h1")
        return elem.text.strip() if elem else "Unknown Title"

    def _extract_company(self, soup) -> str:
        elem = soup.select_one("h1.employers-panel-title")
        return elem.text.strip() if elem else "Unknown Company"

    def _extract_locations(self, soup, json_data: Optional[Dict]) -> list:
        if json_data:
            campaign = json_data.get("campaignstore", {}).get("campaign", {})
            locations_list = campaign.get("locations", [])
            if locations_list:
                return locations_list
        overview = soup.select_one("div.job-overview-container")
        if overview:
            dt = overview.find("dt", string=lambda text: text and "Location" in text)
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    return [dd.text.strip()]
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and "location" in strong.text.strip().lower():
                    value = li.text.replace(strong.text, "").strip()
                    if "...show more" in value:
                        value = value.replace("...show more", "").strip()
                    return [loc.strip() for loc in value.split(",")]
        return ["Australia"]

    def _extract_salary(self, soup, json_data: Optional[Dict]) -> Optional[Dict[str, float]]:
        if json_data:
            campaign = json_data.get("campaignstore", {}).get("campaign", {})
            salary = campaign.get("salary")
            if salary:
                if isinstance(salary, dict):
                    min_salary = salary.get("min_salary")
                    max_salary = salary.get("max_salary")

                    if min_salary is not None or max_salary is not None:
                        def _safe_float(v) -> Optional[float]:
                            if v is None:
                                return None
                            try:
                                return float(str(v).replace(",", "").strip())
                            except (ValueError, TypeError):
                                return None

                        low = _safe_float(min_salary)
                        high = _safe_float(max_salary)
                        if low is not None and high is not None:
                            return {"annual_min": min(low, high), "annual_max": max(low, high)}
                        if low is not None:
                            return {"annual_min": low, "annual_max": low}
                        if high is not None:
                            return {"annual_min": high, "annual_max": high}

                    details = salary.get("details")
                    if isinstance(details, str) and details.strip():
                        normalized = normalize_salary(details)
                        if normalized:
                            return normalized

                if isinstance(salary, str):
                    normalized = normalize_salary(salary)
                    if normalized:
                        return normalized
        if soup is None:
            return None
        overview = soup.select_one("div.job-overview-container")
        if overview:
            dt = overview.find("dt", string=lambda text: text and "Salary" in text)
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    normalized = normalize_salary(dd.text.strip())
                    if normalized:
                        return normalized
        description = self._extract_description(soup)
        if description:
            raw_salary = extract_salary_from_text(description)
            if raw_salary:
                normalized = normalize_salary(raw_salary)
                if normalized:
                    return normalized
        return None

    def _extract_description(self, soup) -> str:
        desc_elem = soup.select_one("div.campaign-content-container")
        if desc_elem:
            return remove_html_tags(str(desc_elem))
        desc_elem = soup.select_one("div.job-description-container")
        if desc_elem:
            return remove_html_tags(str(desc_elem))
        return remove_html_tags(str(soup.body))

    def _extract_posted_date(self, soup) -> Optional[str]:
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and "posted" in strong.text.strip().lower():
                    value = li.text.replace(strong.text, "").strip()
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
                    except:
                        return None
        return None

    def _extract_closing_date(self, soup, json_data: Optional[Dict]) -> Optional[str]:
        if json_data:
            campaign = json_data.get("campaignstore", {}).get("campaign", {})
            closing_date = campaign.get("closing_date")
            if closing_date:
                try:
                    return datetime.fromisoformat(closing_date.replace("Z", "+00:00")).date().isoformat()
                except:
                    pass
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and ("deadline" in strong.text.strip().lower() or "closing" in strong.text.strip().lower()):
                    value = li.text.replace(strong.text, "").strip()
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
                    except:
                        try:
                            cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", value)
                            dt = datetime.strptime(cleaned, "%d %b %Y, %I:%M %p")
                            return dt.date().isoformat()
                        except:
                            return None
        return None

    def run(self):
        asyncio.run(self.scrape())


if __name__ == "__main__":
    scraper = GradConnectionScraper()
    scraper.run()

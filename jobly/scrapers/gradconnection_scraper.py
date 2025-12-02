import os
import asyncio
import random
import json
import re
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from datetime import datetime
from jobly.scrapers.base_scraper import BaseScraper
from jobly.config import settings
from jobly.utils.scraper_utils import (
    remove_html_tags,
    extract_salary_from_text,
    determine_seniority,
    normalize_locations,
    extract_job_role,
)


class GradConnectionScraper(BaseScraper):
    def __init__(self):
        super().__init__("gradconnection")
        self.base_url = "https://au.gradconnection.com"

    async def scrape(self, initial_run: bool = False):
        self.logger.info("Starting GradConnection Scraper...")
        
        terms = settings.scraper.gradconnection_keywords
        limit = settings.scraper.max_pages
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
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
                        
                        # Check if None (hit notify-me) or empty
                        if job_links is None:
                            self.logger.info("Hit 'notify-me' link, stopping pagination.")
                            break
                        
                        if not job_links:
                            self.logger.info("No more results found or error fetching links.")
                            break
                        
                        # Deduplication: Check which URLs already exist
                        existing_urls = self.db.check_existing_urls(job_links, only_complete=initial_run)
                        new_links = [link for link in job_links if link not in existing_urls]
                        
                        skipped_count = len(job_links) - len(new_links)
                        if skipped_count > 0:
                            self.logger.info(f"Skipping {skipped_count} existing jobs.")
                        
                        self.logger.info(f"Found {len(new_links)} NEW jobs on page {page_num}")
                        
                        await self.process_jobs_concurrently(context, new_links)
                                
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num}: {e}")
                        break

            await browser.close()
            self.logger.info("GradConnection Scraper Finished.")

    async def _get_job_links(self, page: Page, url: str) -> List[str] | None:
        """
        Navigates to the list page and extracts job links.
        Returns None if we hit a 'notify-me' link (stopping condition).
        Returns empty list [] if no jobs found or other errors.
        """
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 4))
            
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            job_links = []
            
            # Find all <a> tags with class "box-header-title"
            title_elements = soup.find_all("a", class_="box-header-title")
            
            if not title_elements:
                # No jobs found on this page
                return []
            
            for elem in title_elements:
                href = elem.get('href')
                if not href:
                    continue
                
                # Check for notify-me link (stopping condition)
                if "notifyme" in href or "notify-me" in href:
                    self.logger.info(f"Found notify-me link: {href}")
                    return None  # Signal to stop
                
                # Construct full URL
                if not href.startswith("http"):
                    base = self.base_url.rstrip('/')
                    path = href if href.startswith('/') else '/' + href
                    href = f"{base}{path}"
                
                job_links.append(href)
            
            return job_links
            
        except Exception as e:
            self.logger.error(f"Error getting job links from {url}: {e}")
            return []

    async def _process_job(self, page: Page, job_url: str):
        """
        Navigates to a job URL, extracts details, and saves the job.
        """
        try:
            self.logger.info(f"Scraping Job: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            
            # Wait for content to load
            try:
                await page.wait_for_selector("h1.employers-profile-h1", timeout=10000)
                await asyncio.sleep(2)
            except Exception:
                self.logger.warning(f"Timeout waiting for h1 on {job_url}")

            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            # Check if this is an event posting and skip if so
            if self._is_event_posting(soup):
                self.logger.info(f"Skipping event posting: {job_url}")
                return None
            
            # Try to extract JSON data
            json_data = await self._extract_json_data(page)
            
            # Extract all fields
            extracted = {
                "title": self._extract_title(soup),
                "company": self._extract_company(soup),
                "locations": self._extract_locations(soup, json_data),
                "description": self._extract_description(soup),
                "salary": self._extract_salary(soup, json_data),
                "posted_at": self._extract_posted_date(soup),
                "closing_date": self._extract_closing_date(soup, json_data),
            }
            
            # Build JobPosting using base class helper
            job_posting = self._build_job_posting(
                job_title=extracted["title"],
                company=extracted["company"],
                raw_locations=extracted["locations"],
                source_url=job_url,
                description=extracted["description"],
                salary=extracted.get("salary"),
                seniority="Junior",  # Hardcoded for graduate/internship platform
                posted_at=extracted.get("posted_at"),
                closing_date=extracted.get("closing_date"),
            )
            
            # Save to database
            self.save_job(job_posting)
            
        except Exception as e:
            self.logger.error(f"Error scraping job {job_url}: {e}")
    
    def _is_event_posting(self, soup) -> bool:
        """Check if this is an event posting that should be skipped"""
        # Check for "Sign up to event" button
        event_button = soup.find("button", string=lambda s: s and "sign up to event" in s.lower())
        if event_button:
            return True
        
        # Check Job Type field in ul.box-content
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and "job type" in strong.text.strip().lower():
                    value = li.text.replace(strong.text, "").strip()
                    if "event" in value.lower():
                        return True
        
        # Check Job Type in overview container
        overview = soup.select_one("div.job-overview-container")
        if overview:
            dt = overview.find("dt", string=lambda text: text and "Job Type" in text)
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd and "event" in dd.text.strip().lower():
                    return True
        
        return False
    
    async def _extract_json_data(self, page: Page) -> Optional[Dict]:
        """Extract window.__initialState__ JSON data via JavaScript"""
        try:
            json_data = await page.evaluate("() => window.__initialState__")
            if json_data:
                self.logger.info("Successfully extracted window.__initialState__")
                return json_data
        except Exception as e:
            self.logger.warning(f"Failed to extract JSON data: {e}")
        return None
    
    def _extract_title(self, soup) -> str:
        """Extract job title from page"""
        elem = soup.select_one("h1.employers-profile-h1")
        return elem.text.strip() if elem else "Unknown Title"
    
    def _extract_company(self, soup) -> str:
        """Extract company name from page"""
        elem = soup.select_one("h1.employers-panel-title")
        return elem.text.strip() if elem else "Unknown Company"
    
    def _extract_locations(self, soup, json_data: Optional[Dict]) -> list:
        """Extract locations from JSON or HTML"""
        # Try JSON first
        if json_data:
            campaign = json_data.get("campaignstore", {}).get("campaign", {})
            locations_list = campaign.get("locations", [])
            if locations_list:
                self.logger.info(f"Extracted {len(locations_list)} locations from JSON")
                return locations_list
        
        # Fallback to HTML extraction
        overview = soup.select_one("div.job-overview-container")
        if overview:
            dt = overview.find("dt", string=lambda text: text and "Location" in text)
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    return [dd.text.strip()]
        
        # Try box-content structure
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and "location" in strong.text.strip().lower():
                    value = li.text.replace(strong.text, "").strip()
                    # Handle "show more" suffix
                    if "...show more" in value:
                        value = value.replace("...show more", "").strip()
                    return [loc.strip() for loc in value.split(",")]
        
        return ["Australia"]  # Default fallback
    
    def _extract_salary(self, soup, json_data: Optional[Dict]) -> Optional[str]:
        """Extract salary from JSON or HTML"""
        # Try JSON first
        if json_data:
            campaign = json_data.get("campaignstore", {}).get("campaign", {})
            salary = campaign.get("salary")
            if salary:
                return salary
        
        # Fallback to HTML
        overview = soup.select_one("div.job-overview-container")
        if overview:
            dt = overview.find("dt", string=lambda text: text and "Salary" in text)
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    return dd.text.strip()
        
        return None
    
    def _extract_description(self, soup) -> str:
        """Extract job description from page"""
        # Try campaign content container first
        desc_elem = soup.select_one("div.campaign-content-container")
        if desc_elem:
            return remove_html_tags(str(desc_elem))
        
        # Fallback to job description container
        desc_elem = soup.select_one("div.job-description-container")
        if desc_elem:
            return remove_html_tags(str(desc_elem))
        
        # Last resort: full body
        return remove_html_tags(str(soup.body))
    
    def _extract_posted_date(self, soup) -> Optional[str]:
        """Extract posted date from page"""
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and "posted" in strong.text.strip().lower():
                    value = li.text.replace(strong.text, "").strip()
                    try:
                        # Try parsing ISO format date
                        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
                    except:
                        return None
        return None
    
    def _extract_closing_date(self, soup, json_data: Optional[Dict]) -> Optional[str]:
        """Extract closing/application deadline from JSON or HTML"""
        # Try JSON first
        if json_data:
            campaign = json_data.get("campaignstore", {}).get("campaign", {})
            closing_date = campaign.get("closing_date")
            if closing_date:
                try:
                    return datetime.fromisoformat(closing_date.replace("Z", "+00:00")).date().isoformat()
                except:
                    pass
        
        # Fallback to HTML
        box_content = soup.select_one("ul.box-content")
        if box_content:
            for li in box_content.find_all("li"):
                strong = li.find("strong")
                if strong and ("deadline" in strong.text.strip().lower() or "closing" in strong.text.strip().lower()):
                    value = li.text.replace(strong.text, "").strip()
                    try:
                        # Try parsing ISO format date
                        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
                    except:
                        # Try parsing formatted date
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

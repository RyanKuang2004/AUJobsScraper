import asyncio
import json
import random
import re
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from jobly.scrapers.base_scraper import BaseScraper
from jobly.config import settings
from jobly.utils.scraper_utils import (
    remove_html_tags,
    extract_salary_from_text,
    determine_seniority,
    normalize_locations,
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
                        
                        for job_url in new_links:
                            await self._process_job(page, job_url)
                                
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
            
            # Wait for the description container to ensure dynamic content is loaded
            # Try waiting for either standard or campaign container
            try:
                # We can't easily wait for "OR" in playwright without a complex selector or Promise.race
                # So we'll just wait for a generic indicator or a short timeout for the primary one
                # Actually, let's try waiting for the h1 which is common
                await page.wait_for_selector("h1.employers-profile-h1", timeout=10000)
                # Give a little extra time for the rest of the body to render
                await asyncio.sleep(2)
            except Exception:
                self.logger.warning(f"Timeout waiting for h1 on {job_url}")

            job_content = await page.content()
            job_soup = BeautifulSoup(job_content, 'lxml')
            
            # ===== EVENT FILTERING =====
            # Check if this is an event posting and skip if so
            # Events should not be saved to the database
            
            # First check for "Sign up to event" button (strong indicator)
            event_button = job_soup.find("button", string=lambda s: s and "sign up to event" in s.lower())
            if event_button:
                self.logger.info(f"Skipping event posting (found 'Sign up to event' button): {job_url}")
                return None
            
            # Also check for Job Type field in ul.box-content (Strategy 2 page structure)
            box_content_check = job_soup.select_one("ul.box-content")
            if box_content_check:
                for li in box_content_check.find_all("li"):
                    strong = li.find("strong")
                    if strong and "job type" in strong.text.strip().lower():
                        # Get value by removing the strong tag text from li text
                        value = li.text.replace(strong.text, "").strip()
                        if "event" in value.lower():
                            self.logger.info(f"Skipping event posting (Job Type = Event): {job_url}")
                            return None
            
            # Check for Job Type in overview container (Strategy 1 page structure)
            overview_check = job_soup.select_one("div.job-overview-container")
            if overview_check:
                dt = overview_check.find("dt", string=lambda text: text and "Job Type" in text)
                if dt:
                    dd = dt.find_next_sibling("dd")
                    if dd and "event" in dd.text.strip().lower():
                        self.logger.info(f"Skipping event posting (Job Type = Event): {job_url}")
                        return None
            
            # Initialize fields
            title = "Unknown Title"
            company = "Unknown Company"
            location = "Australia"
            description = ""
            salary = None
            posted_at = None
            application_deadline = None
            
            # Extract Title
            title_elem = job_soup.select_one("h1.employers-profile-h1")
            if title_elem:
                title = title_elem.text.strip()
            
            # Extract Company
            company_elem = job_soup.select_one("h1.employers-panel-title")
            if company_elem:
                company = company_elem.text.strip()
            
            # ===== PRIMARY STRATEGY: Extract from JSON via JavaScript =====
            # Try to extract data from window.__initialState__ JSON object by evaluating JavaScript
            json_data = None
            try:
                # Use page.evaluate to get the JSON object directly from JavaScript context
                # This avoids parsing issues with large JSON strings
                json_data = await page.evaluate("() => window.__initialState__")
                if json_data:
                    self.logger.info("Successfully extracted window.__initialState__ via JavaScript")
            except Exception as e:
                self.logger.warning(f"Failed to extract JSON data via JavaScript: {e}")
            
            # Extract from JSON if available
            if json_data:
                try:
                    # Navigate to the job data in the JSON structure
                    # Structure: {"campaignstore": {"campaign": {...}}}
                    campaign = json_data.get("campaignstore", {}).get("campaign", {})
                    
                    # Extract locations (it's a list)
                    locations_list = campaign.get("locations", [])
                    if locations_list:
                        location = ", ".join(locations_list)
                        self.logger.info(f"Extracted {len(locations_list)} locations from JSON")
                    
                    # Extract salary if available
                    sal_text = campaign.get("salary")
                    if sal_text:
                        salary = sal_text
                    
                    # Extract closing date
                    closes_text = campaign.get("closing_date")
                    if closes_text:
                        application_deadline = closes_text
                        
                except Exception as e:
                    self.logger.warning(f"Failed to parse JSON fields: {e}")
            
            # ===== FALLBACK STRATEGY: Extract from HTML =====
            # Use HTML extraction if JSON extraction failed OR if key fields are missing
            if not json_data or not location or location == "Australia" or not application_deadline or not posted_at:
                self.logger.info("Using HTML extraction (fallback or supplementary)")
                
                # Strategy 1: Standard Job Page (div.job-overview-container)
                overview_container = job_soup.select_one("div.job-overview-container")
                if overview_container:
                    # Helper to find dd next to dt with specific text
                    def get_detail(label_text):
                        dt = overview_container.find("dt", string=lambda text: text and label_text in text)
                        if dt:
                            dd = dt.find_next_sibling("dd")
                            if dd:
                                return dd.text.strip()
                        return None

                    if not location or location == "Australia":
                        loc_text = get_detail("Locations")
                        if loc_text:
                            location = loc_text
                    
                    if not salary:
                        sal_text = get_detail("Salary")
                        if sal_text:
                            salary = sal_text
                    
                    if not application_deadline:
                        closes_text = get_detail("Closes")
                        if closes_text:
                            application_deadline = closes_text

                    if not posted_at:
                        posted_text = get_detail("Posted")
                        if posted_text:
                            posted_at = posted_text

                # Strategy 2: Campaign Style Page (ul.box-content)
                else:
                    box_content = job_soup.select_one("ul.box-content")
                    if box_content:
                        for li in box_content.find_all("li"):
                            strong = li.find("strong")
                            if not strong:
                                continue
                            
                            label = strong.text.strip().lower()
                            # Remove the strong tag to get the rest of the text
                            strong.extract()
                            value = li.text.strip()
                            
                            if "locations" in label and (not location or location == "Australia"):
                                location = value
                            elif "salary" in label and not salary:
                                salary = value
                            elif "closing date" in label and not application_deadline:
                                application_deadline = value
                            elif "posted" in label and not posted_at:
                                posted_at = value
                
                # Clean up "...show more" text if present (should not be needed with JSON extraction)
                if location and ("...show more" in location.lower() or "show more" in location.lower()):
                    location = re.sub(r'\.{2,}show more', '', location, flags=re.IGNORECASE).strip()
                    self.logger.warning(f"Removed 'show more' text from location: {location[:100]}...")

            # Extract Description
            # Strategy 1: Standard Job Page
            desc_elem = job_soup.select_one("div.job-description-container")
            
            # Strategy 2: Campaign Style Page
            if not desc_elem:
                desc_elem = job_soup.select_one("div.campaign-content-container")
            
            if desc_elem:
                description = remove_html_tags(str(desc_elem))
            else:
                # Fallback to body if specific container not found
                # Try to find main content area first
                main_elem = job_soup.find("main")
                if main_elem:
                    description = remove_html_tags(str(main_elem))
                else:
                    description = remove_html_tags(str(job_soup.body))
            
            self.logger.info(f"Extracted: {title} at {company}")
            self.logger.info(f"Location: {location}, Salary: {salary}, Deadline: {application_deadline}")

            # Parse closing date if available
            closing_date = None
            if application_deadline:
                try:
                    # Remove ordinal suffix (st, nd, rd, th)
                    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", application_deadline)
                    dt = datetime.strptime(cleaned, "%d %b %Y, %I:%M %p")
                    closing_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    self.logger.warning(f"Failed to parse closing date '{application_deadline}': {e}")
            
            # Split and normalize locations to structured format
            # Location may be a comma-separated string like "Brisbane, QLD, Melbourne, VIC"
            location_list = [loc.strip() for loc in location.split(',') if loc.strip()]
            locations = normalize_locations(location_list)

            job_data = {
                "job_title": title,
                "company": company,
                "locations": locations,
                "source_urls": [job_url],
                "description": description,
                "salary": salary,
                "seniority": "Junior",
                "llm_analysis": None,
                "platforms": ["gradconnection"],
                "posted_at": posted_at,
                "closing_date": closing_date
            }
            
            saved_job = self.save_job(job_data)
            if saved_job:
                self.logger.info(f"Saved job: {title}")

            return job_data
            
        except Exception as e:
            self.logger.error(f"Error scraping job details {job_url}: {e}")

    def run(self, initial_run: bool = False):
        asyncio.run(self.scrape(initial_run=initial_run))


if __name__ == "__main__":
    scraper = GradConnectionScraper()
    scraper.run()

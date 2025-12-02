import os
import asyncio
import random
from typing import Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from jobly.scrapers.base_scraper import BaseScraper
from jobly.config import settings
from jobly.utils.scraper_utils import (
    remove_html_tags,
    calculate_posted_date,
    determine_seniority,
    extract_job_role,
    normalize_locations,
)

class SeekScraper(BaseScraper):
    def __init__(self):
        super().__init__("seek")
        self.base_url = "https://www.seek.com.au"

    async def scrape(self):
        self.logger.info("Starting Seek Scraper...")
        
        initial_run = settings.scraper.initial_run
        terms = settings.scraper.search_keywords
        limit = settings.scraper.max_pages
        days_ago = settings.scraper.initial_days_from_posted if initial_run else settings.scraper.days_from_posted
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
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
                            self.logger.info("No more results found or error fetching links.")
                            break
                        
                        # Deduplication: Check which URLs already exist
                        # If initial_run is True, we only consider "complete" jobs (with posted_at) as existing.
                        # This allows us to re-scrape jobs that have null posted_at.
                        existing_urls = self.db.check_existing_urls(job_links, only_complete=initial_run)
                        new_links = [link for link in job_links if link not in existing_urls]
                        
                        skipped_count = len(job_links) - len(new_links)
                        if skipped_count > 0:
                            self.logger.info(f"Skipping {skipped_count} existing jobs.")
                        
                        self.logger.info(f"Found {len(new_links)} NEW jobs on page {page_num}")
                        
                        await self.process_jobs_concurrently(context, new_links)
                                
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num}: {e}")

            await browser.close()
            self.logger.info("Seek Scraper Finished.")

    async def _get_job_links(self, page, url: str) -> list:
        """
        Navigates to the list page and extracts job links.
        """
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 4))
            
            content = await page.content()
            if "No matching search results" in content:
                return []

            soup = BeautifulSoup(content, 'lxml')
            
            job_links = []
            title_elements = soup.find_all("a", attrs={"data-automation": "jobTitle"})
            
            for elem in title_elements:
                link = elem['href']
                if not link.startswith("http"):
                    link = self.base_url + link.split("?")[0]
                job_links.append(link)
            
            return job_links
        except Exception as e:
            self.logger.error(f"Error getting job links from {url}: {e}")
            return []

 

    async def _process_job(self, page, job_url: str):
        """
        Navigates to a job URL, extracts details, and saves the job.
        """
        try:
            self.logger.info(f"Scraping Job: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 3))
            
            # Extract all fields
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            extracted = {
                "title": self._extract_title(soup),
                "company": self._extract_company(soup),
                "location": self._extract_location(soup),
                "description": self._extract_description(soup),
                "salary": self._extract_salary(soup),
                "posted_at": self._extract_posted_date(soup),
            }
            
            # Build JobPosting using base class helper
            job_posting = self._build_job_posting(
                job_title=extracted["title"],
                company=extracted["company"],
                raw_locations=[extracted["location"]],
                source_url=job_url,
                description=extracted["description"],
                salary=extracted.get("salary"),
                posted_at=extracted.get("posted_at"),
            )
            
            # Save to database
            self.save_job(job_posting)
            
        except Exception as e:
            self.logger.error(f"Error scraping job {job_url}: {e}")
    
    def _extract_title(self, soup) -> str:
        """Extract job title from page"""
        elem = soup.find("h1", attrs={"data-automation": "job-detail-title"})
        return elem.text.strip() if elem else "Unknown Title"
    
    def _extract_company(self, soup) -> str:
        """Extract company name from page"""
        elem = soup.find("span", attrs={"data-automation": "advertiser-name"})
        return elem.text.strip() if elem else "Unknown Company"
    
    def _extract_location(self, soup) -> str:
        """Extract location from page"""
        elem = soup.find("span", attrs={"data-automation": "job-detail-location"})
        return elem.text.strip() if elem else "Australia"
    
    def _extract_salary(self, soup) -> Optional[str]:
        """Extract salary from page"""
        elem = soup.find("span", attrs={"data-automation": "job-detail-salary"})
        return elem.text.strip() if elem else None
    
    def _extract_description(self, soup) -> str:
        """Extract job description from page"""
        elem = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        raw_content = str(elem) if elem else str(soup.find("body"))
        return remove_html_tags(raw_content)
    
    def _extract_posted_date(self, soup) -> Optional[str]:
        """Extract posted date from page"""
        meta_elements = soup.find_all(
            "span", 
            class_="_2953uf0 _1cvgfrq50 eytv690 eytv691 eytv691u eytv696 _1lwlriv4"
        )
        for elem in meta_elements:
            if "Posted" in elem.text:
                raw_text = elem.text.strip()
                return calculate_posted_date(raw_text)
        return None

    def run(self):
        # Default run with config values
        asyncio.run(self.scrape())

if __name__ == "__main__":
    scraper = SeekScraper()
    scraper.run()

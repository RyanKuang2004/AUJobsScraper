import os
import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from jobly.scrapers.base_scraper import BaseScraper
from jobly.config import settings
from jobly.utils.scraper_utils import (
    remove_html_tags,
    calculate_posted_date,
    determine_seniority,
)

class SeekScraper(BaseScraper):
    def __init__(self):
        super().__init__("seek")
        self.base_url = "https://www.seek.com.au"

    async def scrape(self, initial_run: bool = False):
        self.logger.info("Starting Seek Scraper...")
        
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
                        
                        for job_url in new_links:
                            await self._process_job(page, job_url)
                                
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
            
            job_content = await page.content()
            job_soup = BeautifulSoup(job_content, 'lxml')
            
            # Extract Title
            title_elem = job_soup.find("h1", attrs={"data-automation": "job-detail-title"})
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            # Extract Company
            company_elem = job_soup.find("span", attrs={"data-automation": "advertiser-name"})
            company = company_elem.text.strip() if company_elem else "Unknown Company"
            
            # Extract Location
            location_elem = job_soup.find("span", attrs={"data-automation": "job-detail-location"})
            location = location_elem.text.strip() if location_elem else "Australia"
            
            # Extract Salary
            salary_elem = job_soup.find("span", attrs={"data-automation": "job-detail-salary"})
            salary = salary_elem.text.strip() if salary_elem else None
            
            # Extract Description
            description_elem = job_soup.find("div", attrs={"data-automation": "jobAdDetails"})
            raw_content = str(description_elem) if description_elem else str(job_soup.find("body"))
            description = remove_html_tags(raw_content)

            # Extract seniority level (Junior, Senior, Intermediate)
            seniority = determine_seniority(title)

            # Extract posted_at
            posted_at = None
            meta_elements = job_soup.find_all("span", class_="_2953uf0 _1cvgfrq50 eytv690 eytv691 eytv691u eytv696 _1lwlriv4")
            for elem in meta_elements:
                if "Posted" in elem.text:
                    raw_text = elem.text.strip()
                    posted_at = calculate_posted_date(raw_text)
                    break
            
            self.logger.info(f"Extracted: {title} at {company}")

            # LLM Analysis is now handled by a separate process (job_processor.py)
            llm_analysis = None

            job_data = {
                "job_title": title,
                "company": company,
                "locations": [location],
                "source_urls": [job_url],
                "description": description,
                "salary": salary,
                "seniority": seniority,
                "llm_analysis": llm_analysis,
                "platforms": ["seek"],
                "posted_at": posted_at,
            }
            
            saved_job = self.save_job(job_data)
            if saved_job:
                self.logger.info(f"Saved job: {title}")

            return job_data
            
        except Exception as e:
            self.logger.error(f"Error scraping job details {job_url}: {e}")

    def run(self, initial_run: bool = False):
        # Default run with config values
        asyncio.run(self.scrape(initial_run=initial_run))

if __name__ == "__main__":
    scraper = SeekScraper()
    scraper.run()

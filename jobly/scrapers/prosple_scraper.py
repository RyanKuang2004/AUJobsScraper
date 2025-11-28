import asyncio
import random
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from jobly.scrapers.base_scraper import BaseScraper
from jobly.config import settings

class ProspleScraper(BaseScraper):
    def __init__(self):
        super().__init__("prosple")
        self.base_url = "https://au.prosple.com"
        # Base search URL as requested
        self.search_url_base = "https://au.prosple.com/search-jobs?locations=9692&study_fields=502&opportunity_types=1"

    async def scrape(self, initial_run: bool = False):
        self.logger.info("Starting Prosple Scraper...")
        
        items_per_page = 20
        start = 0
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            while True:
                url = f"{self.search_url_base}&start={start}"
                self.logger.info(f"Visiting List Page: {url}")
                
                try:
                    job_links_data = await self._get_job_links(page, url)
                    if not job_links_data:
                        self.logger.info("No more results found.")
                        break
                    
                    # Deduplication
                    current_urls = [d['url'] for d in job_links_data]
                    existing_urls = self.db.check_existing_urls(current_urls, only_complete=initial_run)
                    
                    new_jobs_data = [d for d in job_links_data if d['url'] not in existing_urls]
                    
                    skipped_count = len(job_links_data) - len(new_jobs_data)
                    if skipped_count > 0:
                        self.logger.info(f"Skipping {skipped_count} existing jobs.")
                    
                    self.logger.info(f"Found {len(new_jobs_data)} NEW jobs on page start={start}")
                    
                    for job_data in new_jobs_data:
                        await self._process_job(page, job_data)
                    
                    start += items_per_page
                    
                except Exception as e:
                    self.logger.error(f"Error processing page start={start}: {e}")
                    break

            await browser.close()
            self.logger.info("Prosple Scraper Finished.")

    async def _get_job_links(self, page: Page, url: str) -> List[Dict[str, Any]]:
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 4))
            
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            # The container for results
            results_container = soup.find("div", class_="sc-2a88d303-1 ZsVbA")
            if not results_container:
                # Check if we are just out of results (page might be empty or have different structure)
                if "No matching search results" in content:
                    return []
                # If container not found but page loaded, maybe selector changed or empty
                return []

            job_cards = results_container.find_all("a", href=True)
            
            jobs_data = []
            for card in job_cards:
                link = card['href']
                if not link.startswith("http"):
                    link = self.base_url + link.split("?")[0]
                
                # Extract salary from card
                salary = None
                card_text = card.get_text(separator="\n", strip=True)
                lines = card_text.split("\n")
                for line in lines:
                    if "AUD" in line or "/ Year" in line or "/ Hour" in line:
                        salary = line.strip()
                        break
                
                jobs_data.append({
                    "url": link,
                    "salary": salary
                })
            
            return jobs_data

        except Exception as e:
            self.logger.error(f"Error getting job links from {url}: {e}")
            return []

    async def _process_job(self, page: Page, job_info: Dict[str, Any]):
        job_url = job_info['url']
        salary = job_info['salary']
        
        try:
            self.logger.info(f"Scraping Job: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 3))
            
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            # Title
            title_elem = soup.find("h1")
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            # Company
            # Look for a link to graduate-employers which usually contains the company name
            company = "Unknown Company"
            company_elem = soup.find("a", href=lambda x: x and "/graduate-employers/" in x)
            if company_elem:
                company = company_elem.text.strip()
            else:
                # Fallback: try to find it in text if not a link
                # This is a bit loose, but better than nothing.
                pass
            
            # Location
            location = "Australia"
            # Try to find text that looks like a location or is near "Location" label
            # Often in header metadata
            # We can search for common Australian cities in the text as a heuristic if specific selector fails
            # But let's try to grab the header text
            header_elem = soup.find("header")
            if header_elem:
                header_text = header_elem.get_text()
                # Very basic extraction, maybe improve later if specific selector found
            
            # Description
            # Combine text from the main content area
            # We'll grab the main container. 
            # Based on common structure, it might be 'main' or a specific div.
            description = ""
            main_content = soup.find("main")
            if main_content:
                description = self._remove_html_tags(str(main_content))
            else:
                description = self._remove_html_tags(str(soup.body))

            # Seniority
            seniority = self._determine_seniority(title)
            
            job_data = {
                "job_title": title,
                "company": company,
                "locations": [location],
                "source_urls": [job_url],
                "description": description,
                "salary": salary,
                "seniority": seniority,
                "llm_analysis": None,
                "platforms": ["prosple"],
                "posted_at": None,
            }
            
            self.save_job(job_data)

        except Exception as e:
            self.logger.error(f"Error scraping job details {job_url}: {e}")

    def _remove_html_tags(self, content: str) -> str:
        if not content:
            return ""
        soup = BeautifulSoup(content, 'lxml')
        return soup.get_text(separator="\n", strip=True)

    def _determine_seniority(self, title: str) -> str:
        text = title.lower()
        if "senior" in text or "lead" in text or "principal" in text or "manager" in text:
            return "Senior"
        elif "junior" in text or "graduate" in text or "entry" in text:
            return "Junior"
        elif "intermediate" in text or "mid" in text:
            return "Intermediate"
        return "N/A"

if __name__ == "__main__":
    scraper = ProspleScraper()
    asyncio.run(scraper.scrape())

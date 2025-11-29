import asyncio
import random
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
import json
from jobly.scrapers.base_scraper import BaseScraper
from jobly.config import settings
from jobly.utils.scraper_utils import (
    remove_html_tags,
    extract_salary_from_text,
    determine_seniority,
    extract_job_role
)

class ProspleScraper(BaseScraper):
    def __init__(self):
        super().__init__("prosple")
        self.base_url = "https://au.prosple.com"
        # Base search URL as requested
        self.search_url_base = "https://au.prosple.com/search-jobs?locations=9692&study_fields=502&opportunity_types=1"

    async def scrape(self):
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
                    existing_urls = self.db.check_existing_urls(current_urls)
                    
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
            # Based on user request, we look for h2 with specific class
            # class="sc-dOfePm dyaRTx heading sc-692f12d5-0 bTRRDW"
            job_cards = soup.find_all("h2", class_="sc-dOfePm dyaRTx heading sc-692f12d5-0 bTRRDW")
            
            if not job_cards:
                # Check if we are just out of results (page might be empty or have different structure)
                if "No matching search results" in content:
                    return []
                # If container not found but page loaded, maybe selector changed or empty
                return []

            jobs_data = []
            for card_h2 in job_cards:
                link_elem = card_h2.find("a", href=True)
                if not link_elem:
                    continue

                link = link_elem['href']
                if not link.startswith("http"):
                    # Ensure we don't double slash if base_url ends with / and link starts with /
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
            
            # Get full HTML including dynamically loaded content if any
            # But for JSON-LD, domcontentloaded might be enough. 
            # Sometimes JSON-LD is injected by JS, so we might want to wait a bit or check content.
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')
            
            # Initialize fields
            title = "Unknown Title"
            company = "Unknown Company"
            description = ""
            salary = None
            posted_at = None
            application_deadline = None
            work_type = None
            closing_date = None

            # 1. Try JSON-LD Extraction
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            json_data = None
            
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                        json_data = data
                        break
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                json_data = item
                                break
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            if json_data:
                self.logger.info("Found JSON-LD JobPosting data")
                title = json_data.get('title', title)
                title = extract_job_role(title)
                
                hiring_org = json_data.get('hiringOrganization')
                if isinstance(hiring_org, dict):
                    company = hiring_org.get('name', company)
                elif isinstance(hiring_org, str):
                    company = hiring_org
                
                job_loc = json_data.get('jobLocation')
                if isinstance(job_loc, list):
                    locations = [loc["address"] for loc in job_loc if isinstance(loc, dict)]

                    for i, loc in enumerate(locations):
                        if type(loc) == dict:
                            locations[i] = loc.get('addressLocality')
                
                if locations == [None]:
                    locations = ["Australia"]

                description_html = json_data.get('description', "")
                description = remove_html_tags(description_html)
                
                posted_at = json_data.get('datePosted')
                application_deadline = json_data.get('validThrough')
                
                emp_type = json_data.get('employmentType')
                if isinstance(emp_type, list):
                    work_type = ", ".join(emp_type)
                else:
                    work_type = emp_type

            # 2. Fallback / Supplement with HTML Scraping
            
            # Title fallback / refinement (H1 often has more detail like "Start ASAP")
            if title == "Unknown Title" or True: # Always check H1 as it might be better formatted
                h1_elem = soup.find("h1")
                if h1_elem:
                    h1_text = h1_elem.text.strip()
                    if h1_text:
                        title = extract_job_role(h1_text)

            # Company fallback
            if company == "Unknown Company":
                company_elem = soup.find("a", href=lambda x: x and "/graduate-employers/" in x)
                if company_elem:
                    company = company_elem.text.strip()

            # Description fallback
            if not description:
                main_content = soup.find("main")
                if main_content:
                    description = remove_html_tags(str(main_content))
                else:
                    description = remove_html_tags(str(soup.body))

            # Salary Extraction
            # Check JSON-LD baseSalary first (rarely present but good to check)
            if json_data and 'baseSalary' in json_data:
                salary_val = json_data['baseSalary']
                if isinstance(salary_val, dict):
                    # value might be a dict or value
                    val = salary_val.get('value')
                    if isinstance(val, dict):
                        min_sal = val.get('minValue')
                        max_sal = val.get('maxValue')
                        unit = val.get('unitText', '')
                        if min_sal and max_sal:
                            salary = f"{min_sal} - {max_sal} {unit}"
                        elif val.get('value'):
                            salary = f"{val.get('value')} {unit}"
            
            if not salary:
                # Try to extract from description text
                salary = extract_salary_from_text(description)

            # Application closing date

            if json_data and 'validThrough' in json_data:
                closing_date = json_data['validThrough']
            
            final_job_data = {
                "job_title": title,
                "company": company,
                "locations": locations,
                "source_urls": [job_url],
                "description": description,
                "salary": salary,
                "seniority": "Junior",
                "llm_analysis": None,
                "platforms": ["prosple"],
                "posted_at": posted_at,
                "closing_date": closing_date
            }
            
            # If you have extended schema, you can add them. 
            # For now, I'll log them or append to description if critical?
            # Let's just keep standard fields.
            
            self.save_job(final_job_data)

        except Exception as e:
            self.logger.error(f"Error scraping job details {job_url}: {e}")

    def run(self):
        # Default run with config values
        asyncio.run(self.scrape())

if __name__ == "__main__":
    scraper = ProspleScraper()
    scraper.run()

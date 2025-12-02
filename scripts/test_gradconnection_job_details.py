"""
Test script to verify GradConnection job details extraction using the actual Scraper class.
"""
import asyncio
from playwright.async_api import async_playwright
from jobly.scrapers.gradconnection_scraper import GradConnectionScraper

async def test_job_extraction():
    # Example Job URL
    #job_url = "https://au.gradconnection.com/employers/citadel-citadel-securities/jobs/citadel-securities-2025-2026-quantitative-research-phd-internship-engineering-10/"
    #job_url = "https://au.gradconnection.com/employers/tiktok/jobs/tiktok-graduate-frontend-engineer-tiktok-live-2026-start-8/"
    job_url = "https://au.gradconnection.com/employers/tiktok/jobs/tiktok-backend-software-engineer-graduate-trust-and-safety-engineering-2026-start-17/"

    print(f"Testing GradConnection Job Extraction")
    print(f"URL: {job_url}")
    print("=" * 80)
    
    scraper = GradConnectionScraper()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Call the actual method from the scraper
            job_data = await scraper._process_job(page, job_url)
            
            if job_data:
                print("\n--- Extracted Data ---")
                print(f"Title:       {job_data.get('job_title')}")
                print(f"Company:     {job_data.get('company')}")
                print(f"Location:    {job_data.get('locations')}")
                print(f"Salary:      {job_data.get('salary')}")
                print(f"Seniority:   {job_data.get('seniority')}")
                print(f"Posted At:   {job_data.get('posted_at')}")
                print(f"Deadline:    {job_data.get('closing_date')}")
                print("-" * 40)
                print(f"Description:\n{job_data.get('description', '')[:100]}...")
                print("-" * 40)
                
                with open("extracted_dates.txt", "w", encoding="utf-8") as f:
                    f.write(f"Posted At: {job_data.get('posted_at')}\n")
                    f.write(f"Deadline: {job_data.get('closing_date')}\n")
                
                desc = job_data.get('description', '')
                if job_data.get('job_title') != "Unknown Title" and len(desc) > 100:
                     print("\nSUCCESS: Fields extracted correctly.")
                else:
                     print("\nFAILURE: Issues with extraction.")
            else:
                print("\nFAILURE: No data returned.")

        except Exception as e:
            print(f"Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_job_extraction())

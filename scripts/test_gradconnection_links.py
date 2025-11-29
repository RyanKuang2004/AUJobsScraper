"""
Test script to verify GradConnection link extraction.
This script will print all job links found on the first few pages.
"""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import random


async def test_get_job_links():
    base_url = "https://au.gradconnection.com"
    search_term = "Data+Science"  # Example search term
    max_pages = 3  
    starting_page = 5
    
    print(f"Testing GradConnection link extraction for '{search_term}'")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for page_num in range(starting_page, max_pages + starting_page):
            url = f"{base_url}/jobs/australia/?title={search_term}&page={page_num}"
            print(f"\n--- Page {page_num} ---")
            print(f"URL: {url}")
            
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 4))
                
                content = await page.content()
                soup = BeautifulSoup(content, 'lxml')
                
                # Find all <a> tags with class "box-header-title"
                title_elements = soup.find_all("a", class_="box-header-title")
                
                if not title_elements:
                    print("No job links found on this page.")
                    break
                
                print(f"Found {len(title_elements)} job links:")
                
                for idx, elem in enumerate(title_elements, 1):
                    href = elem.get('href')
                    title = elem.text.strip()
                    
                    if not href:
                        print(f"  {idx}. (No href) {title}")
                        continue
                    
                    # Check for notify-me link
                    if "notifyme" in href or "notify-me" in href:
                        print(f"\n🛑 STOPPING CONDITION FOUND!")
                        print(f"  Found notify-me link: {href}")
                        await browser.close()
                        return
                    
                    # Construct full URL
                    if not href.startswith("http"):
                        full_href = f"{base_url.rstrip('/')}{href if href.startswith('/') else '/' + href}"
                    else:
                        full_href = href
                    
                    print(f"  {idx}. {title}")
                    print(f"     {full_href}")
                
            except Exception as e:
                print(f"Error on page {page_num}: {e}")
                break
        
        await browser.close()
        print("\n" + "=" * 80)
        print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_get_job_links())

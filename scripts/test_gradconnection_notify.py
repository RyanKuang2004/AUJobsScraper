"""
Test script to verify GradConnection link extraction with notify-me detection.
This script will print all job links and specifically test the notify-me stopping condition.
"""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import random


async def test_gradconnection_with_notify_detection():
    base_url = "https://au.gradconnection.com"
    max_pages = 10  # Test up to 10 pages to find notify-me
    
    print(f"Testing GradConnection link extraction (looking for notify-me links)")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        total_jobs = 0
        
        for page_num in range(1, max_pages + 1):
            # Using general search without filters to get more results
            url = f"{base_url}/jobs/australia/?page={page_num}"
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
                page_jobs = 0
                
                for idx, elem in enumerate(title_elements, 1):
                    href = elem.get('href')
                    title = elem.text.strip()
                    
                    if not href:
                        print(f"  {idx}. (No href) {title}")
                        continue
                    
                    # Check for notify-me link
                    if "notifyme" in href or "notify-me" in href:
                        print(f"\n🛑 STOPPING CONDITION FOUND!")
                        print(f"  Position: Link #{idx} on Page {page_num}")
                        print(f"  Title: {title}")
                        print(f"  Href: {href}")
                        print(f"\nTotal jobs found before hitting notify-me: {total_jobs}")
                        await browser.close()
                        return
                    
                    # Construct full URL
                    if not href.startswith("http"):
                        full_href = f"{base_url.rstrip('/')}{href if href.startswith('/') else '/' + href}"
                    else:
                        full_href = href
                    
                    # Only print first 3 and last 2 to save space
                    if idx <= 3 or idx > len(title_elements) - 2:
                        print(f"  {idx}. {title[:70]}...")
                        print(f"     {full_href}")
                    elif idx == 4:
                        print(f"  ... ({len(title_elements) - 5} more jobs) ...")
                    
                    page_jobs += 1
                    total_jobs += 1
                
                print(f"\nPage Summary: {page_jobs} jobs on this page | Total so far: {total_jobs}")
                
            except Exception as e:
                print(f"Error on page {page_num}: {e}")
                break
        
        await browser.close()
        print("\n" + "=" * 80)
        print(f"Test completed! Total jobs found: {total_jobs}")
        print("No notify-me link encountered (might be further in pagination)")


if __name__ == "__main__":
    asyncio.run(test_gradconnection_with_notify_detection())

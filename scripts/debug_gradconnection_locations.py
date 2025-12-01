import asyncio
from playwright.async_api import async_playwright

async def debug_locations():
    job_url = "https://au.gradconnection.com/employers/premium-graduate-placements/jobs/premium-graduate-placements-2025-human-resources-internships-program-apply-today-11/"
    print(f"Debugging URL: {job_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await page.goto(job_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000) # Wait for dynamic content
        
        # 1. Dump initial HTML
        with open("debug_gc_initial.html", "w", encoding="utf-8") as f:
            f.write(await page.content())
        print("Saved debug_gc_initial.html")
        
        # 2. Check for "show more" button
        # Try different selectors
        buttons = await page.query_selector_all("button")
        print(f"Found {len(buttons)} buttons")
        
        show_more_btn = None
        for btn in buttons:
            text = await btn.text_content()
            if text and "show more" in text.lower():
                print(f"Found 'show more' button: {text} | Class: {await btn.get_attribute('class')}")
                show_more_btn = btn
                break
        
        if show_more_btn:
            print("Clicking 'show more' button...")
            await show_more_btn.click()
            await page.wait_for_timeout(2000)
            
            # 3. Dump HTML after click
            with open("debug_gc_after_click.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            print("Saved debug_gc_after_click.html")
        else:
            print("Could not find 'show more' button via text search.")
            
            # Try looking for the specific structure mentioned in the scraper
            # button.show-more:has-text("show more")
            specific_btn = await page.query_selector("button.show-more")
            if specific_btn:
                 print("Found button.show-more via selector!")
            else:
                 print("Did not find button.show-more via selector.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_locations())

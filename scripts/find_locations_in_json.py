import asyncio
from playwright.async_api import async_playwright
import json

async def find_locations_in_json():
    job_url = "https://au.gradconnection.com/employers/premium-graduate-placements/jobs/premium-graduate-placements-2025-human-resources-internships-program-apply-today-11/"
    
    print(f"Searching for locations in JSON...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await page.goto(job_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # Extract the JSON
        json_data = await page.evaluate("() => window.__initialState__")
        
        # Recursive function to search for the locations array
        def find_key(obj, target_key, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key == target_key:
                        print(f"\n✓ Found '{target_key}' at path: {current_path}")
                        print(f"  Value type: {type(value)}")
                        if isinstance(value, list):
                            print(f"  List length: {len(value)}")
                            if len(value) > 0:
                                print(f"  First few items: {value[:5]}")
                        elif isinstance(value, str):
                            print(f"  Value: {value[:200]}")
                    if isinstance(value, (dict, list)):
                        find_key(value, target_key, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    if isinstance(item, (dict, list)):
                        find_key(item, target_key, current_path)
        
        find_key(json_data, "locations")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_locations_in_json())

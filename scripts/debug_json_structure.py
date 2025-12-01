import asyncio
from playwright.async_api import async_playwright
import json

async def debug_json_structure():
    job_url = "https://au.gradconnection.com/employers/premium-graduate-placements/jobs/premium-graduate-placements-2025-human-resources-internships-program-apply-today-11/"
    
    print(f"Debugging JSON structure for: {job_url}")
    
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
        
        if json_data:
            print("\nJSON extracted successfully!")
            print(f"Top-level keys: {list(json_data.keys())}")
            
            # Check for jobDetails
            if "jobDetails" in json_data:
                print(f"\njobDetails keys: {list(json_data['jobDetails'].keys())}")
                
                if "job" in json_data["jobDetails"]:
                    job = json_data["jobDetails"]["job"]
                    print(f"\njob keys: {list(job.keys())[:20]}...")  # First 20 keys
                    
                    # Check for locations
                    if "locations" in job:
                        locations = job["locations"]
                        print(f"\nLocations found: {locations}")
                        print(f"Number of locations: {len(locations)}")
                    else:
                        print("\n'locations' key NOT found in job")
                        # Search for location-related keys
                        location_keys = [k for k in job.keys() if 'location' in k.lower()]
                        print(f"Keys containing 'location': {location_keys}")
                else:
                    print("\n'job' key NOT found in jobDetails")
            else:
                print("\n'jobDetails' key NOT found")
                # Try to find it elsewhere
                for key in json_data.keys():
                    if 'job' in key.lower():
                        print(f"Found job-related key: {key}")
        else:
            print("Failed to extract JSON")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_json_structure())

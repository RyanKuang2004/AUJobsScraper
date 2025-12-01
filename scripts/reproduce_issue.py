import asyncio
from playwright.async_api import async_playwright
from jobly.scrapers.gradconnection_scraper import GradConnectionScraper

async def reproduce_issue():
    job_url = "https://au.gradconnection.com/employers/premium-graduate-placements/jobs/premium-graduate-placements-2025-human-resources-internships-program-apply-today-11/"
    expected_locations = [
        'Canberra', 'Regional ACT', 'Regional New South Wales', 'Sydney', 'Darwin', 
        'Regional Northern Territory', 'Brisbane', 'Gold Coast', 'Regional Queensland', 
        'Adelaide', 'Regional South Australia', 'Hobart', 'Regional Tasmania', 
        'Melbourne', 'Regional Victoria', 'Perth', 'Regional Western Australia'
    ]

    print(f"Reproducing Issue for URL: {job_url}")
    
    scraper = GradConnectionScraper()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            job_data = await scraper._process_job(page, job_url)
            
            if job_data:
                extracted_locations = job_data.get('locations', [])
                # The scraper currently returns a list with a single string if it's comma separated, or multiple?
                # The code shows: "locations": [location] where location is a string.
                # So we likely need to split the string to compare.
                
                print(f"Extracted Raw: {extracted_locations}")
                
                if extracted_locations:
                    # Assuming the scraper returns a list containing one string of comma-separated locations
                    # or a list of strings. The current code does: locations = [location]
                    raw_location_str = extracted_locations[0]
                    
                    # Normalize for comparison
                    # The expected locations might be comma separated in the string
                    
                    missing = []
                    for loc in expected_locations:
                        if loc.lower() not in raw_location_str.lower():
                            missing.append(loc)
                    
                    if missing:
                        print(f"\n❌ FAILED: Missing locations: {missing}")
                        print(f"Got: {raw_location_str}")
                    else:
                        print("\n✅ SUCCESS: All locations found.")
                else:
                    print("\n❌ FAILED: No locations extracted.")

            else:
                print("\n❌ FAILED: No data returned.")

        except Exception as e:
            print(f"Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(reproduce_issue())

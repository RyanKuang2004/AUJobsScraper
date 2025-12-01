"""
Test script to verify GradConnection scraper updates:
1. Event filtering - ensure events are skipped
2. Location expansion - ensure "show more" locations are expanded
"""
import asyncio
from playwright.async_api import async_playwright
from jobly.scrapers.gradconnection_scraper import GradConnectionScraper

async def test_event_filtering():
    """Test that event postings are skipped"""
    event_url = "https://au.gradconnection.com/employers/nestle/jobs/nestle-unlock-your-potential-practice-free-psychometric-testing-8/"
    
    print("\n" + "=" * 80)
    print("TEST 1: Event Filtering")
    print("=" * 80)
    print(f"Testing URL: {event_url}")
    print("Expected: Should skip (return None)")
    print("-" * 80)
    
    scraper = GradConnectionScraper()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            job_data = await scraper._process_job(page, event_url)
            
            if job_data is None:
                print("\n✅ SUCCESS: Event posting was correctly skipped")
                result = True
            else:
                print("\n❌ FAILURE: Event posting was NOT skipped")
                print(f"Returned data: {job_data.get('job_title')}")
                result = False
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            result = False
        
        await browser.close()
        return result

async def test_location_expansion():
    """Test that locations with 'show more' are expanded"""
    regular_url = "https://au.gradconnection.com/employers/premium-graduate-placements/jobs/premium-graduate-placements-2025-human-resources-internships-program-apply-today-11/"
    
    print("\n" + "=" * 80)
    print("TEST 2: Location Expansion")
    print("=" * 80)
    print(f"Testing URL: {regular_url}")
    print("Expected: Should expand locations if truncated")
    print("-" * 80)
    
    scraper = GradConnectionScraper()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            job_data = await scraper._process_job(page, regular_url)
            
            if job_data:
                print("\n--- Extracted Data ---")
                print(f"Title:       {job_data.get('job_title')}")
                print(f"Company:     {job_data.get('company')}")
                print(f"Locations:   {job_data.get('locations')}")
                print(f"Salary:      {job_data.get('salary')}")
                print(f"Deadline:    {job_data.get('closing_date')}")
                print("-" * 40)
                
                locations_str = str(job_data.get('locations', []))
                
                # Check if locations were extracted and don't contain "show more"
                if job_data.get('locations') and len(job_data.get('locations')[0]) > 10:
                    if "show more" not in locations_str.lower():
                        print("\n✅ SUCCESS: Locations extracted without 'show more' text")
                        print(f"   Full locations: {locations_str[:200]}...")
                        result = True
                    else:
                        print("\n⚠️  WARNING: Locations still contain 'show more' text")
                        print(f"   Locations: {locations_str}")
                        result = False
                else:
                    print("\n❌ FAILURE: Locations not properly extracted")
                    result = False
            else:
                print("\n❌ FAILURE: No data returned (job should not be skipped)")
                result = False
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            result = False
        
        await browser.close()
        return result

async def main():
    print("\n" + "=" * 80)
    print("GRADCONNECTION SCRAPER UPDATE TESTS")
    print("=" * 80)
    
    # Run both tests
    test1_result = await test_event_filtering()
    test2_result = await test_location_expansion()
    
    # Summary
    print("\n" + "=" *80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Event Filtering:     {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"Location Expansion:  {'✅ PASS' if test2_result else '❌ FAIL'}")
    print("=" * 80)
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")

if __name__ == "__main__":
    asyncio.run(main())

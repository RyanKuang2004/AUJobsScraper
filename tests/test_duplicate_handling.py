"""
Quick test to verify duplicate job handling works correctly.
This test demonstrates the new efficient duplicate detection.
"""

from jobly.db import JobDatabase
from jobly.utils.scraper_utils import normalize_locations

def test_duplicate_detection():
    """Test the new duplicate detection methods"""
    db = JobDatabase()
    
    # Test 1: Check non-existent job
    print("Test 1: Checking non-existent job...")
    result = db.check_duplicate_by_fingerprint("TestCompany", "Test Job Title")
    assert result is None, "Should return None for non-existent job"
    print("✓ Passed: Non-existent job returns None")
    
    # Test 2: Insert a job
    print("\nTest 2: Inserting test job...")
    test_job = {
        "job_title": "Software Engineer",
        "job_role": "Software Engineer",
        "company": "TestCorp",
        "description": "Test description",
        "locations": [{"city": "Sydney", "state": "NSW"}],
        "source_urls": ["https://example.com/job1"],
        "platforms": ["test"],
    }
    
    insert_result = db.upsert_job(test_job)
    job_id = insert_result["id"]
    print(f"✓ Inserted job with ID: {job_id}")
    
    # Test 3: Check duplicate exists
    print("\nTest 3: Checking duplicate detection...")
    duplicate_id = db.check_duplicate_by_fingerprint("TestCorp", "Software Engineer")
    assert duplicate_id == job_id, f"Should return job ID {job_id}, got {duplicate_id}"
    print(f"✓ Passed: Duplicate detected with ID {duplicate_id}")
    
    # Test 4: Update duplicate with new location
    print("\nTest 4: Updating duplicate with new location...")
    new_locations = normalize_locations(["Melbourne, VIC"])
    update_result = db.update_duplicate_job(
        job_id=job_id,
        locations=new_locations,
        source_url="https://example.com/job2",
        platform="test2"
    )
    
    assert update_result["status"] == "updated_duplicate", "Should return updated_duplicate status"
    print(f"✓ Passed: {update_result}")
    
    # Test 5: Verify merged data
    print("\nTest 5: Verifying merged data...")
    updated_job = db.supabase.table("job_postings").select("*").eq("id", job_id).execute()
    job_data = updated_job.data[0]
    
    assert len(job_data["locations"]) == 2, "Should have 2 locations"
    assert len(job_data["source_urls"]) == 2, "Should have 2 source URLs"
    assert len(job_data["platforms"]) == 2, "Should have 2 platforms"
    
    print(f"✓ Locations: {job_data['locations']}")
    print(f"✓ Source URLs: {job_data['source_urls']}")
    print(f"✓ Platforms: {job_data['platforms']}")
    
    # Cleanup
    print("\nCleaning up test data...")
    db.supabase.table("job_postings").delete().eq("id", job_id).execute()
    print("✓ Test data cleaned up")
    
    print("\n" + "="*50)
    print("All tests passed! ✓")
    print("="*50)

if __name__ == "__main__":
    test_duplicate_detection()

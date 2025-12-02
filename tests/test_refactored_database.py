"""
Test to verify the refactored database code works correctly.
Tests both the enhanced update_duplicate_job (with lists) and _update_existing_job.
"""

from jobly.db import JobDatabase
from jobly.utils.scraper_utils import normalize_locations

def test_update_with_lists():
    """Test update_duplicate_job with lists of URLs and platforms"""
    db = JobDatabase()
    
    print("Test 1: Insert initial job...")
    test_job = {
        "job_title": "Backend Developer",
        "job_role": "Backend Developer",
        "company": "TechCorp",
        "description": "Test description",
        "locations": [{"city": "Sydney", "state": "NSW"}],
        "source_urls": ["https://example.com/job1"],
        "platforms": ["seek"],
    }
    
    insert_result = db.upsert_job(test_job)
    job_id = insert_result["id"]
    print(f"✓ Inserted job with ID: {job_id}")
    
    # Test 2: Update with lists of URLs and platforms
    print("\nTest 2: Update with multiple URLs and platforms...")
    new_locations = normalize_locations(["Melbourne, VIC", "Brisbane, QLD"])
    update_result = db.update_duplicate_job(
        job_id=job_id,
        locations=new_locations,
        source_url=["https://example.com/job2", "https://example.com/job3"],  # List
        platform=["prosple", "gradconnection"]  # List
    )
    
    assert update_result["status"] == "updated_duplicate"
    print(f"✓ Updated with lists: {update_result}")
    
    # Test 3: Verify merged data
    print("\nTest 3: Verifying merged data...")
    updated_job = db.supabase.table("job_postings").select("*").eq("id", job_id).execute()
    job_data = updated_job.data[0]
    
    assert len(job_data["locations"]) == 3, f"Expected 3 locations, got {len(job_data['locations'])}"
    assert len(job_data["source_urls"]) == 3, f"Expected 3 URLs, got {len(job_data['source_urls'])}"
    assert len(job_data["platforms"]) == 3, f"Expected 3 platforms, got {len(job_data['platforms'])}"
    
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

def test_upsert_uses_refactored_code():
    """Test that upsert_job uses the refactored _update_existing_job"""
    db = JobDatabase()
    
    print("\nTest 4: Testing upsert with refactored code...")
    
    # Insert initial job
    job1 = {
        "job_title": "Data Scientist",
        "job_role": "Data Scientist",
        "company": "DataCorp",
        "description": "Initial description",
        "locations": [{"city": "Sydney", "state": "NSW"}],
        "source_urls": ["https://example.com/data1"],
        "platforms": ["seek"],
        "salary": "$100k"
    }
    
    result1 = db.upsert_job(job1)
    job_id = result1["id"]
    print(f"✓ Inserted job: {job_id}")
    
    # Upsert same job with new data (should trigger _update_existing_job)
    job2 = {
        "job_title": "Data Scientist",  # Same title
        "job_role": "Data Scientist",
        "company": "DataCorp",  # Same company
        "description": "Updated description",
        "locations": [{"city": "Melbourne", "state": "VIC"}],
        "source_urls": ["https://example.com/data2"],
        "platforms": ["prosple"],
        "salary": "$120k"  # Updated salary
    }
    
    result2 = db.upsert_job(job2)
    assert result2["status"] == "updated", f"Expected 'updated', got {result2['status']}"
    assert result2["id"] == job_id, "Should update same job"
    print(f"✓ Updated job via upsert: {result2}")
    
    # Verify merged and updated data
    updated_job = db.supabase.table("job_postings").select("*").eq("id", job_id).execute()
    job_data = updated_job.data[0]
    
    # Check mergeable fields
    assert len(job_data["locations"]) == 2, "Should have merged locations"
    assert len(job_data["source_urls"]) == 2, "Should have merged URLs"
    assert len(job_data["platforms"]) == 2, "Should have merged platforms"
    
    # Check scalar fields (should prefer new over existing)
    assert job_data["description"] == "Updated description", "Should update description"
    assert job_data["salary"] == "$120k", "Should update salary"
    
    print(f"✓ Merged locations: {job_data['locations']}")
    print(f"✓ Merged URLs: {job_data['source_urls']}")
    print(f"✓ Merged platforms: {job_data['platforms']}")
    print(f"✓ Updated description: {job_data['description']}")
    print(f"✓ Updated salary: {job_data['salary']}")
    
    # Cleanup
    db.supabase.table("job_postings").delete().eq("id", job_id).execute()
    print("✓ Test data cleaned up")
    
    print("\n" + "="*50)
    print("Upsert test passed! ✓")
    print("="*50)

if __name__ == "__main__":
    test_update_with_lists()
    test_upsert_uses_refactored_code()

import os
import sys
import time
from typing import List, Dict, Any

# Add project root to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobly.db.job_database import JobDatabase
from jobly.utils.scraper_utils import normalize_locations, extract_job_role

def migrate_data():
    print("Starting migration...")
    db = JobDatabase()
    
    # Fetch all jobs - using a large limit for now, or pagination if needed
    # Since get_all_jobs has a limit, we might need to implement pagination or just fetch a very large number
    # For this script, let's try to fetch all by using a large limit.
    # If the dataset is huge, we should use cursor-based pagination, but for now let's assume < 10000 jobs.
    
    page_size = 1000
    offset = 0
    total_processed = 0
    
    while True:
        print(f"Fetching jobs offset {offset}...")
        response = db.supabase.table("job_postings").select("*").range(offset, offset + page_size - 1).execute()
        jobs = response.data
        
        if not jobs:
            break
            
        updates = []
        for job in jobs:
            job_id = job.get("id")
            original_locations = job.get("locations", [])
            job_title = job.get("job_title", "")
            company = job.get("company", "")
            
            # Normalize locations
            # Ensure original_locations is a list
            if isinstance(original_locations, str):
                original_locations = [original_locations]
            elif original_locations is None:
                original_locations = []
                
            new_locations = normalize_locations(original_locations)
            
            # Extract job role
            job_role = extract_job_role(job_title, company)
            
            # Update the record
            # We can do individual updates or batch updates. 
            # Supabase-py doesn't support bulk update with different values easily in one call without rpc or complex query.
            # So we will update one by one for simplicity and reliability in this migration script.
            
            try:
                db.supabase.table("job_postings").update({
                    "locations_new": new_locations,
                    "job_role": job_role
                }).eq("id", job_id).execute()
                # print(f"Updated job {job_id}: Role='{job_role}', Locs={len(new_locations)}")
            except Exception as e:
                print(f"Error updating job {job_id}: {e}")
                
            total_processed += 1
            
            if total_processed % 50 == 0:
                print(f"Processed {total_processed} jobs...")
        
        offset += page_size
        
    print(f"Migration complete. Processed {total_processed} jobs.")

if __name__ == "__main__":
    migrate_data()

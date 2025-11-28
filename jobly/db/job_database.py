from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_database import BaseDatabase


class JobDatabase(BaseDatabase):
    @staticmethod
    def _generate_fingerprint(company: str, title: str) -> str:
        """Generates a simple fingerprint for deduplication."""
        # Normalize: lowercase, strip whitespace
        c = (company or "").lower().strip()
        t = (title or "").lower().strip()
        return f"{c}|{t}"

    def upsert_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Smart upsert: Checks for existing job by fingerprint.
        If exists -> Merges locations/platforms and updates.
        If new -> Inserts new record.
        """
        # 1. Generate Fingerprint
        print(f"DEBUG: job_data keys: {job_data.keys()}")
        print(f"DEBUG: description length: {len(job_data.get('description', ''))}")
        company = job_data.get("company", "")
        title = job_data.get("job_title", "") # Changed from title to job_title
        fingerprint = self._generate_fingerprint(company, title)
        
        # Prepare list fields (ensure they are lists)
        new_locs = job_data.get("locations", [])
        if isinstance(new_locs, str): new_locs = [new_locs]
        
        new_platforms = job_data.get("platforms", [])
        if isinstance(new_platforms, str): new_platforms = [new_platforms]
        
        new_urls = job_data.get("source_urls", [])
        if isinstance(new_urls, str): new_urls = [new_urls]
        
        # Handle legacy single fields if passed
        if "location" in job_data and not new_locs:
            new_locs = [job_data["location"]]
        if "platform" in job_data and not new_platforms:
            new_platforms = [job_data["platform"]]
        if "source_url" in job_data and not new_urls:
            new_urls = [job_data["source_url"]]

        # 2. Check for existing record
        existing = self.supabase.table("job_postings").select("*").eq("fingerprint", fingerprint).execute()
        
        if existing.data:
            # --- MERGE ---
            record = existing.data[0]
            record_id = record['id']
            
            # Merge lists and remove duplicates
            merged_locs = list(set(record.get('locations', []) + new_locs))
            merged_platforms = list(set(record.get('platforms', []) + new_platforms))
            merged_urls = list(set(record.get('source_urls', []) + new_urls))
            
            update_payload = {
                "locations": merged_locs,
                "platforms": merged_platforms,
                "source_urls": merged_urls,
                "updated_at": datetime.now().isoformat(),
                # Update other fields if the new one is "fresher" or just overwrite
                "description": job_data.get("description", record.get("description")),
                "salary": job_data.get("salary", record.get("salary")),
                "seniority": job_data.get("seniority", record.get("seniority"))
            }
            
            response = self.supabase.table("job_postings").update(update_payload).eq("id", record_id).execute()
            print(f"Merged duplicate job: {title} ({company})")
            return response.data[0]
            
        else:
            # --- INSERT ---
            insert_payload = {
                "fingerprint": fingerprint,
                "job_title": title,
                "company": company,
                "locations": new_locs,
                "platforms": new_platforms,
                "source_urls": new_urls,
                "description": job_data.get("description"),
                "salary": job_data.get("salary"),
                "seniority": job_data.get("seniority"),
                "llm_analysis": job_data.get("llm_analysis")
            }
            
            response = self.supabase.table("job_postings").insert(insert_payload).execute()
            print(f"Inserted new job: {title} ({company})")
            return response.data[0]

    def get_job_by_fingerprint(self, company: str, title: str) -> Optional[Dict[str, Any]]:
        """Retrieves a job by its fingerprint."""
        fp = self._generate_fingerprint(company, title)
        response = self.supabase.table("job_postings").select("*").eq("fingerprint", fp).execute()
        return response.data[0] if response.data else None

    def check_existing_urls(self, urls: List[str]) -> List[str]:
        """
        Checks a list of URLs and returns the ones that ALREADY exist in the database.
        """
        if not urls:
            return []
            
        # Supabase/PostgREST 'cs' operator means 'contains' for array columns.
        # However, we want to check if any of the rows have a source_url that matches one of our input urls.
        # Since source_urls is an array column in DB, and we have a list of URLs to check.
        
        # Efficient approach:
        # We want to find rows where source_urls && ARRAY[urls].
        # The 'overlaps' operator in PostgREST is 'ov'.
        
        try:
            # We can't easily pass a massive list to the query string if it's too long.
            # But for a page of results (20-30 items), it's fine.
            
            # Format for Postgres array literal: {url1,url2}
            # But the python client might handle list conversion.
            
            response = self.supabase.table("job_postings") \
                .select("source_urls") \
                .ov("source_urls", urls) \
                .execute()
                
            existing_urls = set()
            if response.data:
                for row in response.data:
                    # Each row has a list of source_urls.
                    # We check which of OUR input urls are in this row's list.
                    for db_url in row.get('source_urls', []):
                        if db_url in urls:
                            existing_urls.add(db_url)
                            
            return list(existing_urls)
            
        except Exception as e:
            print(f"Error checking existing URLs: {e}")
            return []

    def update_llm_analysis(self, job_id: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates the llm_analysis field for a specific job.
        """
        response = self.supabase.table("job_postings").update({"llm_analysis": analysis}).eq("id", job_id).execute()
        return response.data[0] if response.data else {}

    def get_all_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves the most recent jobs."""
        response = self.supabase.table("job_postings").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data

    # Placeholder for vector search
    def search_similar_jobs(self, embedding: List[float], threshold: float = 0.7, limit: int = 5):
        """
        Finds jobs with similar embeddings.
        Requires the 'match_documents' or similar RPC function to be set up in Supabase if using pgvector directly via RPC,
        or standard vector filtering if supported by the client library version.
        
        For now, this is a placeholder.
        """
        # Example RPC call if you set up a postgres function for vector search
        # response = self.supabase.rpc(
        #     "match_jobs", 
        #     {"query_embedding": embedding, "match_threshold": threshold, "match_count": limit}
        # ).execute()
        # return response.data
        pass

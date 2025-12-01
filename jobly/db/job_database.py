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
        # Use raw_job_title for fingerprint if available, otherwise use job_title
        title_for_fingerprint = job_data.get("raw_job_title") or job_data.get("job_title", "")
        title_for_display = job_data.get("job_title", "") # Cleaned title for display
        fingerprint = self._generate_fingerprint(company, title_for_fingerprint)
        
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

    def check_existing_urls(self, urls: List[str], only_complete: bool = False) -> List[str]:
        """
        Checks a list of URLs and returns the ones that ALREADY exist in the database.
        If only_complete is True, only returns URLs for jobs that have a non-null posted_at.
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
            
            query = self.supabase.table("job_postings") \
                .select("source_urls") \
                .ov("source_urls", urls)
            
            if only_complete:
                # If we only want "complete" jobs (i.e. those with posted_at),
                # then we filter for posted_at NOT being null.
                # If a job has posted_at as NULL, it won't be returned here,
                # so it won't be in 'existing_urls', so the scraper will treat it as new.
                query = query.neq("posted_at", "null")
                
            response = query.execute()
                
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

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_database import BaseDatabase
from ..utils.scraper_utils import normalize_locations, extract_job_role


class JobDatabase(BaseDatabase):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("JobDatabase")
    
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
        If exists -> Merges and updates. If new -> Inserts.
        """
        # 1. Generate fingerprint
        fingerprint = self._generate_fingerprint(
            job_data.get("company", ""),
            job_data.get("job_title", "")
        )
        
        # 2. Prepare data for insertion/update
        prepared_data = self._prepare_job_data(job_data)
        
        # 3. Check if job exists
        existing = self._find_by_fingerprint(fingerprint)
        
        if existing:
            return self._update_existing_job(existing, prepared_data, fingerprint)
        else:
            return self._insert_new_job(prepared_data, fingerprint)
    
    def _prepare_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and validate job data for database operations"""
        self.logger.debug(f"Preparing job data: {job_data.get('job_title')}")
        
        # Extract required fields
        prepared = {
            "job_title": job_data.get("job_title", ""),
            "job_role": job_data.get("job_role", "Other"),
            "company": job_data.get("company", ""),
            "description": job_data.get("description", ""),
        }
        
        # Prepare list fields (already normalized by scrapers)
        prepared["locations"] = self._prepare_list_field(
            job_data, "locations", "location"
        )
        prepared["platforms"] = self._prepare_list_field(
            job_data, "platforms", "platform"
        )
        prepared["source_urls"] = self._prepare_list_field(
            job_data, "source_urls", "source_url"
        )
        
        # Optional fields
        for field in ["salary", "seniority", "posted_at", "closing_date", "llm_analysis"]:
            prepared[field] = job_data.get(field)
        
        return prepared
    
    def _prepare_list_field(
        self, 
        data: dict, 
        plural_key: str, 
        singular_key: str
    ) -> list:
        """Prepare a list field, handling both plural and singular keys"""
        value = data.get(plural_key, [])
        
        # Convert string to list
        if isinstance(value, str):
            value = [value]
        
        # Handle legacy singular field
        if not value and singular_key in data:
            singular_value = data[singular_key]
            value = [singular_value] if isinstance(singular_value, str) else singular_value
        
        return value if isinstance(value, list) else [value]
    
    def _find_by_fingerprint(self, fingerprint: str) -> Optional[Dict]:
        """Find existing job by fingerprint"""
        try:
            result = self.supabase.table("job_postings") \
                .select("*") \
                .eq("fingerprint", fingerprint) \
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"Error finding job by fingerprint: {e}")
            return None
    
    def _update_existing_job(
        self, 
        existing: Dict, 
        new_data: Dict, 
        fingerprint: str
    ) -> Dict[str, Any]:
        """Merge new data with existing job and update"""
        self.logger.info(f"Updating existing job: {existing['id']}")
        
        # Merge list fields
        merged_data = {
            "locations": self._merge_locations(
                existing.get("locations", []),
                new_data["locations"]
            ),
            "platforms": self._merge_unique_values(
                existing.get("platforms", []),
                new_data["platforms"]
            ),
            "source_urls": self._merge_unique_values(
                existing.get("source_urls", []),
                new_data["source_urls"]
            ),
            "updated_at": datetime.now().isoformat(),
        }
        
        # Update scalar fields (prefer new over existing)
        for field in ["job_title", "job_role", "company", "description", 
                      "salary", "seniority", "posted_at", "closing_date"]:
            merged_data[field] = new_data[field] or existing.get(field)
        
        # Execute update
        self.supabase.table("job_postings") \
            .update(merged_data) \
            .eq("id", existing["id"]) \
            .execute()
        
        return {
            "id": existing["id"],
            "status": "updated",
            "fingerprint": fingerprint
        }
    
    def _insert_new_job(self, data: Dict, fingerprint: str) -> Dict[str, Any]:
        """Insert a new job posting"""
        self.logger.info(f"Inserting new job: {data['job_title']}")
        
        insert_data = {
            **data,
            "fingerprint": fingerprint,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        result = self.supabase.table("job_postings") \
            .insert(insert_data) \
            .execute()
        
        return {
            "id": result.data[0]["id"],
            "status": "inserted",
            "fingerprint": fingerprint
        }
    
    def _merge_locations(
        self, 
        current: List[Dict], 
        new: List[Dict]
    ) -> List[Dict]:
        """Merge location lists, removing duplicates based on city+state"""
        if not isinstance(current, list):
            current = []
        
        combined = current + new
        unique_locs = []
        seen = set()
        
        for loc in combined:
            key = (loc.get("city"), loc.get("state"))
            if key not in seen:
                seen.add(key)
                unique_locs.append(loc)
        
        return unique_locs
    
    def _merge_unique_values(self, current: List, new: List) -> List:
        """Merge two lists and remove duplicates"""
        return list(set(current + new))

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

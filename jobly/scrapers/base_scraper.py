import logging
from typing import List, Dict, Any, Optional
from jobly.db import JobDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class BaseScraper:
    def __init__(self, platform_name: str):
        self.platform = platform_name
        self.db = JobDatabase()
        self.logger = logging.getLogger(f"Scraper-{platform_name}")

    def save_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Saves a job to the database using the smart upsert logic.
        Automatically adds the platform to the job data.
        """
        try:
            # Ensure platform is set
            if "platforms" not in job_data:
                job_data["platforms"] = [self.platform]
            elif self.platform not in job_data["platforms"]:
                job_data["platforms"].append(self.platform)
                
            result = self.db.upsert_job(job_data)
            title = job_data.get('job_title') or job_data.get('title')
            self.logger.info(f"Saved job: {title} ({job_data.get('company')})")
            return result
        except Exception as e:
            self.logger.error(f"Failed to save job: {e}")
            return None

    def run(self):
        """Main entry point for the scraper."""
        raise NotImplementedError("Subclasses must implement run()")

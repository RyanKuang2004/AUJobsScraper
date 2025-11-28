"""
Run the job scraper workflow.

This script runs the Seek scraper to collect job postings.
"""

import logging
import sys

from jobly.scrapers import SeekScraper
from jobly.config import settings   

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RunScraper")


def main():
    """Main entry point for running the scraper."""
    logger.info("--- Starting Job Scraper ---")
    
    try:
        logger.info("Running Seek Scraper...")
        scraper = SeekScraper()
        scraper.run(initial_run=settings.scraper.initial_run)
        logger.info("Scraper completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

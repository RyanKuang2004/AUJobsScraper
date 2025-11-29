"""
Run the job scraper workflow.

This script runs job scrapers to collect job postings.
Supports multiple scraper platforms: seek, prosple, gradconnection.
"""

import argparse
import logging
import sys

from jobly.scrapers import SeekScraper
from jobly.scrapers.prosple_scraper import ProspleScraper
from jobly.scrapers.gradconnection_scraper import GradConnectionScraper
from jobly.config import settings   

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RunScraper")


# Scraper registry
SCRAPERS = {
    'seek': SeekScraper,
    'prosple': ProspleScraper,
    'gradconnection': GradConnectionScraper,
}


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Run job scraper to collect job postings from various platforms.'
    )
    parser.add_argument(
        '--scraper',
        type=str,
        choices=list(SCRAPERS.keys()),
        default='seek',
        help='Which scraper to run (default: seek)'
    )
    return parser.parse_args()


def main():
    """Main entry point for running the scraper."""
    args = parse_args()
    
    logger.info("--- Starting Job Scraper ---")
    logger.info(f"Platform: {args.scraper}")
    
    try:
        # Get the scraper class
        scraper_class = SCRAPERS[args.scraper]
        scraper = scraper_class()
        
        # Run the scraper
        logger.info(f"Running {args.scraper.capitalize()} Scraper...")
        scraper.run()
        logger.info("Scraper completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

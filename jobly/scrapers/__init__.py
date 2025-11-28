"""
Web scrapers module for job posting collection.
"""

from jobly.scrapers.base_scraper import BaseScraper
from jobly.scrapers.seek_scraper import SeekScraper

__all__ = ["BaseScraper", "SeekScraper"]

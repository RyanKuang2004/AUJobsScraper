"""AUJobsScraper — Australian job board scrapers."""

from aujobsscraper.models.job import JobPosting
from aujobsscraper.models.location import Location
from aujobsscraper.scrapers.seek_scraper import SeekScraper
from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper
from aujobsscraper.scrapers.prosple_scraper import ProspleScraper

__all__ = [
    "JobPosting",
    "Location",
    "SeekScraper",
    "GradConnectionScraper",
    "ProspleScraper",
]
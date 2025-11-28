"""
Jobly - Australian Job Market Scraper and Analyzer

A comprehensive job scraping and analysis tool for the Australian job market.
"""

__version__ = "0.1.0"
__author__ = "Ryan Kuang"

# Package-level exports for convenient imports
from jobly.db import JobDatabase, ConversationDatabase, BaseDatabase
from jobly.config import settings

__all__ = [
    "JobDatabase",
    "ConversationDatabase", 
    "BaseDatabase",
    "settings",
    "__version__",
]

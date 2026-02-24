# aujobsscraper/config.py
"""Scraper configuration that reads SCRAPER_* environment variables.

List values must be provided as JSON arrays, for example:
SCRAPER_SEARCH_KEYWORDS=["software engineer","data engineer"]

Consumers of this library are responsible for loading their own .env file
before importing, e.g. by calling dotenv.load_dotenv() in their application.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScraperSettings(BaseSettings):
    search_keywords: List[str] = Field(
        default=[
            "software engineer",
            "software developer",
            "data scientist",
            "machine learning engineer",
            "ai engineer",
            "data engineer",
        ],
    )
    gradconnection_keywords: List[str] = Field(
        default=[
            "software engineer",
            "software developer",
            "data science",
            "machine learning engineer",
            "ai engineer",
            "data analyst",
        ],
    )
    max_pages: int = Field(default=20)
    days_from_posted: int = Field(default=2)
    initial_days_from_posted: int = Field(default=31)
    initial_run: bool = Field(default=False)
    concurrency: int = Field(default=5)

    indeed_hours_old: int = Field(default=72)
    indeed_initial_hours_old: int = Field(default=2000)
    indeed_results_wanted: int = Field(default=20)
    indeed_results_wanted_total: int | None = Field(default=100)
    indeed_term_concurrency: int = Field(default=2)
    indeed_location: str = Field(default="")
    indeed_country: str = Field(default="Australia")

    prosple_items_per_page: int = Field(default=20)
    prosple_regular_max_pages: int = Field(default=3)

    model_config = SettingsConfigDict(env_prefix="SCRAPER_")


settings = ScraperSettings()

# aujobsscraper/config.py
"""Scraper configuration — reads SCRAPER_* environment variables."""

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


class ScraperSettings(BaseSettings):
    search_keywords: List[str] = Field(
        default=["software engineer", "software developer", "data scientist",
                 "machine learning engineer", "ai engineer", "data engineer"],
    )
    gradconnection_keywords: List[str] = Field(
        default=["software engineer", "software developer", "data science",
                 "machine learning engineer", "ai engineer", "data analyst"],
    )
    max_pages: int = Field(default=20)
    days_from_posted: int = Field(default=2)
    initial_days_from_posted: int = Field(default=31)
    initial_run: bool = Field(default=False)
    concurrency: int = Field(default=5)

    model_config = SettingsConfigDict(env_prefix="SCRAPER_")


load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)
settings = ScraperSettings()

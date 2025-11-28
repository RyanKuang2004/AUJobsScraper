"""
Configuration module for the Jobly application.
Uses Pydantic Settings for environment-based configuration.
"""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelSettings(BaseSettings):
    """LLM model configuration."""
    
    job_analyzer_model: str = Field(
        default="gpt-5-nano",
        description="OpenAI model for job analysis"
    )
    job_analyzer_temperature: float = Field(
        default=0.0,
        description="Temperature for job analyzer LLM"
    )
    
    model_config = SettingsConfigDict(env_prefix="MODEL_")


class ScraperSettings(BaseSettings):
    """Web scraper configuration."""
    
    search_keywords: List[str] = Field(
        default=[
            "machine learning",
            "data science",
            "artificial intelligence",
            "software developer"
        ],
        description="Job search keywords"
    )
    max_pages: int = Field(
        default=5,
        description="Maximum pages to scrape per keyword"
    )
    days_from_posted: int = Field(
        default=7,
        description="Number of days back to search for jobs"
    )
    initial_days_from_posted: int = Field(
        default=31,
        description="Number of days back for initial scrape"
    )
    
    model_config = SettingsConfigDict(env_prefix="SCRAPER_")


class ProcessorSettings(BaseSettings):
    """Job processor configuration."""
    
    batch_size: int = Field(
        default=10,
        description="Number of jobs to process in each batch"
    )
    
    model_config = SettingsConfigDict(env_prefix="PROCESSOR_")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: str = Field(default="development", description="Application environment")
    
    # Sub-configurations
    models: ModelSettings = Field(default_factory=ModelSettings)
    scraper: ScraperSettings = Field(default_factory=ScraperSettings)
    processor: ProcessorSettings = Field(default_factory=ProcessorSettings)
    
    # Supabase (loaded from environment)
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")
    
    # OpenAI (loaded from environment)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Singleton instance
settings = Settings()

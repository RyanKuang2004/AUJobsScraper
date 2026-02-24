# aujobsscraper/models/job.py
"""Job posting model — scraping fields only (no LLM extraction fields)"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from aujobsscraper.models.location import Location
from aujobsscraper.models.fingerprint import FingerprintGenerator


class JobPosting(BaseModel):
    """Job posting with only the fields a scraper can populate."""

    # Core identification
    job_title: str = Field(..., description="Original job title from posting")
    company: str = Field(..., description="Company name")
    description: str = Field(..., description="Full job description text")

    # Fingerprint (auto-generated)
    fingerprint: Optional[str] = Field(None, description="Unique fingerprint for deduplication")

    # Location and sources
    locations: List[Location] = Field(default_factory=list, description="Job locations")
    source_urls: List[str] = Field(default_factory=list, description="Source URLs for this job")
    platforms: List[str] = Field(default_factory=list, description="Platforms where job was found")

    # Optional scraping fields
    salary: Optional[Dict[str, float]] = Field(None, description="Structured salary info {annual_min, annual_max}")
    posted_at: Optional[str] = Field(None, description="Date posted (ISO format)")
    closing_date: Optional[str] = Field(None, description="Application closing date (ISO format)")

    class Config:
        frozen = False

    @model_validator(mode='after')
    def generate_fingerprint(self):
        if not self.fingerprint:
            job_data = {
                "company": self.company,
                "job_title": self.job_title,
                "locations": [{"city": loc.city, "state": loc.state} for loc in self.locations],
            }
            self.fingerprint = FingerprintGenerator.generate_from_job(job_data)
        return self

    def validate(self) -> List[str]:
        """Returns list of validation error messages. Empty list = valid."""
        errors = []
        if not self.locations:
            errors.append("Job must have at least one location")
        if not self.source_urls:
            errors.append("Job must have at least one source URL")
        if not self.platforms:
            errors.append("Job must have at least one platform")
        if not self.description or len(self.description.strip()) < 10:
            errors.append("Job description must be at least 10 characters")
        return errors

    def to_dict(self) -> dict:
        data = self.model_dump()
        data['locations'] = [
            {'city': loc.city, 'state': loc.state} if isinstance(loc, Location) else loc
            for loc in self.locations
        ]
        return data

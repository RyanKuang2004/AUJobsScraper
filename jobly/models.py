"""
Data models for job scraping system.

Provides strongly-typed dataclasses for job postings and locations,
replacing dictionary-based data passing with validated models.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Location:
    """Normalized location data"""
    city: str
    state: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for database storage"""
        return {"city": self.city, "state": self.state}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Location':
        """Create Location from dictionary"""
        return cls(city=data["city"], state=data["state"])


@dataclass
class JobPosting:
    """
    Complete job posting data model.
    
    Provides type safety, validation, and consistent data structure
    across all scrapers and database operations.
    """
    # Required fields
    job_title: str
    job_role: str
    company: str
    locations: List[Location]
    source_urls: List[str]
    platforms: List[str]
    description: str
    
    # Optional fields
    salary: Optional[str] = None
    seniority: Optional[str] = None
    posted_at: Optional[str] = None
    closing_date: Optional[str] = None
    llm_analysis: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion"""
        return {
            "job_title": self.job_title,
            "job_role": self.job_role,
            "company": self.company,
            "locations": [loc.to_dict() for loc in self.locations],
            "source_urls": self.source_urls,
            "platforms": self.platforms,
            "description": self.description,
            "salary": self.salary,
            "seniority": self.seniority,
            "posted_at": self.posted_at,
            "closing_date": self.closing_date,
            "llm_analysis": self.llm_analysis,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobPosting':
        """Create JobPosting from dictionary"""
        # Convert location dicts to Location objects
        locations = [
            Location.from_dict(loc) if isinstance(loc, dict) else loc 
            for loc in data.get("locations", [])
        ]
        
        return cls(
            job_title=data["job_title"],
            job_role=data["job_role"],
            company=data["company"],
            locations=locations,
            source_urls=data["source_urls"],
            platforms=data["platforms"],
            description=data["description"],
            salary=data.get("salary"),
            seniority=data.get("seniority"),
            posted_at=data.get("posted_at"),
            closing_date=data.get("closing_date"),
            llm_analysis=data.get("llm_analysis"),
        )
    
    def validate(self) -> List[str]:
        """
        Validate required fields and data quality.
        
        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors = []
        
        # Check required string fields
        if not self.job_title or self.job_title == "Unknown Title":
            errors.append("job_title is required and cannot be 'Unknown Title'")
        
        if not self.job_role:
            errors.append("job_role is required")
            
        if not self.company or self.company == "Unknown Company":
            errors.append("company is required and cannot be 'Unknown Company'")
        
        if not self.description or len(self.description.strip()) < 10:
            errors.append("description is required and must be at least 10 characters")
        
        # Check list fields
        if not self.locations:
            errors.append("locations cannot be empty")
        
        if not self.source_urls:
            errors.append("source_urls cannot be empty")
            
        if not self.platforms:
            errors.append("platforms cannot be empty")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the job posting is valid"""
        return len(self.validate()) == 0

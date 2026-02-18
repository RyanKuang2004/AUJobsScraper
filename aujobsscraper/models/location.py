# app/models/location.py
"""Location model for job postings"""

from pydantic import BaseModel, Field


class Location(BaseModel):
    """Location model representing Australian cities and states"""

    city: str = Field(..., description="City name")
    state: str = Field(..., description="Australian state/territory code (NSW, VIC, etc.)")

    class Config:
        frozen = False

    def __str__(self) -> str:
        return f"{self.city}, {self.state}"

    def __repr__(self) -> str:
        return f"Location(city='{self.city}', state='{self.state}')"

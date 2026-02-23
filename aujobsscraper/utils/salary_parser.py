from typing import Optional, Dict


class SalaryParser:
    """Extract salary information from job description text."""

    @staticmethod
    def extract_salary(description: str) -> Optional[Dict[str, float]]:
        """Extract salary from description and normalize to annual.

        Args:
            description: Job description text

        Returns:
            Dict with 'annual_min' and 'annual_max' floats, or None if not found
        """
        if not description or not isinstance(description, str):
            return None
        return None

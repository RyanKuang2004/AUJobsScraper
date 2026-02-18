# app/models/fingerprint.py
"""
Fingerprint generation for job deduplication.

Uses normalized hash approach: company + job_title 
"""

import hashlib
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FingerprintComponents:
    """Components used to generate a job fingerprint"""
    company: str
    job_title: str


class FingerprintGenerator:
    """Generate stable fingerprints for job deduplication"""

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for consistent fingerprinting.

        Rules:
        - Lowercase
        - Remove punctuation except spaces
        - Remove extra whitespace
        - Remove common suffixes (Pty Ltd, Inc, etc.)
        """
        if not text:
            return ""

        # Lowercase
        normalized = text.lower().strip()

        # Remove company suffixes
        suffixes = [
            r'\bpty\.?\s*ltd\.?',
            r'\blimited',
            r'\binc\.?',
            r'\bcorp\.?',
            r'\bllc\.?',
            r'\bco\.?',
        ]
        for suffix in suffixes:
            normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)

        # Remove punctuation except spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    @classmethod
    def generate(cls, components: FingerprintComponents) -> str:
        """
        Generate a fingerprint from components.

        The fingerprint is an MD5 hash of normalized components.

        Args:
            components: FingerprintComponents with job details

        Returns:
            Hex string fingerprint (32 characters)
        """
        # Normalize each component
        normalized_company = cls.normalize_text(components.company)
        normalized_title = cls.normalize_text(components.job_title)

        # Combine into fingerprint string
        fingerprint_parts = [
            normalized_company,
            normalized_title
        ]

        fingerprint_string = "|".join(fingerprint_parts)

        # Generate hash
        hash_obj = hashlib.md5(fingerprint_string.encode('utf-8'))
        return hash_obj.hexdigest()

    @classmethod
    def from_job_data(cls, job_data: Dict[str, Any]) -> FingerprintComponents:
        """
        Extract fingerprint components from job data dictionary.

        Args:
            job_data: Dictionary with job fields

        Returns:
            FingerprintComponents ready for fingerprint generation
        """
        company = job_data.get("company", "")
        job_title = job_data.get("job_title", "")

        return FingerprintComponents(
            company=company,
            job_title=job_title,
        )

    @classmethod
    def generate_from_job(cls, job_data: Dict[str, Any]) -> str:
        """
        Convenience method to generate fingerprint directly from job data.

        Args:
            job_data: Dictionary with job fields

        Returns:
            Hex string fingerprint
        """
        components = cls.from_job_data(job_data)
        return cls.generate(components)

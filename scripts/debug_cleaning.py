"""
Debug script to see what's happening with the cleaning logic
"""

from jobly.utils.scraper_utils import extract_job_role
import re

# Test cases that are failing
failing_cases = [
    "Software Engineer - AI/ML",
    "AI / Machine Learning Developer (Azure AI, Cop...",
    "Principal Software Engineer - AI.",
]

STOP_WORDS = {
    "internship", "intern", "grad", "program", "graduate", "graduate program",
    "phd", "masters", "start", "2025", "2026", "2024", "2027", "full-time", "full time",
    "part-time", "part time", "remote", "on-site", "onsite", "temporary", "contract",
    # Seniority-related terms to remove
    "senior", "junior", "lead", "entry", "entry level", "level", "principal",
    "head", "staff", "trainee"
}

def debug_cleaning(title):
    print(f"\nOriginal: {title}")
    
    # Step 1: lowercase
    cleaned = title.lower()
    print(f"After lowercase: {cleaned}")
    
    # Remove parentheses and content
    cleaned = re.sub(r'\([^)]*\)', ' ', cleaned)
    print(f"After removing parentheses: {cleaned}")
    
    # Remove year ranges and single years
    cleaned = re.sub(r'\b20\d{2}(?:[\s/-]*\d{2,4})?\b', ' ', cleaned)
    print(f"After removing years: {cleaned}")
    
    # Remove seniority and noise words
    for word in STOP_WORDS:
        before = cleaned
        cleaned = re.sub(rf'\b{re.escape(word)}\b', ' ', cleaned)
        if before != cleaned:
            print(f"After removing '{word}': {cleaned}")
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    print(f"After whitespace normalization: {cleaned}")
    
    # Now test classification
    result = extract_job_role(title)
    print(f"Final classification: {result}")

for case in failing_cases:
    debug_cleaning(case)
    print("-" * 80)

"""
Shared utility functions for web scraping.

This module contains pure helper functions used across multiple scrapers
for common tasks like HTML parsing, text processing, and data extraction.
"""

import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


def remove_html_tags(content: str) -> str:
    """
    Remove HTML tags from content and return plain text.
    
    Args:
        content: HTML content as a string
        
    Returns:
        Plain text with HTML tags removed
    """
    if not content:
        return ""
    soup = BeautifulSoup(content, 'lxml')
    return soup.get_text(separator="\n", strip=True)


def extract_salary_from_text(text: str) -> str | None:
    """
    Extract salary information from text using regex patterns.
    
    Supports various salary formats including:
    - $50,000 - $60,000
    - $100k - $120k
    - 50k - 60k
    - $50k
    
    Args:
        text: Text to search for salary information
        
    Returns:
        Extracted salary string or None if not found
    """
    if not text:
        return None
    
    # Regex patterns for common salary formats
    salary_patterns = [
        r'\$\d{1,3}(?:,\d{3})*k?(?:\s*-\s*\$\d{1,3}(?:,\d{3})*k?)?',  # $100k - $120k, $50,000 - $60,000
        r'\d{2,3}k\s*-\s*\d{2,3}k',  # 50k - 60k
        r'\$\d{2,3}k', # $50k
    ]
    
    # Look for lines containing salary-related keywords
    lines = text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ['salary', 'remuneration', 'package', 'compensation']):
            # Try to find a number pattern in this line
            for pattern in salary_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(0)
    
    return None


def calculate_posted_date(text: str) -> str:
    """
    Calculate the posting date from relative time text.
    
    Parses text like "Posted 2d ago" and calculates the actual date.
    Handles days (d), hours (h), and minutes (m) formats.
    
    Args:
        text: Relative time text (e.g., "Posted 2d ago", "Posted 30+d ago")
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    try:
        # Clean text: "Posted 2d ago" -> "2d"
        clean_text = text.replace("Posted", "").replace("ago", "").strip().lower()
        
        days_ago = 0
        if "d" in clean_text:
            # Handle "30+d" case
            clean_text = clean_text.replace("+", "")
            days_ago = int(clean_text.replace("d", ""))
        elif "h" in clean_text or "m" in clean_text:
            # Hours or minutes ago = today
            days_ago = 0
            
        posted_date = datetime.now() - timedelta(days=days_ago)
        return posted_date.strftime("%Y-%m-%d")
    except Exception:
        # Default to today if parsing fails
        return datetime.now().strftime("%Y-%m-%d")


def determine_seniority(title: str) -> str:
    """
    Determine the seniority level from a job title.
    
    Analyzes keywords in the job title to classify the seniority level.
    
    Args:
        title: Job title string
        
    Returns:
        One of: "Senior", "Junior", "Intermediate", or "N/A"
    """
    text = title.lower().strip()

    # Pre-cleaning
    text = re.sub(r"[^a-z0-9+ ]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    patterns = {
        "Senior": [
            r"\bsenior\b",
            r"\blead\b",
            r"\bprincipal\b",
            r"\bmanager\b",
            r"\bhead\b",
            r"\bstaff\b",
        ],
        "Junior": [
            r"\bjunior\b",
            r"\bgraduate\b",
            r"\bentry\b",
            r"\bentry level\b",
            r"\bintern\b",
            r"\binternship\b",
            r"\btrainee\b",
        ],
        "Intermediate": [
            r"\bintermediate\b",
            r"\bmid\b",
            r"\bmid level\b",
            r"\bmid-level\b",
        ],
    }

    for level, regex_list in patterns.items():
        for pattern in regex_list:
            if re.search(pattern, text):
                return level

    return "N/A"

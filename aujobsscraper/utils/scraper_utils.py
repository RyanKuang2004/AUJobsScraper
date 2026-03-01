"""
Shared utility functions for web scraping.

This module contains pure helper functions used across multiple scrapers
for common tasks like HTML parsing, text processing, and data extraction.
"""

import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Import all constants from the constants module
from .constants import (
    CITY_TO_STATE,
    STATE_NAMES,
    NON_CITY_PATTERNS,
    AUSTRALIAN_STATES
)


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

def normalize_salary(raw_text: str):
    if not raw_text:
        return None

    # 1. Lowercase and basic cleanup
    text = raw_text.lower().replace(',', '')
    
    # 2. Identify Time Unit
    multiplier = 1
    if any(x in text for x in ['hour', 'hr', '/hr', 'ph']):
        multiplier = 2080
    elif any(x in text for x in ['month', 'mo', '/mo']):
        multiplier = 12
    elif any(x in text for x in ['week', 'wk']):
        multiplier = 52
    elif any(x in text for x in ['day', 'daily']):
        multiplier = 260
    
    # 3. Extract numbers using Regex
    # Matches numbers like 50, 50.5, 50k, 50000
    matches = re.findall(r'(\d+\.?\d*)(k?)', text)
    
    if not matches:
        return None

    # Convert matches to pure floats
    values = []
    for num, suffix in matches:
        val = float(num)
        if suffix == 'k':
            val *= 1000
        values.append(val)
    
    # 4. Handle "80-100k" context logic
    # If we have 2 numbers, and the 2nd is thousands but 1st is small
    if len(values) == 2:
        if values[1] > 1000 and values[0] < 1000:
            values[0] *= 1000

    # 5. Calculate Annual Min/Max
    min_sal = min(values) * multiplier
    max_sal = max(values) * multiplier
    
    # 6. Sanity Check (Remove extreme outliers caused by parsing errors)
    # e.g., If annual salary < $10k or > $1M, flag for manual review or discard
    if min_sal < 10000 or min_sal > 1000000:
        return None

    return {
        "annual_min": min_sal,
        "annual_max": max_sal,
    }


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
        day_match = re.search(r"(\d+)\+?d", clean_text)
        if day_match:
            days_ago = int(day_match.group(1))
        elif "h" in clean_text or "m" in clean_text:
            # Hours or minutes ago = today
            days_ago = 0
            
        posted_date = datetime.now() - timedelta(days=days_ago)
        return posted_date.strftime("%Y-%m-%d")
    except Exception:
        # Default to today if parsing fails
        return datetime.now().strftime("%Y-%m-%d")



def normalize_locations(locations: list[str]) -> list[dict[str, str]]:
    """
    Normalize location strings into structured city/state dictionaries.
    
    Converts location strings into structured format with Australian city-to-state mapping.
    Filters out states, regions, and suburbs to return only main cities.
    
    Examples:
    - "Fortitude Valley, Brisbane QLD" -> {"city": "Brisbane", "state": "QLD"}
    - "Sydney" -> {"city": "Sydney", "state": "NSW"}
    - "Melbourne CBD and Inner Suburbs" -> {"city": "Melbourne", "state": "VIC"}
    - "New South Wales" -> (filtered out, not a city)
    
    Args:
        locations: List of location strings to normalize
        
    Returns:
        List of dictionaries with "city" and "state" keys, containing only valid cities
    """
    if not locations:
        return []
    
    # Australian state/territory abbreviations
    state_pattern = '|'.join(AUSTRALIAN_STATES)
    
    normalized = []
    
    for location in locations:
        if not location or not isinstance(location, str):
            continue
            
        # Clean the location string
        location = location.strip()
        location_lower = location.lower()

        # Special case: "Australia" or "AU" - preserve as country-level location
        if location_lower in ('australia', 'au'):
            normalized.append({"city": "Australia", "state": ""})
            continue

        # Skip if it's a state name (but not "Australia" which we handled above)
        if location_lower in STATE_NAMES:
            continue
        
        # Skip if it matches non-city patterns
        skip = False
        for pattern in NON_CITY_PATTERNS:
            if re.search(pattern, location_lower):
                skip = True
                break
        if skip:
            continue
        
        city = None
        state = None
        
        # Try to extract state abbreviation from the location string
        state_match = re.search(rf'\b({state_pattern})\b', location, re.IGNORECASE)
        
        if state_match:
            state = state_match.group(1).upper()
            
            # Extract city name - look for the main city before the state
            # Pattern: "Suburb, City STATE" or "City STATE"
            location_before_state = location[:state_match.start()].strip()
            
            # Remove trailing comma if present
            location_before_state = location_before_state.rstrip(',').strip()
            
            # If there's a comma, take the part after the last comma (the main city)
            # e.g., "Fortitude Valley, Brisbane" -> "Brisbane"
            if ',' in location_before_state:
                parts = [p.strip() for p in location_before_state.split(',')]
                # Take the last part as the main city
                city_candidate = parts[-1]
            else:
                # No comma, the whole string before state is the city
                city_candidate = location_before_state
            
            # Verify this is actually a known city
            if city_candidate.lower() in CITY_TO_STATE:
                city = city_candidate.title()
            else:
                # Not in our known cities, but we have a state - use empty city
                city = ""
        else:
            # No state abbreviation found, try to identify city from the string
            # Remove common prefixes and check if it's a known city
            
            # First, try to extract city from comma-separated parts
            if ',' in location:
                parts = [p.strip() for p in location.split(',')]
                # Try each part to see if it's a known city
                for part in reversed(parts):  # Start from the end
                    if part.lower() in CITY_TO_STATE:
                        city = part.title()
                        state = CITY_TO_STATE[part.lower()]
                        break
            else:
                # Check if the whole location is a known city
                if location_lower in CITY_TO_STATE:
                    city = location.title()
                    state = CITY_TO_STATE[location_lower]
        
        # Only add valid city entries (city is required, state is optional for country-level locations like "Australia")
        if city:
            normalized.append({
                "city": city,
                "state": state or ""  # Ensure state is never None
            })
    
    # Remove duplicates while preserving order
    seen = set()
    unique_normalized = []
    for loc in normalized:
        # Create a tuple for hashability
        loc_tuple = (loc.get("city"), loc.get("state"))
        if loc_tuple not in seen:
            seen.add(loc_tuple)
            unique_normalized.append(loc)
    
    return unique_normalized


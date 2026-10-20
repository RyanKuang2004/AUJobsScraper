"""
Shared utility functions for web scraping.

This module contains pure helper functions used across multiple scrapers
for common tasks like HTML parsing, text processing, and data extraction.
"""

import re
from bs4 import BeautifulSoup
from typing import Literal

from . import posted_time

# Import all constants from the constants module
from .constants import (
    CITY_TO_STATE,
    STATE_NAMES,
    NON_CITY_PATTERNS,
    AUSTRALIAN_STATES,
    NZ_CITY_TO_REGION,
    NZ_REGION_NAMES,
)

_COUNTRY_CONFIG = {
    "AU": {
        "city_to_state": CITY_TO_STATE,
        "state_names": STATE_NAMES,
        "state_abbrevs": AUSTRALIAN_STATES,
        "country_names": {"australia", "au"},
        "country_label": "Australia",
    },
    "NZ": {
        "city_to_state": NZ_CITY_TO_REGION,
        "state_names": NZ_REGION_NAMES,
        "state_abbrevs": [],
        "country_names": {"new zealand", "nz"},
        "country_label": "New Zealand",
    },
}


def remove_html_tags(content: str) -> str:
    """
    Convert HTML content into lightweight Markdown text.
    
    Args:
        content: HTML content as a string
        
    Returns:
        Markdown-like text with basic structure preserved
    """
    if not content:
        return ""

    soup = BeautifulSoup(content, 'lxml')

    # Convert headings into Markdown headings.
    for level in range(1, 7):
        for tag in soup.find_all(f"h{level}"):
            text = tag.get_text(" ", strip=True)
            if text:
                tag.replace_with(f"\n{'#' * level} {text}\n")
            else:
                tag.decompose()

    # Treat bold/strong labels as section headings.
    for tag in soup.find_all(["strong", "b"]):
        text = tag.get_text(" ", strip=True)
        if text:
            tag.replace_with(f"\n## {text}\n")
        else:
            tag.decompose()

    # Convert list items into Markdown bullet/numbered lines.
    for list_tag in soup.find_all(["ul", "ol"]):
        ordered = list_tag.name == "ol"
        lines = []
        for idx, item in enumerate(list_tag.find_all("li", recursive=False), start=1):
            text = item.get_text(" ", strip=True)
            if not text:
                continue
            marker = f"{idx}. " if ordered else "- "
            lines.append(f"{marker}{text}")
        replacement = "\n" + "\n".join(lines) + "\n" if lines else ""
        list_tag.replace_with(replacement)

    # Ensure paragraphs become separate lines.
    for tag in soup.find_all("p"):
        text = tag.get_text(" ", strip=True)
        if text:
            tag.replace_with(f"{text}\n")
        else:
            tag.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.rstrip() for line in text.splitlines()]

    # Keep at most one consecutive blank line.
    cleaned_lines = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        cleaned_lines.append(line)
        previous_blank = is_blank

    return "\n".join(cleaned_lines).strip()


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


def calculate_posted_date(text: str) -> str | None:
    """
    Calculate the posting date from relative time text.

    Parses text like "Posted 2d ago" and returns the Melbourne-local date.
    Kept for callers that only need the date; see posted_time.from_relative
    for the timestamp and precision.

    Args:
        text: Relative time text (e.g., "Posted 2d ago", "Posted 30+d ago")

    Returns:
        Date string in YYYY-MM-DD format, or None if the text can't be parsed
    """
    return posted_time.from_relative(text).date


def normalize_locations(
    locations: list[str], country: Literal["AU", "NZ"] = "AU"
) -> list[dict[str, str]]:
    """
    Normalize location strings into structured city/state dictionaries.

    Converts location strings into structured format with a country-specific
    city-to-state (AU) or city-to-region (NZ) mapping. Filters out states,
    regions, and suburbs to return only main cities.

    Examples:
    - "Fortitude Valley, Brisbane QLD" -> {"city": "Brisbane", "state": "QLD"}
    - "Sydney" -> {"city": "Sydney", "state": "NSW"}
    - "Auckland CBD, Auckland" (country="NZ") -> {"city": "Auckland", "state": "Auckland"}
    - "New South Wales" -> (filtered out, not a city)

    Args:
        locations: List of location strings to normalize
        country: Which country's city/region tables to use ("AU" or "NZ")

    Returns:
        List of dictionaries with "city" and "state" keys, containing only valid cities
    """
    if not locations:
        return []

    cfg = _COUNTRY_CONFIG[country]
    city_to_state = cfg["city_to_state"]
    state_names = cfg["state_names"]
    state_abbrevs = cfg["state_abbrevs"]
    country_names = cfg["country_names"]
    country_label = cfg["country_label"]

    state_pattern = '|'.join(state_abbrevs) if state_abbrevs else None

    normalized = []

    for location in locations:
        if not location or not isinstance(location, str):
            continue

        # Clean the location string. Strip a trailing work-mode annotation
        # (e.g. "Auckland (Hybrid)", "Waikato (Remote)") - common on Seek NZ
        # listings - so it doesn't break exact-match city/region lookups.
        location = location.strip()
        location = re.sub(r'\s*\([^)]*\)\s*$', '', location).strip()
        location_lower = location.lower()

        # Special case: country name - preserve as country-level location
        if location_lower in country_names:
            normalized.append({"city": country_label, "state": ""})
            continue

        # Skip if it's a state/region name (but not the country name, handled above)
        if location_lower in state_names:
            continue

        # Skip if it matches non-city patterns (e.g., "Greater X", "Inner Suburbs")
        skip = False
        for pattern in NON_CITY_PATTERNS:
            if re.search(pattern, location_lower):
                skip = True
                break
        if skip:
            continue

        city = None
        state = None

        # Try to extract a state/region abbreviation from the location string
        # (NZ has no such abbreviations in postings, so state_pattern is None
        # and this always falls through to the city-lookup branch below)
        state_match = None
        if state_pattern:
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
            if city_candidate.lower() in city_to_state:
                city = city_candidate.title()
            else:
                # Not in our known cities, but we have a state - use empty city
                city = ""
        else:
            # No state/region abbreviation found, try to identify city from the string

            # First, try to extract city from comma-separated parts
            if ',' in location:
                parts = [p.strip() for p in location.split(',')]
                # Try each part to see if it's a known city
                for part in reversed(parts):  # Start from the end
                    if part.lower() in city_to_state:
                        city = part.title()
                        state = city_to_state[part.lower()]
                        break
            else:
                # Check if the whole location is a known city
                if location_lower in city_to_state:
                    city = location.title()
                    state = city_to_state[location_lower]

        # Only add valid city entries (city is required, state is optional for country-level locations)
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


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
    STOP_WORDS,
    ROLE_SUFFIXES,
    ROLE_TAXONOMY,
    CITY_TO_STATE,
    STATE_NAMES,
    NON_CITY_PATTERNS,
    AUSTRALIAN_STATES
)

def _clean_text(raw: str) -> str:
    text = raw.lower()
    # remove parentheses and content inside
    text = re.sub(r'\([^)]*\)', ' ', text)
    # remove years ranges like 2025-2026, 2025/26 or single years like 2025
    text = re.sub(r'\b20\d{2}(?:[\s/-]*\d{2,4})?\b', ' ', text)
    # replace punctuation that splits phrases with consistent separators
    # NOTE: preserve forward slashes (/) for cases like "ai/ml"
    text = re.sub(r'[_\|,;]+', ' - ', text)
    # remove stop words as standalone tokens
    for w in STOP_WORDS:
        text = re.sub(rf'\b{re.escape(w)}\b', ' ', text)
    # collapse multiple separators/spaces
    text = re.sub(r'[-–—]+', ' - ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _collapse_repeated_subphrases(text: str) -> str:
    """
    Collapse repeated words/phrases separated by dash/comma, e.g.
    "software engineering - engineering" -> "software engineering"
    Also removes phrases that are substrings of other phrases.
    """
    parts = [p.strip() for p in re.split(r'[-,]', text) if p.strip()]
    # collapse repeats (keep order) and remove substrings
    seen = []
    for p in parts:
        # Check if this part is already a substring of any existing part
        is_substring = any(p in existing or existing in p for existing in seen)
        if not is_substring:
            seen.append(p)
        elif any(p in existing for existing in seen):
            # p is substring of existing, skip it
            continue
        else:
            # existing is substring of p, replace it
            seen = [p if p in existing or existing in p else existing for existing in seen]
    return ' - '.join(seen)

def _normalize_engineering_word(phrase: str) -> str:
    # map 'software engineering' -> 'software engineer'
    phrase = re.sub(r'\bengineering\b', 'engineer', phrase)
    # remove residual words like 'role' or trailing separators
    phrase = re.sub(r'\b(role|position)\b', '', phrase)
    phrase = re.sub(r'\s+', ' ', phrase).strip()
    return phrase

# Lazy load OpenAI embeddings to avoid startup cost
_embedding_model = None
_role_embeddings = None


def _get_embedding_model():
    """Lazy load the OpenAI embeddings model."""
    global _embedding_model, _role_embeddings
    if _embedding_model is None:
        from langchain_openai import OpenAIEmbeddings
        _embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
        # Pre-compute embeddings for all standard roles
        _role_embeddings = _embedding_model.embed_documents(list(ROLE_TAXONOMY.keys()))
    return _embedding_model, _role_embeddings


def extract_job_role(title: str, company_name: str = None, similarity_threshold: float = 0.5) -> str:
    """
    Classify job title into standardized roles using hybrid approach:
    1. Check for early-match patterns (e.g., Graduate Program) before stop word removal
    2. Clean the title (remove company name, seniority terms, noise)
    3. Try keyword matching against taxonomy
    4. Fall back to embedding similarity if no keyword match
    5. Return "Specialized" if similarity is below threshold
    
    Args:
        title: Raw job title
        company_name: Optional company name to remove from title
        similarity_threshold: Minimum similarity score for embedding match (default 0.4)
        
    Returns:
        Standardized job role name or "Specialized"
    """
    if not title:
        return "Specialized"
    
    # Step 0: Early pattern matching for roles that would be affected by stop word removal
    # This catches patterns like "Graduate Program", "Internship Program", etc. BEFORE
    # stop words like "graduate", "program", "intern" are removed
    # BUT only when there's no specific role mentioned (e.g., "Data Science Graduate Program" should extract "Data Scientist")
    title_lower = title.lower()
    
    # Check if title contains "graduate program" or "internship program"
    has_graduate_program = bool(re.search(r'\b(graduate|grad)\s+(program|programme|development\s+programme)\b', title_lower))
    has_internship_program = bool(re.search(r'\b(internship|intern)\s+(program|programme)\b', title_lower))
    
    if has_graduate_program or has_internship_program:
        # Check if there's a specific role keyword in the title
        # Look for role-related words that indicate a specific discipline
        role_indicators = [
            # Technical roles
            'data', 'software', 'cyber', 'security', 'cloud', 'devops',
            'engineer', 'developer', 'analyst', 'scientist', 'architect',
            # Specific technologies/domains
            'machine learning', 'artificial intelligence', 'ai', 'ml',
            'frontend', 'backend', 'full stack', 'fullstack',
            'mobile', 'web', 'ios', 'android',
            'qa', 'test', 'automation',
            # Business/management
            'business', 'product', 'project', 'consulting'
        ]
        
        has_specific_role = False
        for indicator in role_indicators:
            if indicator in title_lower:
                has_specific_role = True
                break
        
        # Only classify as Graduate Program if no specific role was found
        if not has_specific_role:
            return "Graduate Program"
    
    # Step 1: Clean the title
    cleaned = title.lower()
    
    # Remove company name if provided
    if company_name:
        cleaned = re.sub(rf'\b{re.escape(company_name.lower())}\b', ' ', cleaned)
    
    # Remove parentheses and content
    cleaned = re.sub(r'\([^)]*\)', ' ', cleaned)
    
    # Remove year ranges and single years
    cleaned = re.sub(r'\b20\d{2}(?:[\s/-]*\d{2,4})?\b', ' ', cleaned)
    
    # Remove seniority and noise words
    for word in STOP_WORDS:
        cleaned = re.sub(rf'\b{re.escape(word)}\b', ' ', cleaned)
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    if not cleaned:
        return "Specialized"
    
    # Step 2: Keyword matching with category priority
    # Categories are ordered by priority in ROLE_TAXONOMY (AI/ML first, Software Engineer later)
    # For each category, check if ANY keyword matches. If yes, pick the longest match in that category.
    # This ensures higher-priority categories (AI/ML) are checked before lower-priority ones (Software Engineer)
    
    for role, keywords in ROLE_TAXONOMY.items():
        # Find all matching keywords for this role category
        matches = [(kw, len(kw)) for kw in keywords if kw in cleaned]
        
        if matches:
            # Pick the longest keyword match within this category
            best_keyword = max(matches, key=lambda x: x[1])[0]
            return role

    
    # Step 3: Embedding fallback
    try:
        model, role_embeddings = _get_embedding_model()
        
        # Encode the cleaned title
        title_embedding = model.embed_query(cleaned)
        
        # Compute cosine similarity with all standard roles using numpy
        import numpy as np
        
        # Normalize vectors for cosine similarity
        title_norm = np.array(title_embedding) / np.linalg.norm(title_embedding)
        
        similarities = []
        for role_emb in role_embeddings:
            role_norm = np.array(role_emb) / np.linalg.norm(role_emb)
            similarity = np.dot(title_norm, role_norm)
            similarities.append(similarity)
        
        # Find best match
        max_sim_idx = np.argmax(similarities)
        max_similarity = similarities[max_sim_idx]
        
        if max_similarity >= similarity_threshold:
            return list(ROLE_TAXONOMY.keys())[max_sim_idx]
        else:
            return "Specialized"
            
    except Exception as e:
        # If embedding fails, return Specialized
        return "Specialized"


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


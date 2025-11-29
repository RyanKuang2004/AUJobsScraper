"""
Shared utility functions for web scraping.

This module contains pure helper functions used across multiple scrapers
for common tasks like HTML parsing, text processing, and data extraction.
"""

import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import spacy

import re
import spacy

nlp = spacy.load("en_core_web_sm")

# stop / noise words to strip early (including seniority terms)
STOP_WORDS = {
    "internship", "intern", "grad", "program", "graduate", "graduate program",
    "phd", "masters", "start", "2025", "2026", "2024", "2027", "full-time", "full time",
    "part-time", "part time", "remote", "on-site", "onsite", "temporary", "contract",
    # Seniority-related terms to remove
    "senior", "junior", "lead", "entry", "entry level", "level", "principal",
    "head", "staff", "trainee"
}

# Useful suffixes we want to detect (multi-word ones first)
ROLE_SUFFIXES = [
    "test automation engineer",
    "machine learning engineer",
    "software engineer",
    "electrical engineer",
    "civil engineer",
    "automation engineer",
    "test engineer",
    "data scientist",
    "data engineer",
    "software developer",
    "research scientist",
    "systems engineer",
    "hardware engineer",
    "design engineer",
    "engineer",
    "developer",
    "scientist",
    "analyst",
    "architect",
    "designer",
    "administrator",
    "specialist",
    "consultant",
    "technician",
    "coordinator",
    "manager",
]

# ensure longest-first matching
ROLE_SUFFIXES = sorted(ROLE_SUFFIXES, key=lambda s: -len(s))

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

def extract_job_role(title: str) -> str:
    """
    Fast role extractor:
      1) clean the raw text
      2) try regex expansion around known ROLE_SUFFIXES (longest-first)
      3) choose longest/specific candidate
      4) fallback to spaCy noun chunks
    Returns title-cased role or cleaned text if nothing found.
    """
    raw = title or ""
    text = _clean_text(raw)
    text = _collapse_repeated_subphrases(text)

    candidates = []

    # For each suffix try to find occurrences and expand left up to 4 words
    for suffix in ROLE_SUFFIXES:
        # find all occurrences of the suffix
        for m in re.finditer(re.escape(suffix), text):
            start = m.start()
            # expand left to capture up to 4 words before the suffix (to get modifiers)
            left = text[:start].rstrip()
            # take last up to 4 words from left
            left_words = re.findall(r'\b[\w&/+-]+\b', left)
            if left_words:
                # Filter out likely company names (short acronyms) and location words
                filtered_words = []
                for word in left_words[-4:]:
                    # Skip single letters, short acronyms (2-4 chars, all same case)
                    if len(word) <= 4 and (word.isupper() or word.islower()) and word.isalpha():
                        # Likely a company acronym or short word, skip unless it's part of role
                        # Keep common role modifiers like "ai", "ml", "qa", "it"
                        if word.lower() not in {'ai', 'ml', 'qa', 'it', 'ui', 'ux', 'bi', 'ci', 'cd'}:
                            continue
                    filtered_words.append(word)
                
                if filtered_words:
                    prefix = " ".join(filtered_words)
                    candidate = (prefix + " " + suffix).strip()
                else:
                    candidate = suffix
            else:
                candidate = suffix
            # cleanup candidate
            candidate = re.sub(r'\s+', ' ', candidate).strip()
            candidate = _normalize_engineering_word(candidate)
            # discard garbage candidates that are too short/generic like just "engineering"
            if candidate.lower() in {"engineering", ""}:
                continue
            candidates.append(candidate)

    # If we found any candidates, pick the longest (most specific), then title-case
    if candidates:
        best = max(candidates, key=lambda s: len(s))
        return best.title()

    # fallback: use spaCy noun chunks but filter to chunks that contain a role-like suffix
    doc = nlp(text)
    chunk_candidates = []
    for chunk in doc.noun_chunks:
        c = chunk.text.strip()
        # discard overly generic single words like "engineering"
        if c.lower() in {"engineering", ""}:
            continue
        # choose chunks containing any role suffix or any of the suffix words
        if any(suf in c.lower() for suf in ROLE_SUFFIXES):
            c = _normalize_engineering_word(c)
            chunk_candidates.append(c)

    if chunk_candidates:
        best = max(chunk_candidates, key=lambda s: len(s))
        return best.title()

    # final fallback: last meaningful token(s)
    tokens = [t.text for t in doc if not t.is_stop and t.is_alpha]
    if tokens:
        out = " ".join(tokens[-3:]).title()
        return out

    # as last resort return cleaned, title-cased original
    return _normalize_engineering_word(text).title()

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


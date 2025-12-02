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

# Lazy load OpenAI embeddings to avoid startup cost
_embedding_model = None
_role_embeddings = None

# Job role taxonomy mapping standard roles to keywords
# IMPORTANT: Order matters! More specific roles are checked first to avoid misclassification.
# AI/ML and specialized roles appear before generic "Software Engineer" category.
ROLE_TAXONOMY = {
    # ========================================
    # AI & ML (HIGHEST PRIORITY - Most Specific)
    # ========================================
    "AI Engineer": [
        # Combined AI/ML terminology - should classify as AI Engineer per user requirement
        "ai/ml engineer", "ai ml engineer", "ai / ml", "ai/ml", "ai & ml",
        # AI-focused roles
        "ai engineer", "ai software engineer", "ai developer", "ai software developer", 
        "ai programmer", "artificial intelligence engineer",
        # Generative AI
        "generative ai", "genai engineer", "gen ai", "generative ai engineer",
        # AI Platform/Infrastructure
        "ai platform engineer", "ai devops", "ai infrastructure",
        # General AI
        "artificial intelligence",
    ],
    "Machine Learning Engineer": [
        "machine learning engineer", "ml engineer", "machine learning developer", "ml developer",
        "mlops engineer", "mlops", "deep learning engineer", "ml software engineer",
    ],
    "NLP Engineer": [
        "nlp engineer", "natural language processing", "conversational ai", 
        "prompt engineer", "llm engineer", "large language model",
    ],
    "Research Scientist": [
        "research scientist", "computer scientist", "applied scientist",
        "research fellow", "computational science", "research assistant",
    ],
    
    # ========================================
    # Data & Analytics (High Priority - Specific)
    # ========================================
    "Data Scientist": ["data scientist", "applied scientist", "spatial data scientist"],
    "Data Engineer": ["data engineer", "big data", "etl developer", "azure data engineer", "data pipeline"],
    "Data Analyst": ["data analyst", "reporting analyst", "insights analyst", "commercial analyst"],
    "Business Intelligence Analyst": ["business intelligence", "bi analyst", "bi developer", "power bi", "tableau", "analytics"],
    "Data Architect": ["data architect", "data modeler", "database architect"],
    "Database Administrator": ["database administrator", "database developer", "sql developer", "dba"],
    
    # ========================================
    # Infrastructure, Cloud & DevOps (Medium-High Priority)
    # ========================================
    "DevOps Engineer": ["devops engineer", "site reliability engineer", "sre", "ci/cd engineer", "devsecops"],
    "Cloud Engineer": ["cloud engineer", "azure engineer", "aws engineer", "cloud architect", "solutions engineer", "gcp engineer"],
    "Platform Engineer": ["platform engineer", "infrastructure engineer", "systems engineer"],
    "Systems Administrator": ["systems administrator", "it support", "application support", "service desk", "sysadmin"],
    
    # ========================================
    # Security (Medium Priority)
    # ========================================
    "Cyber Security Engineer": ["cyber security", "security analyst", "infosec", "detection engineer", "security engineer", "cybersecurity"],
    
    # ========================================
    # QA & Testing (Medium Priority)
    # ========================================
    "QA Engineer": ["qa engineer", "test engineer", "software tester", "automation engineer", "quality assurance", "test automation"],
    
    # ========================================
    # Specialized Engineering (Medium Priority)
    # ========================================
    "Embedded Systems Engineer": ["embedded systems", "firmware engineer", "embedded software", "embedded engineer"],
    "Game Developer": ["game developer", "game software engineer", "unity developer", "game engineer"],
    "Mobile Developer": ["mobile developer", "ios developer", "android developer", "react native", "mobile app developer", "flutter"],
    "Web Developer": ["web developer", "react developer", "angular developer", "vue developer", "php developer", "website designer", "frontend developer"],
    "Full Stack Developer": ["full stack", "fullstack", "javascript full stack", "typescript full stack"],
    
    # ========================================
    # Generic Software Engineering (LOWER Priority - Catch-all)
    # ========================================
    "Software Engineer": ["software engineer", "developer", "programmer", "backend", "frontend", "application engineer", "app engineer"],
    
    # ========================================
    # Management & Strategy
    # ========================================
    "Engineering Manager": ["engineering manager", "head of engineering", "development manager", "team lead", "cto", "chief technology officer"],
    "Product Manager": ["product manager", "product owner", "digital product manager"],
    "Business Analyst": ["business analyst", "technical business analyst", "process analyst"],
    "Solutions Architect": ["solutions architect", "enterprise architect", "technical architect", "solution architect"],
    
    # ========================================
    # Specialized/Niche
    # ========================================
    "Quantitative Analyst": ["quantitative analyst", "quant", "actuary", "algorithmic trader"],
    "GIS Analyst": ["gis analyst", "gis", "spatial analyst", "geospatial"],
    "Technical Writer": ["technical writer", "documentation engineer"],
    "Sales Engineer": ["sales engineer", "field application engineer", "presales engineer"],
    
    # ========================================
    # Executive & Leadership
    # ========================================
    "Executive Leadership": ["head of", "director of", "chief", "partner", "vp", "vice president", "executive"],
    "Data Leadership": ["head of data", "manager data", "data manager", "data lead", "master data", "mdm"],
    "Technical Lead": ["tech lead", "technical lead", "lead developer", "delivery lead", "initiative lead"],

    # ========================================
    # Academic & Education
    # ========================================
    "Lecturer": ["lecturer", "professor", "phd", "research fellow", "faculty", "teaching staff", "academic", "tutor"],

    # ========================================
    # Health & Clinical Informatics
    # ========================================
    "Health Informatics": ["clinical coder", "clinical data", "emr", "casemix", "health data", "medical coder", "cognitive rater"],

    # ========================================
    # Data Governance, Compliance & Strategy
    # ========================================
    "Data Governance & Compliance": ["data governance", "data protection", "data integrity", "privacy", "compliance", "audit", "risk", "policy"],
    "Strategy & Transformation": ["digital transformation", "strategy", "roadmap", "change manager", "business development"],

    # ========================================
    # Consulting & Implementation
    # ========================================
    "Technical Consultant": ["consultant", "advisor", "implementation specialist", "integration specialist", "solution specialist"],
    "Graduate Program": ["graduate", "cadet", "intern", "trainee", "early career", "digital futures"],

    # ========================================
    # Specialized Operations & Support
    # ========================================
    "Technical Support": ["support advisor", "help desk", "service desk", "support specialist", "technical support"],
    "Operations & Logistics": ["coordinator", "scheduler", "logistics", "weighbridge", "gatehouse"],
    
    # ========================================
    # Niche / Other Tech
    # ========================================
    "SEO & Digital Marketing": ["seo", "search engine optimization", "digital marketing", "marketing technology", "martech"],
    "Intelligence & Security": ["intelligence officer", "tspv", "security clearance", "defense"],
}


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
    1. Clean the title (remove company name, seniority terms, noise)
    2. Try keyword matching against taxonomy
    3. Fall back to embedding similarity if no keyword match
    4. Return "Specialized" if similarity is below threshold
    
    Args:
        title: Raw job title
        company_name: Optional company name to remove from title
        similarity_threshold: Minimum similarity score for embedding match (default 0.4)
        
    Returns:
        Standardized job role name or "Specialized"
    """
    if not title:
        return "Specialized"
    
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
    
    # Comprehensive Australian city-to-state mapping (major cities and regional centers)
    CITY_TO_STATE = {
        # New South Wales
        'sydney': 'NSW', 'newcastle': 'NSW', 'wollongong': 'NSW', 'central coast': 'NSW',
        'maitland': 'NSW', 'wagga wagga': 'NSW', 'albury': 'NSW', 'port macquarie': 'NSW',
        'tamworth': 'NSW', 'orange': 'NSW', 'dubbo': 'NSW', 'bathurst': 'NSW',
        'lismore': 'NSW', 'nowra': 'NSW', 'north sydney': 'NSW', 'parramatta': 'NSW',
        
        # Victoria
        'melbourne': 'VIC', 'geelong': 'VIC', 'ballarat': 'VIC', 'bendigo': 'VIC',
        'shepparton': 'VIC', 'mildura': 'VIC', 'warrnambool': 'VIC', 'wodonga': 'VIC',
        'traralgon': 'VIC', 'horsham': 'VIC',
        
        # Queensland
        'brisbane': 'QLD', 'gold coast': 'QLD', 'sunshine coast': 'QLD', 'townsville': 'QLD',
        'cairns': 'QLD', 'toowoomba': 'QLD', 'mackay': 'QLD', 'rockhampton': 'QLD',
        'bundaberg': 'QLD', 'hervey bay': 'QLD', 'gladstone': 'QLD', 'ipswich': 'QLD',
        
        # South Australia
        'adelaide': 'SA', 'mount gambier': 'SA', 'whyalla': 'SA', 'port lincoln': 'SA',
        'port augusta': 'SA', 'murray bridge': 'SA',
        
        # Western Australia
        'perth': 'WA', 'mandurah': 'WA', 'bunbury': 'WA', 'geraldton': 'WA',
        'albany': 'WA', 'kalgoorlie': 'WA', 'busselton': 'WA', 'rockingham': 'WA',
        
        # Tasmania
        'hobart': 'TAS', 'launceston': 'TAS', 'devonport': 'TAS', 'burnie': 'TAS',
        
        # Northern Territory
        'darwin': 'NT', 'alice springs': 'NT', 'palmerston': 'NT',
        
        # Australian Capital Territory
        'canberra': 'ACT',
    }
    
    # State/territory full names to filter out
    STATE_NAMES = {
        'new south wales', 'nsw', 'victoria', 'vic', 'queensland', 'qld',
        'south australia', 'sa', 'western australia', 'wa', 'tasmania', 'tas',
        'northern territory', 'nt', 'australian capital territory', 'act', 'australia', 'au'
    }
    
    # Common non-city descriptors to filter out
    NON_CITY_PATTERNS = [
        r'cbd and inner suburbs',
        r'inner suburbs',
        r'western suburbs',
        r'eastern suburbs',
        r'northern suburbs',
        r'southern suburbs',
        r'metro',
        r'metropolitan',
        r'region',
        r'area',
        r'greater\s+\w+',
    ]
    
    # Australian state/territory abbreviations
    states = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT']
    state_pattern = '|'.join(states)
    
    normalized = []
    
    for location in locations:
        if not location or not isinstance(location, str):
            continue
            
        # Clean the location string
        location = location.strip()
        location_lower = location.lower()
        
        # Skip if it's a state name
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
                # Not in our known cities, skip this location
                continue
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
        
        # Only add valid city entries
        if city and state:
            normalized.append({
                "city": city,
                "state": state
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


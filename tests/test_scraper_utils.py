import pytest
from jobly.utils.scraper_utils import extract_job_role, normalize_locations


@pytest.mark.parametrize("title,expected", [
    # Provided examples
    ("2025-2026 software engineering internship - engineering",
     "Software Engineer"),

    ("graduate test automation engineer",
     "Test Automation Engineer"),

    ("phd graduate machine learning engineer graduate, trust and safety - 2026 start",
     "Machine Learning Engineer"),

    ("graduate civil engineer (civil and roads) maroochydore, sunshine coast",
     "Civil Engineer"),

    # Additional robustness tests

    # Seniority noise removal
    ("Senior Lead Software Engineer", "Software Engineer"),
    ("Junior Data Scientist", "Data Scientist"),
    ("Entry Level Software Developer", "Software Developer"),

    # Modifier phrases
    ("cloud platform software engineer", "Cloud Platform Software Engineer"),
    ("ai/ml research scientist", "Ai/Ml Research Scientist"),

    # Extra punctuation, commas, symbols
    ("Software Engineer, Backend - 2025 Intake", "Software Engineer"),
    ("Test Engineer / QA - Contract", "Test Engineer"),

    # Engineering vs engineer
    ("software engineering role", "Software Engineer"),
    ("civil engineering graduate position", "Civil Engineer"),

    # Fallbacks and tricky structures
    ("intern - data engineering", "Data Engineer"),
    ("machine learning and ai engineer", "Machine Learning Ai Engineer"),

    # Noisy location text
    ("software engineer sydney, NSW", "Software Engineer"),
    
    # Company names and complex formats
    ("GHD - Grad Program 2025/26 - Graduate Electrical Engineer - Cairns", "Electrical Engineer"),
])
def test_extract_job_role(title, expected):
    """Test the extract_job_role function with various job title formats."""
    assert extract_job_role(title) == expected


@pytest.mark.parametrize("locations,expected", [
    # User requested: Canberra ACT with hybrid mode
    (
        ["Canberra ACT (Hybrid)"],
        [{"city": "Canberra", "state": "ACT"}]
    ),
    
    # Suburb-city-state combinations (should extract main city)
    (
        ["Fortitude Valley, Brisbane QLD"],
        [{"city": "Brisbane", "state": "QLD"}]
    ),
    
    # City with state abbreviation
    (
        ["Sydney NSW"],
        [{"city": "Sydney", "state": "NSW"}]
    ),
    
    # City without state abbreviation (should look up from mapping)
    (
        ["Melbourne"],
        [{"city": "Melbourne", "state": "VIC"}]
    ),
    
    # CBD and suburbs patterns (should be filtered out)
    (
        ["Melbourne CBD and Inner Suburbs"],
        []
    ),
    
    # State names only (should be filtered out)
    (
        ["New South Wales", "Victoria", "Queensland"],
        []
    ),
    
    # State abbreviations only (should be filtered out)
    (
        ["NSW", "VIC", "ACT"],
        []
    ),
    
    # Multiple locations with various formats
    (
        ["Sydney NSW", "Melbourne VIC", "Brisbane QLD"],
        [
            {"city": "Sydney", "state": "NSW"},
            {"city": "Melbourne", "state": "VIC"},
            {"city": "Brisbane", "state": "QLD"}
        ]
    ),
    
    # Regional cities
    (
        ["Newcastle NSW", "Geelong VIC", "Gold Coast QLD"],
        [
            {"city": "Newcastle", "state": "NSW"},
            {"city": "Geelong", "state": "VIC"},
            {"city": "Gold Coast", "state": "QLD"}
        ]
    ),
    
    # Mixed known and unknown locations (unknown should be filtered)
    (
        ["Perth WA", "Unknown City SA"],
        [{"city": "Perth", "state": "WA"}]
    ),
    
    # Duplicate locations (should be deduplicated)
    (
        ["Adelaide SA", "Adelaide SA", "Adelaide, SA"],
        [{"city": "Adelaide", "state": "SA"}]
    ),
    
    # City with comma-separated suburb
    (
        ["North Sydney, Sydney NSW"],
        [{"city": "Sydney", "state": "NSW"}]
    ),
    
    # Remote/work mode indicators (should still extract location)
    (
        ["Darwin NT (Remote)", "Hobart TAS (On-site)"],
        [
            {"city": "Darwin", "state": "NT"},
            {"city": "Hobart", "state": "TAS"}
        ]
    ),
    
    # Empty and invalid inputs
    (
        [],
        []
    ),
    (
        ["", None, "   "],
        []
    ),
    
    # Non-city descriptors (should be filtered out)
    (
        ["Greater Sydney", "Western Suburbs", "Metro Area"],
        []
    ),
])
def test_normalize_locations(locations, expected):
    """Test the normalize_locations function with various location formats."""
    assert normalize_locations(locations) == expected

import pytest
from jobly.utils.scraper_utils import extract_job_role


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

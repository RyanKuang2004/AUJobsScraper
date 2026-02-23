import pytest
from unittest.mock import Mock, patch
from aujobsscraper.scrapers.indeed_scraper import IndeedScraper
from aujobsscraper.utils.salary_parser import SalaryParser


def test_extract_salary_uses_parser_when_jobspy_fields_none():
    """Test that salary parser is used as fallback when min_amount/max_amount are None."""
    scraper = IndeedScraper(search_term="test")

    # Mock job_post with None salary fields
    job_post = {
        "title": "Software Developer",
        "company": "Test Company",
        "description": "$80,000 - $90,000 per year",
        "location": {"city": "Sydney", "state": "NSW", "country": "Australia"},
        "min_amount": None,
        "max_amount": None,
        "interval": None,
        "job_url": "https://test.com/job",
    }

    # Patch SalaryParser to verify it's called
    with patch.object(SalaryParser, 'extract_salary') as mock_extract:
        mock_extract.return_value = {"annual_min": 80000.0, "annual_max": 90000.0}

        result = scraper._extract_salary(job_post)

        # Verify parser was called with description
        mock_extract.assert_called_once_with(job_post["description"])

        # Verify correct result returned
        assert result is not None
        assert result["annual_min"] == 80000.0
        assert result["annual_max"] == 90000.0


def test_extract_salary_skips_parser_when_jobspy_fields_present():
    """Test that salary parser is NOT used when min_amount/max_amount have values."""
    scraper = IndeedScraper(search_term="test")

    # Mock job_post with salary fields present
    job_post = {
        "title": "Software Developer",
        "company": "Test Company",
        "description": "$100,000 per year",  # This should be ignored
        "location": {"city": "Sydney", "state": "NSW", "country": "Australia"},
        "min_amount": 50000.0,
        "max_amount": 60000.0,
        "interval": "yearly",
        "job_url": "https://test.com/job",
    }

    # Patch SalaryParser to verify it's NOT called
    with patch.object(SalaryParser, 'extract_salary') as mock_extract:
        result = scraper._extract_salary(job_post)

        # Verify parser was NOT called
        mock_extract.assert_not_called()

        # Verify result from job_post fields is used
        assert result is not None
        assert result["annual_min"] == 50000.0
        assert result["annual_max"] == 60000.0


def test_format_jobpost_with_salary_in_description():
    """Test full job posting flow with salary in description."""
    scraper = IndeedScraper(search_term="test")

    job_post = {
        "title": "Software Developer",
        "company": "W.D.T. Engineers Pty Ltd",
        "description": (
            "**Boilermaker/Metal Fabricator**\n\n"
            "**W.D.T. Engineers Pty Ltd**\n\n"
            "**$76,000 \\- $85,000 per year \\+ Superannuation**\n\n"
            "**Permanent, Full-time (38 hours per week)**\n\n"
            "**Acacia Ridge QLD 4110**"
        ),
        "location": {"city": "Acacia Ridge", "state": "QLD", "country": "Australia"},
        "min_amount": None,
        "max_amount": None,
        "interval": None,
        "job_url": "https://au.indeed.com/viewjob?jk=test",
        "date_posted": None,
    }

    result = scraper.format_jobpost(job_post)

    assert result is not None
    assert result.job_title == "Software Developer"
    assert result.company == "W.D.T. Engineers Pty Ltd"
    assert result.salary is not None
    assert result.salary["annual_min"] == 76000.0
    assert result.salary["annual_max"] == 85000.0


def test_format_jobpost_without_salary():
    """Test job posting without any salary information."""
    scraper = IndeedScraper(search_term="test")

    job_post = {
        "title": "Volunteer Coordinator",
        "company": "Charity Org",
        "description": "This is a volunteer position with no salary.",
        "location": {"city": "Melbourne", "state": "VIC", "country": "Australia"},
        "min_amount": None,
        "max_amount": None,
        "interval": None,
        "job_url": "https://au.indeed.com/viewjob?jk=test",
        "date_posted": None,
    }

    result = scraper.format_jobpost(job_post)

    assert result is not None
    assert result.job_title == "Volunteer Coordinator"
    assert result.salary is None

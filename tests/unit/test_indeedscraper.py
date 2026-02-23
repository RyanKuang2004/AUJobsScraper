import asyncio

from aujobsscraper.scrapers.indeedscraper import IndeedScraper


def test_format_jobpost_maps_jobspy_payload_to_job_posting():
    scraper = IndeedScraper()

    job_post = {
        "title": "Software Engineer",
        "company": "Acme",
        "job_url": "https://au.indeed.com/viewjob?jk=123",
        "location": {
            "country": "Australia",
            "city": "Sydney",
            "state": "NSW",
        },
        "description": "Build and maintain backend services in Python for our core platform.",
        "interval": "hourly",
        "min_amount": 60,
        "max_amount": 80,
        "date_posted": "2026-02-19",
    }

    posting = scraper.format_jobpost(job_post)
    assert posting is not None
    assert posting.job_title == "Software Engineer"
    assert posting.company == "Acme"
    assert posting.source_urls == ["https://au.indeed.com/viewjob?jk=123"]
    assert posting.platforms == ["indeed"]
    assert posting.locations[0].city == "Sydney"
    assert posting.locations[0].state == "NSW"
    assert posting.posted_at == "2026-02-19"
    assert posting.salary == {"annual_min": 124800.0, "annual_max": 166400.0}


def test_format_jobpost_handles_missing_location():
    scraper = IndeedScraper()
    job_post = {
        "title": "Data Engineer",
        "company": "Contoso",
        "job_url": "https://au.indeed.com/viewjob?jk=456",
        "description": "This is a sufficiently long description for validation checks.",
    }

    posting = scraper.format_jobpost(job_post)
    assert posting is not None
    assert posting.locations[0].city == "Australia"
    assert posting.locations[0].state == ""


def test_scrape_formats_and_filters_invalid_rows():
    scraper = IndeedScraper()
    rows = [
        {
            "title": "DevOps Engineer",
            "company": "Globex",
            "job_url": "https://au.indeed.com/viewjob?jk=789",
            "location": {"city": "Melbourne", "state": "VIC", "country": "Australia"},
            "description": "Operate reliable cloud infrastructure and CI/CD tooling.",
        },
        {
            "title": "Invalid",
            "company": "NoDesc Pty",
            "job_url": "https://au.indeed.com/viewjob?jk=000",
            "location": {"city": "Melbourne", "state": "VIC", "country": "Australia"},
            "description": "bad",
        },
    ]

    scraper._scrape_jobs = lambda: rows

    result = asyncio.run(scraper.scrape())

    assert len(result) == 1
    assert result[0].job_title == "DevOps Engineer"

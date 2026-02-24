import asyncio

from aujobsscraper.scrapers.indeed_scraper import IndeedScraper


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
    scraper = IndeedScraper(search_terms=["devops engineer"])
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

    scraper._scrape_jobs_for_term = lambda term: rows

    result = asyncio.run(scraper.scrape())

    assert len(result) == 1
    assert result[0].job_title == "DevOps Engineer"


def test_scrape_aggregates_across_multiple_search_terms_and_dedupes_urls():
    scraper = IndeedScraper(
        search_terms=["software engineer", "software developer"],
        results_wanted=10,
    )

    rows_by_term = {
        "software engineer": [
            {
                "title": "Software Engineer",
                "company": "Acme",
                "job_url": "https://au.indeed.com/viewjob?jk=abc",
                "location": {"city": "Sydney", "state": "NSW", "country": "Australia"},
                "description": "A valid long description for the first role in this test.",
            }
        ],
        "software developer": [
            {
                "title": "Software Engineer",
                "company": "Acme",
                "job_url": "https://au.indeed.com/viewjob?jk=abc",
                "location": {"city": "Sydney", "state": "NSW", "country": "Australia"},
                "description": "A valid long description for the duplicate role in this test.",
            },
            {
                "title": "Software Developer",
                "company": "Globex",
                "job_url": "https://au.indeed.com/viewjob?jk=def",
                "location": {"city": "Melbourne", "state": "VIC", "country": "Australia"},
                "description": "A valid long description for the second unique role in this test.",
            },
        ],
    }

    scraper._scrape_jobs_for_term = lambda term: rows_by_term[term]
    result = asyncio.run(scraper.scrape())

    assert len(result) == 2
    assert {job.source_urls[0] for job in result} == {
        "https://au.indeed.com/viewjob?jk=abc",
        "https://au.indeed.com/viewjob?jk=def",
    }


def test_scrape_uses_single_search_term_when_search_terms_not_provided():
    scraper = IndeedScraper(search_term="data scientist")

    scraper._scrape_jobs_for_term = lambda term: [
        {
            "title": "Data Scientist",
            "company": "Contoso",
            "job_url": "https://au.indeed.com/viewjob?jk=xyz",
            "location": {"city": "Brisbane", "state": "QLD", "country": "Australia"},
            "description": "A sufficiently long description for the data scientist role.",
        }
    ]

    result = asyncio.run(scraper.scrape())

    assert len(result) == 1
    assert result[0].job_title == "Data Scientist"


def test_scrape_continues_when_one_search_term_fails():
    scraper = IndeedScraper(search_terms=["software engineer", "data engineer"])

    def fake_scrape(term):
        if term == "software engineer":
            raise RuntimeError("temporary failure")
        return [
            {
                "title": "Data Engineer",
                "company": "Initech",
                "job_url": "https://au.indeed.com/viewjob?jk=ok1",
                "location": {"city": "Adelaide", "state": "SA", "country": "Australia"},
                "description": "A sufficiently long description for the data engineer role.",
            }
        ]

    scraper._scrape_jobs_for_term = fake_scrape
    result = asyncio.run(scraper.scrape())

    assert len(result) == 1
    assert result[0].job_title == "Data Engineer"

import inspect
import pytest
from aujobsscraper.scrapers.base_scraper import BaseScraper


def test_scrape_stub_is_async_generator():
    """BaseScraper.scrape() must be an async generator so subclasses are too."""

    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield  # make it an async generator

    scraper = MinimalScraper("test")
    gen = scraper.scrape()
    assert inspect.isasyncgen(gen)


def test_base_scraper_defaults_to_au_country():
    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield

    scraper = MinimalScraper("test")
    assert scraper.country == "AU"


def test_base_scraper_accepts_nz_country():
    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield

    scraper = MinimalScraper("test", country="NZ")
    assert scraper.country == "NZ"


def test_build_job_posting_normalizes_locations_using_country():
    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield

    scraper = MinimalScraper("test", country="NZ")
    posting = scraper._build_job_posting(
        job_title="Backend Engineer",
        company="Acme NZ",
        raw_locations=["Wellington"],
        source_url="https://nz.seek.com/job/1",
        description="A sufficiently long description for validation purposes.",
    )
    assert posting.locations[0].city == "Wellington"
    assert posting.locations[0].state == "Wellington"


def test_build_job_posting_passes_through_description_markdown():
    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield

    scraper = MinimalScraper("test")
    posting = scraper._build_job_posting(
        job_title="Backend Engineer",
        company="Acme",
        raw_locations=["Sydney"],
        source_url="https://seek.com.au/job/1",
        description="A sufficiently long description for validation purposes.",
        description_markdown="## Responsibilities\n- Build things",
    )
    assert posting.description_markdown == "## Responsibilities\n- Build things"


def test_build_job_posting_defaults_description_markdown_to_none():
    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield

    scraper = MinimalScraper("test")
    posting = scraper._build_job_posting(
        job_title="Backend Engineer",
        company="Acme",
        raw_locations=["Sydney"],
        source_url="https://seek.com.au/job/1",
        description="A sufficiently long description for validation purposes.",
    )
    assert posting.description_markdown is None

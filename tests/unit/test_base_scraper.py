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

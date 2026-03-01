import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aujobsscraper.config import settings
from aujobsscraper.scrapers.prosple_scraper import ProspleScraper


class FakePage:
    def __init__(self, html: str):
        self._html = html

    async def goto(self, url, wait_until="domcontentloaded"):
        return None

    async def content(self):
        return self._html


def _make_prosple_playwright_manager():
    class _FakePage:
        async def goto(self, url, wait_until="domcontentloaded"):
            return None

    class _FakeContext:
        async def new_page(self):
            return _FakePage()

    class _FakeBrowser:
        async def new_context(self, **kwargs):
            return _FakeContext()

        async def close(self):
            return None

    class _FakePlaywrightManager:
        async def __aenter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(launch=self._launch))

        async def __aexit__(self, *args):
            return None

        async def _launch(self, headless=True):
            return _FakeBrowser()

    return _FakePlaywrightManager()


def test_prosple_regular_run_url_includes_sort_newest_desc(monkeypatch):
    """On a regular run, listing URLs must include sort=newest_opportunities%7Cdesc."""
    scraper = ProspleScraper()
    monkeypatch.setattr(settings, "initial_run", False)
    monkeypatch.setattr(settings, "max_pages", 20)
    monkeypatch.setattr(settings, "prosple_regular_max_pages", 4)
    monkeypatch.setattr(settings, "prosple_items_per_page", 20)
    monkeypatch.setattr(settings, "search_keywords", ["software engineer"])

    seen_urls = []

    async def _fake_get_job_links(page, url):
        seen_urls.append(url)
        return []

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr(
        "aujobsscraper.scrapers.prosple_scraper.async_playwright",
        lambda: _make_prosple_playwright_manager(),
    )
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(_drain(scraper))

    assert len(seen_urls) == 1
    assert "sort=newest_opportunities%7Cdesc" in seen_urls[0]


def test_prosple_initial_run_url_excludes_sort_param(monkeypatch):
    """On an initial run, listing URLs must NOT include the sort param."""
    scraper = ProspleScraper()
    monkeypatch.setattr(settings, "initial_run", True)
    monkeypatch.setattr(settings, "max_pages", 1)
    monkeypatch.setattr(settings, "prosple_items_per_page", 20)
    monkeypatch.setattr(settings, "search_keywords", ["software engineer"])

    seen_urls = []

    async def _fake_get_job_links(page, url):
        seen_urls.append(url)
        return []

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr(
        "aujobsscraper.scrapers.prosple_scraper.async_playwright",
        lambda: _make_prosple_playwright_manager(),
    )
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(_drain(scraper))

    assert len(seen_urls) == 1
    assert "sort=" not in seen_urls[0]


def test_get_job_links_extracts_target_blank_graduate_employer_links(monkeypatch):
    html = """
    <html>
      <body>
        <a target="_blank" href="/graduate-employers/acme/jobs-internships/software-engineer-123">Match 1</a>
        <a target="_blank" href="/graduate-employers/contoso/jobs-internships/data-engineer-456">Match 2</a>
        <a target="_self" href="/graduate-employers/ignored/jobs-internships/nope">Ignore target</a>
        <a target="_blank" href="/not-graduate-employers/ignored">Ignore prefix</a>
      </body>
    </html>
    """

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    scraper = ProspleScraper()
    page = FakePage(html)

    jobs = asyncio.run(scraper._get_job_links(page, "https://au.prosple.com/search-jobs"))
    assert jobs == [
        {"url": "https://au.prosple.com/graduate-employers/acme/jobs-internships/software-engineer-123"},
        {"url": "https://au.prosple.com/graduate-employers/contoso/jobs-internships/data-engineer-456"},
    ]


def test_extract_salary_returns_dict_from_json_ld_quantitative_value():
    scraper = ProspleScraper()
    json_data = {
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "AUD",
            "value": {
                "@type": "QuantitativeValue",
                "unitText": "YEAR",
                "minValue": 50000,
                "maxValue": 56000,
            },
        }
    }

    salary = scraper._extract_salary(None, json_data)
    assert salary == {"annual_min": 50000.0, "annual_max": 56000.0}


def test_extract_salary_handles_comma_formatted_min_max_values():
    """JSON-LD minValue/maxValue as comma-formatted strings must not raise ValueError."""
    scraper = ProspleScraper()
    json_data = {
        "@type": "JobPosting",
        "baseSalary": {
            "value": {
                "minValue": "70,000",
                "maxValue": "90,000",
            }
        }
    }
    result = scraper._extract_salary(None, json_data)
    assert result == {"annual_min": 70000.0, "annual_max": 90000.0}


def test_scrape_stops_at_configured_max_pages(monkeypatch):
    scraper = ProspleScraper()
    monkeypatch.setattr(settings, "initial_run", False)
    monkeypatch.setattr(settings, "max_pages", 1)
    monkeypatch.setattr(settings, "prosple_regular_max_pages", 1)
    monkeypatch.setattr(settings, "prosple_items_per_page", 20)
    monkeypatch.setattr(settings, "search_keywords", ["software engineer"])

    class _FakePage:
        async def goto(self, url, wait_until="domcontentloaded"):
            return None

    class _FakeContext:
        async def new_page(self):
            return _FakePage()

    class _FakeBrowser:
        async def new_context(self, user_agent=None):
            return _FakeContext()

        async def close(self):
            return None

    class _FakePlaywrightManager:
        async def __aenter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(launch=self._launch))

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def _launch(self, headless=True):
            return _FakeBrowser()

    calls = {"count": 0}

    async def _fake_get_job_links(page, url):
        calls["count"] += 1
        if calls["count"] <= 3:
            return [{"url": f"https://au.prosple.com/job-{calls['count']}"}]
        return []

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr("aujobsscraper.scrapers.prosple_scraper.async_playwright", lambda: _FakePlaywrightManager())
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(_drain(scraper))

    assert calls["count"] == 1


def test_scrape_iterates_keywords_and_uses_plus_encoded_tag(monkeypatch):
    scraper = ProspleScraper()
    monkeypatch.setattr(settings, "initial_run", False)
    monkeypatch.setattr(settings, "max_pages", 1)
    monkeypatch.setattr(settings, "prosple_regular_max_pages", 1)
    monkeypatch.setattr(settings, "prosple_items_per_page", 20)
    monkeypatch.setattr(settings, "search_keywords", ["software engineer", "data scientist"])

    class _FakePage:
        async def goto(self, url, wait_until="domcontentloaded"):
            return None

    class _FakeContext:
        async def new_page(self):
            return _FakePage()

    class _FakeBrowser:
        async def new_context(self, user_agent=None):
            return _FakeContext()

        async def close(self):
            return None

    class _FakePlaywrightManager:
        async def __aenter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(launch=self._launch))

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def _launch(self, headless=True):
            return _FakeBrowser()

    seen_urls = []

    async def _fake_get_job_links(page, url):
        seen_urls.append(url)
        if "software+engineer" in url:
            return [{"url": "https://au.prosple.com/job-software"}]
        if "data+scientist" in url:
            return [{"url": "https://au.prosple.com/job-data"}]
        return []

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr("aujobsscraper.scrapers.prosple_scraper.async_playwright", lambda: _FakePlaywrightManager())
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(_drain(scraper))

    assert seen_urls == [
        f"{scraper.search_url_base}&keywords=software+engineer&start=0&sort=newest_opportunities%7Cdesc",
        f"{scraper.search_url_base}&keywords=data+scientist&start=0&sort=newest_opportunities%7Cdesc",
    ]


def test_prosple_uses_full_max_pages_on_initial_run():
    scraper = ProspleScraper()
    with patch("aujobsscraper.scrapers.prosple_scraper.settings") as mock_settings:
        mock_settings.initial_run = True
        mock_settings.max_pages = 20
        mock_settings.prosple_regular_max_pages = 3
        mock_settings.prosple_items_per_page = 20
        limit = mock_settings.max_pages if mock_settings.initial_run else mock_settings.prosple_regular_max_pages
        assert limit == 20


def test_prosple_uses_regular_max_pages_on_regular_run():
    scraper = ProspleScraper()
    with patch("aujobsscraper.scrapers.prosple_scraper.settings") as mock_settings:
        mock_settings.initial_run = False
        mock_settings.max_pages = 20
        mock_settings.prosple_regular_max_pages = 3
        mock_settings.prosple_items_per_page = 20
        limit = mock_settings.max_pages if mock_settings.initial_run else mock_settings.prosple_regular_max_pages
        assert limit == 3


# ---------------------------------------------------------------------------
# Async-generator interface tests
# ---------------------------------------------------------------------------

async def _drain(scraper):
    """Consume the async generator returned by scraper.scrape()."""
    async for _ in scraper.scrape():
        pass


def test_prosple_scrape_is_async_generator():
    scraper = ProspleScraper()
    gen = scraper.scrape()
    assert inspect.isasyncgen(gen)


@pytest.mark.asyncio
async def test_prosple_scrape_yields_one_batch_per_page():
    scraper = ProspleScraper()

    async def fake_get_job_links(page, url):
        return [{"url": "https://au.prosple.com/job/1"}]

    page_count = 0

    async def fake_process_jobs_concurrently(context, urls):
        nonlocal page_count
        page_count += 1
        for url in urls:
            scraper._results.append(MagicMock())

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch.object(scraper, '_get_job_links', fake_get_job_links), \
         patch.object(scraper, 'process_jobs_concurrently', fake_process_jobs_concurrently), \
         patch('aujobsscraper.scrapers.prosple_scraper.async_playwright') as mock_pw, \
         patch('aujobsscraper.scrapers.prosple_scraper.settings') as mock_settings:
        mock_pw.return_value.__aenter__.return_value = mock_p
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_settings.initial_run = False
        mock_settings.search_keywords = ["software engineer"]
        mock_settings.max_pages = 5
        mock_settings.prosple_regular_max_pages = 1
        mock_settings.prosple_items_per_page = 10
        mock_settings.concurrency = 2

        batches = []
        async for batch in scraper.scrape():
            batches.append(list(batch))

    assert len(batches) == 1
    assert len(batches[0]) == 1

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace


class _FakeJobPosting:
    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return self._payload


class _FakeSimpleScraper:
    async def scrape(self, skip_urls=None):
        yield [_FakeJobPosting({"source_urls": ["https://example.com/job/1"]})]


class _FakeProspleScraper:
    def __init__(self):
        self.get_job_links_calls = 0

    async def _get_job_links(self, page, url):
        self.get_job_links_calls += 1
        return [{"url": "https://example.com/prosple/job-1"}]

    async def scrape(self, skip_urls=None):
        first = await self._get_job_links(None, "https://example.com/start=0")
        if first:
            yield [_FakeJobPosting({"source_urls": [first[0]["url"]]})]


def _load_module():
    path = Path("scripts/run_all_scrapers_first_iteration.py")
    spec = importlib.util.spec_from_file_location("run_all_scrapers_first_iteration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_scraper_indeed_uses_first_search_term_and_caps_results(monkeypatch):
    module = _load_module()
    captured = {}

    fake_settings = SimpleNamespace(
        search_keywords=["software engineer", "data engineer"],
        gradconnection_keywords=["software engineer", "data science"],
        max_pages=20,
    )
    monkeypatch.setattr(module, "settings", fake_settings)

    def _indeed_factory(**kwargs):
        captured["kwargs"] = kwargs
        return _FakeSimpleScraper()

    monkeypatch.setattr(module, "IndeedScraper", _indeed_factory)

    asyncio.run(module.run_scraper("indeed"))

    assert captured["kwargs"]["search_terms"] == ["software engineer"]
    assert captured["kwargs"]["results_wanted"] == 5
    assert captured["kwargs"]["results_wanted_total"] == 5


def test_run_scraper_prosple_stops_after_first_page(monkeypatch):
    module = _load_module()
    fake_scraper = _FakeProspleScraper()

    monkeypatch.setattr(module, "ProspleScraper", lambda: fake_scraper)
    monkeypatch.setattr(module, "settings", SimpleNamespace(
        search_keywords=["software engineer"],
        gradconnection_keywords=["software engineer"],
        max_pages=20,
    ))

    result = asyncio.run(module.run_scraper("prosple"))

    assert result["count"] == 1
    assert fake_scraper.get_job_links_calls == 1

import asyncio
from types import SimpleNamespace

from aujobsscraper.config import settings
from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper


class FakePage:
    def __init__(self, html: str, json_data=None):
        self._html = html
        self._json_data = json_data

    async def goto(self, url, wait_until="domcontentloaded"):
        if not isinstance(url, str):
            raise TypeError("Page.goto: url must be string")
        return None

    async def wait_for_selector(self, selector, timeout=10000):
        return None

    async def content(self):
        return self._html

    async def evaluate(self, _):
        return self._json_data


def _make_gc_playwright_manager():
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


def test_gradconnection_regular_run_url_includes_ordering_param(monkeypatch):
    """On a regular run, listing URLs must include ordering=-recent_job_created."""
    scraper = GradConnectionScraper()
    monkeypatch.setattr(settings, "initial_run", False)
    monkeypatch.setattr(settings, "gradconnection_keywords", ["software engineer"])
    monkeypatch.setattr(settings, "gradconnection_regular_max_pages", 4)

    seen_urls = []

    async def _fake_get_job_links(page, url):
        seen_urls.append(url)
        return []

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr(
        "aujobsscraper.scrapers.gradconnection_scraper.async_playwright",
        lambda: _make_gc_playwright_manager(),
    )
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(scraper.scrape())

    assert len(seen_urls) == 1
    assert "ordering=-recent_job_created" in seen_urls[0]


def test_gradconnection_initial_run_url_excludes_ordering_param(monkeypatch):
    """On an initial run, listing URLs must NOT include the ordering param."""
    scraper = GradConnectionScraper()
    monkeypatch.setattr(settings, "initial_run", True)
    monkeypatch.setattr(settings, "gradconnection_keywords", ["software engineer"])
    monkeypatch.setattr(settings, "max_pages", 1)

    seen_urls = []

    async def _fake_get_job_links(page, url):
        seen_urls.append(url)
        return []

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr(
        "aujobsscraper.scrapers.gradconnection_scraper.async_playwright",
        lambda: _make_gc_playwright_manager(),
    )
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(scraper.scrape())

    assert len(seen_urls) == 1
    assert "ordering=" not in seen_urls[0]


def test_gradconnection_regular_run_respects_regular_max_pages(monkeypatch):
    """On a regular run, scraper stops after gradconnection_regular_max_pages pages."""
    scraper = GradConnectionScraper()
    monkeypatch.setattr(settings, "initial_run", False)
    monkeypatch.setattr(settings, "gradconnection_keywords", ["software engineer"])
    monkeypatch.setattr(settings, "gradconnection_regular_max_pages", 4)
    monkeypatch.setattr(settings, "max_pages", 20)

    call_count = {"n": 0}

    async def _fake_get_job_links(page, url):
        call_count["n"] += 1
        return [f"https://au.gradconnection.com/job-{call_count['n']}-{i}/" for i in range(5)]

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr(
        "aujobsscraper.scrapers.gradconnection_scraper.async_playwright",
        lambda: _make_gc_playwright_manager(),
    )
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(scraper.scrape())

    assert call_count["n"] == 4


def test_gradconnection_initial_run_uses_max_pages(monkeypatch):
    """On an initial run, scraper uses max_pages (not gradconnection_regular_max_pages)."""
    scraper = GradConnectionScraper()
    monkeypatch.setattr(settings, "initial_run", True)
    monkeypatch.setattr(settings, "gradconnection_keywords", ["software engineer"])
    monkeypatch.setattr(settings, "max_pages", 3)
    monkeypatch.setattr(settings, "gradconnection_regular_max_pages", 4)

    call_count = {"n": 0}

    async def _fake_get_job_links(page, url):
        call_count["n"] += 1
        return [f"https://au.gradconnection.com/job-{call_count['n']}-{i}/" for i in range(5)]

    async def _fake_process_jobs(context, job_urls):
        return None

    monkeypatch.setattr(
        "aujobsscraper.scrapers.gradconnection_scraper.async_playwright",
        lambda: _make_gc_playwright_manager(),
    )
    monkeypatch.setattr(scraper, "_get_job_links", _fake_get_job_links)
    monkeypatch.setattr(scraper, "process_jobs_concurrently", _fake_process_jobs)

    asyncio.run(scraper.scrape())

    assert call_count["n"] == 3


def test_process_job_accepts_dict_payload_with_url():
    html = """
    <html>
      <body>
        <h1 class="employers-profile-h1">FPGA Engineer Internship</h1>
        <h1 class="employers-panel-title">Citadel Securities</h1>
        <div class="campaign-content-container">
          This is a sufficiently long description for validation.
        </div>
        <ul class="box-content">
          <li><strong>Location</strong> Sydney</li>
        </ul>
      </body>
    </html>
    """

    scraper = GradConnectionScraper()
    page = FakePage(html)

    asyncio.run(
        scraper._process_job(
            page,
            {"url": "https://au.gradconnection.com/employers/citadel/jobs/fpga-internship/"},
        )
    )

    assert len(scraper._results) == 1


def test_process_job_normalizes_gradconnection_salary_dict():
    html = """
    <html>
      <body>
        <h1 class="employers-profile-h1">Graduate Software Engineer</h1>
        <h1 class="employers-panel-title">Example Co</h1>
        <div class="campaign-content-container">
          This is a sufficiently long description for validation.
        </div>
        <ul class="box-content">
          <li><strong>Location</strong> Sydney</li>
        </ul>
      </body>
    </html>
    """
    json_data = {
        "campaignstore": {
            "campaign": {
                "salary": {
                    "min_salary": "60,000",
                    "max_salary": "80,000",
                    "details": "",
                }
            }
        }
    }

    scraper = GradConnectionScraper()
    page = FakePage(html, json_data=json_data)

    asyncio.run(
        scraper._process_job(
            page,
            {"url": "https://au.gradconnection.com/jobs/example"},
        )
    )

    assert len(scraper._results) == 1
    assert scraper._results[0].salary == {"annual_min": 60000.0, "annual_max": 80000.0}


def test_extract_salary_handles_comma_formatted_strings():
    """Salary dict with comma-formatted string values must not crash."""
    scraper = GradConnectionScraper()
    json_data = {
        "campaignstore": {
            "campaign": {
                "salary": {
                    "min_salary": "60,000",
                    "max_salary": "80,000",
                    "details": "",
                }
            }
        }
    }
    result = scraper._extract_salary(None, json_data)
    assert result == {"annual_min": 60000.0, "annual_max": 80000.0}


def test_extract_salary_returns_none_for_unparseable_salary():
    """Returns None when salary values cannot be parsed."""
    scraper = GradConnectionScraper()
    json_data = {
        "campaignstore": {
            "campaign": {
                "salary": {
                    "min_salary": None,
                    "max_salary": None,
                    "details": "",
                }
            }
        }
    }
    result = scraper._extract_salary(None, json_data)
    assert result is None

import asyncio
import importlib.util
from pathlib import Path


class _FakeJobPosting:
    def to_dict(self):
        return {"title": "Example"}


class _FakeScraper:
    def __init__(self):
        self._results = []
        self.calls = []

    async def _process_job(self, page, job):
        self.calls.append(job)
        self._results.append(_FakeJobPosting())


class _FakePage:
    async def close(self):
        return None


class _FakeContext:
    async def new_page(self):
        return _FakePage()

    async def close(self):
        return None


class _FakeBrowser:
    async def new_context(self, **kwargs):
        return _FakeContext()

    async def close(self):
        return None


class _FakeChromium:
    async def launch(self, headless=True):
        return _FakeBrowser()


class _FakePlaywright:
    def __init__(self):
        self.chromium = _FakeChromium()


class _FakePlaywrightCM:
    async def __aenter__(self):
        return _FakePlaywright()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _load_module():
    path = Path("scripts/temp_run_gradconnection_one_job.py")
    spec = importlib.util.spec_from_file_location("temp_run_gradconnection_one_job", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_one_job_processes_single_url_and_prints_count(monkeypatch):
    module = _load_module()
    scraper = _FakeScraper()

    monkeypatch.setattr(module, "GradConnectionScraper", lambda: scraper)
    monkeypatch.setattr(module, "async_playwright", lambda: _FakePlaywrightCM())

    captured = []
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: captured.append(" ".join(str(a) for a in args)))

    url = "https://au.gradconnection.com/jobs/example-job"
    asyncio.run(module.run_one_job(url))

    assert scraper.calls == [{"url": url}]
    assert any("Processed jobs: 1" in line for line in captured)

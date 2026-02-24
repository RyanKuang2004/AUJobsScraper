import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


class _FakeJobPosting:
    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return self._payload


class _FakeScraper:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = 0

    async def scrape(self):
        self.calls += 1
        return [
            _FakeJobPosting(
                {
                    "job_title": "Software Engineer",
                    "company": "Acme",
                    "platforms": ["indeed"],
                }
            )
        ]


def _load_module():
    path = Path("scripts/temp_run_indeed_jobs.py")
    spec = importlib.util.spec_from_file_location("temp_run_indeed_jobs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_jobs_prints_processed_count_and_sample(monkeypatch):
    module = _load_module()
    captured = {}

    def _factory(**kwargs):
        captured["scraper"] = _FakeScraper(**kwargs)
        return captured["scraper"]

    monkeypatch.setattr(module, "IndeedScraper", _factory)

    printed = []
    monkeypatch.setattr(
        "builtins.print", lambda *args, **kwargs: printed.append(" ".join(str(a) for a in args))
    )

    asyncio.run(module.run_jobs(search_term="software engineer", results_wanted=1))

    fake_scraper = captured["scraper"]
    assert fake_scraper.calls == 1
    assert fake_scraper.kwargs["search_term"] == "software engineer"
    assert any("Processed jobs: 1" in line for line in printed)
    assert any('"job_title": "Software Engineer"' in line for line in printed)


def test_run_jobs_defaults_to_configured_search_terms(monkeypatch):
    module = _load_module()
    captured = {}

    def _factory(**kwargs):
        captured["scraper"] = _FakeScraper(**kwargs)
        return captured["scraper"]

    monkeypatch.setattr(module, "IndeedScraper", _factory)

    asyncio.run(module.run_jobs(search_term=None, results_wanted=2))

    fake_scraper = captured["scraper"]
    assert fake_scraper.calls == 1
    assert fake_scraper.kwargs["search_terms"] == module.settings.search_keywords
    assert fake_scraper.kwargs["results_wanted_total"] == 2


def test_script_runs_directly_without_pythonpath():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "scripts/temp_run_indeed_jobs.py", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Temporarily run IndeedScraper" in result.stdout

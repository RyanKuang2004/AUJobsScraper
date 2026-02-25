# Add Sorting and Regular-Run Page Limits Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** On regular runs (`initial_run = False`), sort both Prosple and GradConnection results by newest and cap each keyword search at 4 pages. Initial runs are unchanged.

**Architecture:** Three-part change — (1) update config defaults and add `gradconnection_regular_max_pages`, (2) conditionally append the sort/ordering query param to listing URLs only on regular runs, (3) wire GradConnection's page limit to `initial_run` the same way Prosple already does. No changes to initial-run behaviour.

**Tech Stack:** Python, Pydantic Settings (config), Playwright (browser), pytest (tests).

---

### Task 1: Update config — change `prosple_regular_max_pages` default and add `gradconnection_regular_max_pages`

**Files:**
- Modify: `aujobsscraper/config.py`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_config.py`:

```python
def test_prosple_regular_max_pages_default_is_4():
    settings = ScraperSettings()
    assert settings.prosple_regular_max_pages == 4


def test_gradconnection_regular_max_pages_default_is_4():
    settings = ScraperSettings()
    assert settings.gradconnection_regular_max_pages == 4
```

**Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_config.py::test_prosple_regular_max_pages_default_is_4 tests/unit/test_config.py::test_gradconnection_regular_max_pages_default_is_4 -v
```

Expected: first test `FAILED` (default is 3, not 4), second test `FAILED` (attribute doesn't exist).

**Step 3: Update config fields**

In `aujobsscraper/config.py`, make two changes:

```python
# Change default from 3 to 4:
prosple_regular_max_pages: int = Field(default=4)

# Add after prosple_regular_max_pages:
gradconnection_regular_max_pages: int = Field(default=4)
```

**Step 4: Run tests to verify they pass**

```
pytest tests/unit/test_config.py::test_prosple_regular_max_pages_default_is_4 tests/unit/test_config.py::test_gradconnection_regular_max_pages_default_is_4 -v
```

Expected: `PASSED`

**Step 5: Run the full config test suite to check for regressions**

```
pytest tests/unit/test_config.py -v
```

Expected: All `PASSED`. Note: `test_indeed_and_prosple_settings_have_defaults` does not assert `prosple_regular_max_pages`, so it will not break.

**Step 6: Commit**

```bash
git add aujobsscraper/config.py tests/unit/test_config.py
git commit -m "feat: set prosple_regular_max_pages to 4 and add gradconnection_regular_max_pages"
```

---

### Task 2: Add sort param to Prosple URL on regular runs

**Files:**
- Modify: `aujobsscraper/scrapers/prosple_scraper.py`
- Test: `tests/unit/test_prosple_scraper.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_prosple_scraper.py`:

```python
from types import SimpleNamespace


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

    asyncio.run(scraper.scrape())

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

    asyncio.run(scraper.scrape())

    assert len(seen_urls) == 1
    assert "sort=" not in seen_urls[0]
```

**Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_prosple_scraper.py::test_prosple_regular_run_url_includes_sort_newest_desc tests/unit/test_prosple_scraper.py::test_prosple_initial_run_url_excludes_sort_param -v
```

Expected: first test `FAILED` (sort param not present yet), second test `PASSED` (no sort present currently — this confirms initial-run behaviour is preserved).

**Step 3: Add conditional sort param to URL in `ProspleScraper.scrape()`**

In `aujobsscraper/scrapers/prosple_scraper.py`, add the sort suffix computation just before the `while` loop (after `page_count = 0`):

```python
# Add after "page_count = 0":
sort_suffix = "&sort=newest_opportunities%7Cdesc" if not settings.initial_run else ""
```

Then change line 50 (the URL construction) from:

```python
url = f"{self.search_url_base}&keywords={encoded_keyword}&start={start}"
```

To:

```python
url = f"{self.search_url_base}&keywords={encoded_keyword}&start={start}{sort_suffix}"
```

**Step 4: Run both tests to verify they pass**

```
pytest tests/unit/test_prosple_scraper.py::test_prosple_regular_run_url_includes_sort_newest_desc tests/unit/test_prosple_scraper.py::test_prosple_initial_run_url_excludes_sort_param -v
```

Expected: `PASSED`

**Step 5: Run the full Prosple test suite**

```
pytest tests/unit/test_prosple_scraper.py -v
```

Expected: All `PASSED`. Note: `test_scrape_iterates_keywords_and_uses_plus_encoded_tag` asserts exact URLs — it monkeypatches `settings.initial_run = False`, so it will now expect URLs with the sort suffix. Update that test's assertions:

```python
# In test_scrape_iterates_keywords_and_uses_plus_encoded_tag, change:
assert seen_urls == [
    f"{scraper.search_url_base}&keywords=software+engineer&start=0",
    f"{scraper.search_url_base}&keywords=data+scientist&start=0",
]

# To:
assert seen_urls == [
    f"{scraper.search_url_base}&keywords=software+engineer&start=0&sort=newest_opportunities%7Cdesc",
    f"{scraper.search_url_base}&keywords=data+scientist&start=0&sort=newest_opportunities%7Cdesc",
]
```

Re-run after fixing:

```
pytest tests/unit/test_prosple_scraper.py -v
```

Expected: All `PASSED`

**Step 6: Commit**

```bash
git add aujobsscraper/scrapers/prosple_scraper.py tests/unit/test_prosple_scraper.py
git commit -m "feat: sort Prosple results by newest on regular runs"
```

---

### Task 3: Add ordering param and regular-run page limit to GradConnection

**Files:**
- Modify: `aujobsscraper/scrapers/gradconnection_scraper.py`
- Test: `tests/unit/test_gradconnection_scraper.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_gradconnection_scraper.py`:

```python
import asyncio
from types import SimpleNamespace

from aujobsscraper.config import settings


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
    from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper

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
    from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper

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
    from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper

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
    from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper

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
```

**Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_gradconnection_scraper.py::test_gradconnection_regular_run_url_includes_ordering_param tests/unit/test_gradconnection_scraper.py::test_gradconnection_initial_run_url_excludes_ordering_param tests/unit/test_gradconnection_scraper.py::test_gradconnection_regular_run_respects_regular_max_pages tests/unit/test_gradconnection_scraper.py::test_gradconnection_initial_run_uses_max_pages -v
```

Expected: ordering and page-limit tests `FAILED`, initial-run exclusion test likely `PASSED` (ordering not present yet).

**Step 3: Update `GradConnectionScraper.scrape()`**

In `aujobsscraper/scrapers/gradconnection_scraper.py`, change lines 29–30 from:

```python
terms = settings.gradconnection_keywords
limit = settings.max_pages
```

To:

```python
terms = settings.gradconnection_keywords
limit = settings.max_pages if settings.initial_run else settings.gradconnection_regular_max_pages
```

Then change line 44 (URL construction) from:

```python
url = f"{self.base_url}/jobs/australia/?title={encoded_term}&page={page_num}"
```

To:

```python
if settings.initial_run:
    url = f"{self.base_url}/jobs/australia/?title={encoded_term}&page={page_num}"
else:
    url = f"{self.base_url}/jobs/australia/?title={encoded_term}&ordering=-recent_job_created&page={page_num}"
```

**Step 4: Run all four new tests to verify they pass**

```
pytest tests/unit/test_gradconnection_scraper.py::test_gradconnection_regular_run_url_includes_ordering_param tests/unit/test_gradconnection_scraper.py::test_gradconnection_initial_run_url_excludes_ordering_param tests/unit/test_gradconnection_scraper.py::test_gradconnection_regular_run_respects_regular_max_pages tests/unit/test_gradconnection_scraper.py::test_gradconnection_initial_run_uses_max_pages -v
```

Expected: All `PASSED`

**Step 5: Run full test suite**

```
pytest tests/unit/ -v
```

Expected: All `PASSED`

**Step 6: Commit**

```bash
git add aujobsscraper/scrapers/gradconnection_scraper.py tests/unit/test_gradconnection_scraper.py
git commit -m "feat: sort GradConnection by newest and use regular-run page limit"
```

---

## Summary of all changes

| File | Change |
|---|---|
| `aujobsscraper/config.py` | `prosple_regular_max_pages` default 3 → 4; add `gradconnection_regular_max_pages = 4` |
| `aujobsscraper/scrapers/prosple_scraper.py` | Append `&sort=newest_opportunities%7Cdesc` to URL only when `initial_run = False` |
| `aujobsscraper/scrapers/gradconnection_scraper.py` | Pick `gradconnection_regular_max_pages` vs `max_pages` based on `initial_run`; append `&ordering=-recent_job_created` to URL only when `initial_run = False` |
| `tests/unit/test_config.py` | Add default-value tests for `prosple_regular_max_pages` (4) and `gradconnection_regular_max_pages` (4) |
| `tests/unit/test_prosple_scraper.py` | Add sort-URL tests (regular + initial run); fix existing URL-assertion test for new sort suffix |
| `tests/unit/test_gradconnection_scraper.py` | Add ordering-URL tests (regular + initial run); add page-limit tests for both run modes |

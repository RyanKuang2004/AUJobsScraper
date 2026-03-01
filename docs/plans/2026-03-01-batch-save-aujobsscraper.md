# Async Generator Scrape Interface — aujobsscraper

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert `scrape()` in `BaseScraper`, `SeekScraper`, `GradConnectionScraper`, and `ProspleScraper` from a coroutine that buffers all results to an async generator that yields one `List[JobPosting]` per page-batch, enabling the caller to persist jobs immediately as they are collected.

**Architecture:** Each scraper's `scrape()` method already calls `process_jobs_concurrently()` once per listing page, appending results to `self._results`. The change records a `batch_start` index before each call and yields the slice `self._results[batch_start:]` immediately after. `BaseScraper` gets an updated type hint and a helper `_run_async()` to keep `run()` working. `IndeedScraper` is unchanged.

**Tech Stack:** Python 3.12+, pytest, pytest-asyncio, unittest.mock

---

### Task 1: Update `BaseScraper.scrape()` signature and `run()`

**Files:**
- Modify: `aujobsscraper/scrapers/base_scraper.py`
- Test: `tests/unit/test_base_scraper.py` (create)

**Step 1: Write the failing test**

```python
# tests/unit/test_base_scraper.py
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
```

**Step 2: Run to confirm it fails**

```bash
pytest tests/unit/test_base_scraper.py::test_scrape_stub_is_async_generator -v
```

Expected: FAIL — `BaseScraper.scrape()` is currently a plain coroutine, not an async generator.

**Step 3: Update `base_scraper.py`**

Replace the `scrape()` stub and `run()` method:

```python
from typing import AsyncGenerator, List, Optional, Set

# ...existing imports...

class BaseScraper:
    # ...existing __init__, _build_job_posting, _collect_job, _setup_browser_context...

    async def scrape(
        self, skip_urls: Optional[Set[str]] = None
    ) -> AsyncGenerator[List[JobPosting], None]:
        """
        Yield batches of JobPosting objects as they are collected.
        Each yield corresponds to one listing page worth of jobs.
        Subclasses must implement this as an async generator.
        """
        raise NotImplementedError("Subclasses must implement scrape()")
        yield  # makes this an async generator

    async def _run_async(self) -> None:
        """Consume the scrape generator, discarding results (used by run())."""
        async for _ in self.scrape():
            pass

    def run(self) -> None:
        asyncio.run(self._run_async())

    async def _process_job(self, page, url: str) -> None:
        raise NotImplementedError("Subclasses must implement _process_job()")
```

**Step 4: Run the test**

```bash
pytest tests/unit/test_base_scraper.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/base_scraper.py tests/unit/test_base_scraper.py
git commit -m "feat: convert BaseScraper.scrape() to async generator interface"
```

---

### Task 2: Convert `SeekScraper.scrape()` to async generator

**Files:**
- Modify: `aujobsscraper/scrapers/seek_scraper.py`
- Test: `tests/unit/test_seek_scraper.py` (create)

**Step 1: Write the failing tests**

```python
# tests/unit/test_seek_scraper.py
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aujobsscraper.scrapers.seek_scraper import SeekScraper


def test_seek_scrape_is_async_generator():
    scraper = SeekScraper()
    gen = scraper.scrape()
    assert inspect.isasyncgen(gen)


@pytest.mark.asyncio
async def test_seek_scrape_yields_one_batch_per_page():
    """Each call to process_jobs_concurrently produces one yielded batch."""
    scraper = SeekScraper()

    # Simulate two pages: page 1 → 2 jobs, page 2 → 1 job, page 3 → empty (stop)
    link_responses = [
        ["https://seek.com.au/job/1", "https://seek.com.au/job/2"],
        ["https://seek.com.au/job/3"],
        [],
    ]
    link_call_count = 0

    async def fake_get_job_links(page, url):
        nonlocal link_call_count
        links = link_responses[min(link_call_count, len(link_responses) - 1)]
        link_call_count += 1
        return links

    async def fake_process_jobs_concurrently(context, urls):
        for url in urls:
            job = MagicMock()
            job.job_title = f"Job from {url}"
            scraper._results.append(job)

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch.object(scraper, '_get_job_links', fake_get_job_links), \
         patch.object(scraper, 'process_jobs_concurrently', fake_process_jobs_concurrently), \
         patch('aujobsscraper.scrapers.seek_scraper.async_playwright') as mock_pw:
        mock_pw.return_value.__aenter__.return_value = mock_p
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        batches = []
        async for batch in scraper.scrape():
            batches.append(list(batch))

    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


@pytest.mark.asyncio
async def test_seek_scrape_skips_known_urls():
    scraper = SeekScraper()
    skip_urls = {"https://seek.com.au/job/1"}

    async def fake_get_job_links(page, url):
        return ["https://seek.com.au/job/1", "https://seek.com.au/job/2"]

    processed_urls = []

    async def fake_process_jobs_concurrently(context, urls):
        processed_urls.extend(urls)
        for url in urls:
            job = MagicMock()
            scraper._results.append(job)

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch.object(scraper, '_get_job_links', fake_get_job_links), \
         patch.object(scraper, 'process_jobs_concurrently', fake_process_jobs_concurrently), \
         patch('aujobsscraper.scrapers.seek_scraper.async_playwright') as mock_pw:
        mock_pw.return_value.__aenter__.return_value = mock_p
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        # Only iterate one page (settings.max_pages may be > 1 in test env,
        # but _get_job_links returns same links every call — use max_pages=1 via settings patch)
        with patch('aujobsscraper.scrapers.seek_scraper.settings') as mock_settings:
            mock_settings.initial_run = False
            mock_settings.search_keywords = ["software engineer"]
            mock_settings.max_pages = 1
            mock_settings.days_from_posted = 7
            mock_settings.concurrency = 2

            async for _ in scraper.scrape(skip_urls=skip_urls):
                pass

    assert "https://seek.com.au/job/1" not in processed_urls
    assert "https://seek.com.au/job/2" in processed_urls
```

**Step 2: Run to confirm tests fail**

```bash
pytest tests/unit/test_seek_scraper.py -v
```

Expected: `test_seek_scrape_is_async_generator` FAIL (currently a coroutine), others error.

**Step 3: Convert `seek_scraper.py`**

Change the `scrape()` method — three edits only:

1. Remove `return self._results` at the end of the method
2. Before each `await self.process_jobs_concurrently(context, new_links)`, add:
   ```python
   batch_start = len(self._results)
   ```
3. After each `await self.process_jobs_concurrently(context, new_links)`, add:
   ```python
   batch = self._results[batch_start:]
   if batch:
       yield batch
   ```

Full updated inner loop (inside `for term in terms` → `for page_num in range(...)`):

```python
try:
    job_links = await self._get_job_links(page, url)
    if not job_links:
        self.logger.info("No more results found.")
        break

    new_links = [link for link in job_links if link not in skip_urls]
    skipped = len(job_links) - len(new_links)
    if skipped > 0:
        self.logger.info(f"Skipping {skipped} already-known URLs.")

    self.logger.info(f"Found {len(new_links)} new jobs on page {page_num}")
    batch_start = len(self._results)
    await self.process_jobs_concurrently(context, new_links)
    batch = self._results[batch_start:]
    if batch:
        yield batch

except Exception as e:
    self.logger.error(f"Error processing page {page_num}: {e}")
```

Remove the final `return self._results` line and update the log message at the end to use `len(self._results)` (still accurate since `_results` accumulates).

**Step 4: Run the tests**

```bash
pytest tests/unit/test_seek_scraper.py -v
```

Expected: all PASS

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/seek_scraper.py tests/unit/test_seek_scraper.py
git commit -m "feat: convert SeekScraper.scrape() to async generator"
```

---

### Task 3: Convert `GradConnectionScraper.scrape()` to async generator

**Files:**
- Modify: `aujobsscraper/scrapers/gradconnection_scraper.py`
- Test: `tests/unit/test_gradconnection_scraper.py` (create)

**Step 1: Write the failing test**

```python
# tests/unit/test_gradconnection_scraper.py
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aujobsscraper.scrapers.gradconnection_scraper import GradConnectionScraper


def test_gradconnection_scrape_is_async_generator():
    scraper = GradConnectionScraper()
    gen = scraper.scrape()
    assert inspect.isasyncgen(gen)


@pytest.mark.asyncio
async def test_gradconnection_scrape_yields_one_batch_per_page():
    scraper = GradConnectionScraper()

    link_responses = [
        ["https://au.gradconnection.com/job/1", "https://au.gradconnection.com/job/2"],
        [],
    ]
    link_call_count = 0

    async def fake_get_job_links(page, url):
        nonlocal link_call_count
        links = link_responses[min(link_call_count, len(link_responses) - 1)]
        link_call_count += 1
        return links

    async def fake_process_jobs_concurrently(context, urls):
        for url in urls:
            job = MagicMock()
            scraper._results.append(job)

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch.object(scraper, '_get_job_links', fake_get_job_links), \
         patch.object(scraper, 'process_jobs_concurrently', fake_process_jobs_concurrently), \
         patch('aujobsscraper.scrapers.gradconnection_scraper.async_playwright') as mock_pw, \
         patch('aujobsscraper.scrapers.gradconnection_scraper.settings') as mock_settings:
        mock_pw.return_value.__aenter__.return_value = mock_p
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_settings.gradconnection_keywords = ["software engineer"]
        mock_settings.initial_run = False
        mock_settings.max_pages = 5
        mock_settings.gradconnection_regular_max_pages = 5
        mock_settings.concurrency = 2

        batches = []
        async for batch in scraper.scrape():
            batches.append(list(batch))

    assert len(batches) == 1
    assert len(batches[0]) == 2
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_gradconnection_scraper.py::test_gradconnection_scrape_is_async_generator -v
```

Expected: FAIL

**Step 3: Apply the same three-edit pattern to `gradconnection_scraper.py`**

Inside the `try:` block of the page loop, add `batch_start` before and `yield batch` after `process_jobs_concurrently`. Remove `return self._results`.

```python
# Before:
await self.process_jobs_concurrently(context, new_links)

# After:
batch_start = len(self._results)
await self.process_jobs_concurrently(context, new_links)
batch = self._results[batch_start:]
if batch:
    yield batch
```

Remove the `return self._results` line at the end.

**Step 4: Run the tests**

```bash
pytest tests/unit/test_gradconnection_scraper.py -v
```

Expected: all PASS

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/gradconnection_scraper.py tests/unit/test_gradconnection_scraper.py
git commit -m "feat: convert GradConnectionScraper.scrape() to async generator"
```

---

### Task 4: Convert `ProspleScraper.scrape()` to async generator

**Files:**
- Modify: `aujobsscraper/scrapers/prosple_scraper.py`
- Test: `tests/unit/test_prosple_scraper.py` (create)

**Step 1: Write the failing test**

```python
# tests/unit/test_prosple_scraper.py
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aujobsscraper.scrapers.prosple_scraper import ProspleScraper


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
        mock_settings.prosple_regular_max_pages = 1  # one page only
        mock_settings.prosple_items_per_page = 10
        mock_settings.concurrency = 2

        batches = []
        async for batch in scraper.scrape():
            batches.append(list(batch))

    assert len(batches) == 1
    assert len(batches[0]) == 1
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_prosple_scraper.py::test_prosple_scrape_is_async_generator -v
```

Expected: FAIL

**Step 3: Apply the three-edit pattern to `prosple_scraper.py`**

`ProspleScraper.scrape()` has a slightly different structure — it uses a `while page_count < max_pages` loop and has a top-level `try/except` wrapping `async with async_playwright()`. The edit is the same:

```python
# Before (inside the inner try:):
await self.process_jobs_concurrently(context, new_links)

# After:
batch_start = len(self._results)
await self.process_jobs_concurrently(context, new_links)
batch = self._results[batch_start:]
if batch:
    yield batch
```

There are two `return self._results` statements in `ProspleScraper.scrape()` (one in the outer `except`, one at the end). Remove both — an async generator cannot have `return <value>`, only a bare `return` to stop iteration early. Replace them with bare `return` statements:

```python
# Before:
except Exception as e:
    self.logger.error(f"Unhandled error in scrape(): {e}")
    return self._results   # ← change to: return

return self._results  # ← remove entirely (generator ends naturally)
```

**Step 4: Run the tests**

```bash
pytest tests/unit/test_prosple_scraper.py -v
```

Expected: all PASS

**Step 5: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all PASS

**Step 6: Commit**

```bash
git add aujobsscraper/scrapers/prosple_scraper.py tests/unit/test_prosple_scraper.py
git commit -m "feat: convert ProspleScraper.scrape() to async generator"
```

---

### Task 5: Bump version and reinstall

**Files:**
- Modify: `pyproject.toml` (or `setup.py` / wherever version is declared)

**Step 1: Bump the patch version**

Find the version field (e.g. `version = "0.1.1"`) and increment it:

```toml
version = "0.1.2"
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.1.2 for async generator scrape interface"
git tag v0.1.2
git push && git push --tags
```

**Step 3: Reinstall in the JobTrendsAU workspace**

In the JobTrendsAU repo:

```bash
pip install git+https://github.com/RyanKuang2004/AUJobsScraper.git@v0.1.2
```

Verify installation:

```bash
pip show aujobsscraper | grep Version
# Expected: Version: 0.1.2
```

# All Scrapers `.env` Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all scrapers and runner scripts use `.env`/`SCRAPER_*` configuration as the default source of operational settings, with explicit constructor overrides still supported.

**Architecture:** Keep a single source of truth in `aujobsscraper/config.py` (`ScraperSettings`) and wire each scraper to consume defaults from it. Preserve per-call overrides by treating constructor args as higher priority than settings defaults. Remove hardcoded runtime values from `scripts/` so host repos can configure behavior without code edits.

**Tech Stack:** Python 3.12+, `pydantic-settings`, `python-dotenv`, `pytest`, Playwright, JobSpy.

---

### Task 1: Expand and Normalize Settings Schema

**Files:**
- Modify: `aujobsscraper/config.py`
- Test: `tests/unit/test_config.py` (new)

**Step 1: Write the failing test**

```python
import os
from aujobsscraper.config import ScraperSettings

def test_config_parses_json_list_keywords(monkeypatch):
    monkeypatch.setenv("SCRAPER_SEARCH_KEYWORDS", '["software engineer","data engineer"]')
    settings = ScraperSettings()
    assert settings.search_keywords == ["software engineer", "data engineer"]

def test_config_rejects_python_style_list(monkeypatch):
    monkeypatch.setenv("SCRAPER_SEARCH_KEYWORDS", "['software engineer','data engineer']")
    try:
        ScraperSettings()
        assert False, "Expected parse failure"
    except Exception:
        assert True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`  
Expected: FAIL because file/fields do not yet exist or behavior not yet codified.

**Step 3: Write minimal implementation**

Add settings fields needed to eliminate hardcoded runtime knobs:

```python
indeed_hours_old: int = Field(default=72)
indeed_results_wanted: int = Field(default=20)
indeed_results_wanted_total: int | None = Field(default=100)
indeed_term_concurrency: int = Field(default=2)
indeed_location: str = Field(default="")
indeed_country: str = Field(default="Australia")
prosple_items_per_page: int = Field(default=20)
```

Keep `env_prefix="SCRAPER_"` and add clarifying module docstring comments for JSON list format requirements.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add aujobsscraper/config.py tests/unit/test_config.py
git commit -m "feat: expand scraper settings schema for env-driven runtime config"
```

### Task 2: Move Indeed Defaults to Settings and Keep Overrides

**Files:**
- Modify: `aujobsscraper/scrapers/indeed_scraper.py`
- Modify: `scripts/run_all_scrapers.py`
- Test: `tests/unit/test_indeed_scraper.py`

**Step 1: Write the failing test**

```python
def test_indeed_uses_settings_defaults_when_args_not_provided(monkeypatch):
    from aujobsscraper.scrapers.indeed_scraper import IndeedScraper
    from aujobsscraper.config import settings
    monkeypatch.setattr(settings, "indeed_hours_old", 24)
    scraper = IndeedScraper()
    assert scraper.hours_old == 24
```

Add a second test verifying explicit constructor args override settings defaults.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_indeed_scraper.py -v`  
Expected: FAIL because constructor currently hardcodes defaults (`72`, etc.).

**Step 3: Write minimal implementation**

In `IndeedScraper.__init__`, change optional arguments from hardcoded defaults to `None` and resolve values from settings:

```python
self.hours_old = hours_old if hours_old is not None else settings.indeed_hours_old
```

Apply same pattern for `results_wanted`, `results_wanted_total`, `term_concurrency`, `location`, and `country_indeed`.

In `scripts/run_all_scrapers.py`, remove hardcoded constructor values:

```python
scraper = IndeedScraper()
```

or map CLI args later if needed.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_indeed_scraper.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/indeed_scraper.py scripts/run_all_scrapers.py tests/unit/test_indeed_scraper.py
git commit -m "feat: make indeed runtime defaults env-driven with override support"
```

### Task 3: Apply Settings Consistently in Prosple/Seek/GradConnection

**Files:**
- Modify: `aujobsscraper/scrapers/prosple_scraper.py`
- Modify: `aujobsscraper/scrapers/seek_scraper.py` (small cleanup only if needed)
- Modify: `aujobsscraper/scrapers/gradconnection_scraper.py` (small cleanup only if needed)
- Test: `tests/unit/test_prosple_scraper.py`

**Step 1: Write the failing test**

```python
def test_prosple_respects_max_pages(monkeypatch):
    from aujobsscraper.config import settings
    monkeypatch.setattr(settings, "max_pages", 1)
    # assert pagination loop stops after first page fetch
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_prosple_scraper.py -v`  
Expected: FAIL because current Prosple loop is unbounded by settings.

**Step 3: Write minimal implementation**

Use settings in Prosple pagination loop:
- `items_per_page = settings.prosple_items_per_page`
- stop loop when fetched page count reaches `settings.max_pages`

For Seek/GradConnection, verify no hardcoded alternatives bypass settings; keep existing behavior where they already read `settings`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_prosple_scraper.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/prosple_scraper.py tests/unit/test_prosple_scraper.py
git commit -m "feat: wire prosple pagination controls to shared env settings"
```

### Task 4: Add Script-Level Config Surface for Host Repos

**Files:**
- Modify: `scripts/run_all_scrapers.py`
- Modify: `scripts/run_all_scrapers_first_iteration.py`
- Test: `tests/unit/test_run_all_scrapers_first_iteration.py`

**Step 1: Write the failing test**

```python
def test_run_all_uses_settings_backed_defaults_for_indeed_factory(...):
    # assert script does not hardcode results_wanted=20/results_wanted_total=100
```

Add one CLI test if adding new flags (for example `--indeed-hours-old`).

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_run_all_scrapers_first_iteration.py -v`  
Expected: FAIL where script behavior still depends on hardcoded values.

**Step 3: Write minimal implementation**

Pick one consistent approach:
- Default-only path: remove all script hardcoded scraper knobs so settings drive behavior.
- Optional override path: add CLI flags that override settings at runtime; only set scraper args when flags are provided.

Keep first-iteration script behavior intact (single term/page preview), but source base values from settings before narrowing.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_run_all_scrapers_first_iteration.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/run_all_scrapers.py scripts/run_all_scrapers_first_iteration.py tests/unit/test_run_all_scrapers_first_iteration.py
git commit -m "feat: remove hardcoded runner scraper settings in favor of env defaults"
```

### Task 5: Documentation and End-to-End Verification

**Files:**
- Modify: `README.md`
- Optional Create: `.env.example`
- Test: `tests/unit/test_run_all_scrapers_first_iteration.py` (if docs-driven behavior adds expectations)

**Step 1: Write/update docs-first checks**

Document exact env formats and each scraper-relevant var:

```dotenv
SCRAPER_SEARCH_KEYWORDS=["software engineer","data engineer"]
SCRAPER_GRADCONNECTION_KEYWORDS=["software engineer","data science"]
SCRAPER_MAX_PAGES=3
SCRAPER_DAYS_FROM_POSTED=2
SCRAPER_INITIAL_DAYS_FROM_POSTED=31
SCRAPER_INITIAL_RUN=false
SCRAPER_CONCURRENCY=5
SCRAPER_INDEED_HOURS_OLD=24
SCRAPER_INDEED_RESULTS_WANTED=30
SCRAPER_INDEED_RESULTS_WANTED_TOTAL=120
SCRAPER_INDEED_TERM_CONCURRENCY=2
SCRAPER_INDEED_LOCATION=
SCRAPER_INDEED_COUNTRY=Australia
SCRAPER_PROSPLE_ITEMS_PER_PAGE=20
```

**Step 2: Run full targeted test suite**

Run:
- `pytest tests/unit/test_config.py -v`
- `pytest tests/unit/test_indeed_scraper.py -v`
- `pytest tests/unit/test_prosple_scraper.py -v`
- `pytest tests/unit/test_run_all_scrapers_first_iteration.py -v`

Expected: PASS.

**Step 3: Run broader regression**

Run: `pytest tests/unit -v`  
Expected: PASS with no scraper behavior regressions.

**Step 4: Smoke test scripts**

Run:
- `python scripts/run_all_scrapers.py --help`
- `python scripts/run_all_scrapers_first_iteration.py --help`

Expected: Commands execute and usage text matches new config strategy.

**Step 5: Commit**

```bash
git add README.md .env.example tests/unit/test_config.py
git commit -m "docs: document unified env configuration for all scrapers"
```

## Notes for Implementation

- Keep backward compatibility where possible: constructor args should override env defaults, not the other way around.
- Do not break existing callers that instantiate `IndeedScraper(search_term=...)`.
- Prefer deterministic tests via monkeypatching settings instead of requiring real `.env` reads.
- Maintain DRY by keeping defaults only in `ScraperSettings`, not repeated in scripts/scrapers.

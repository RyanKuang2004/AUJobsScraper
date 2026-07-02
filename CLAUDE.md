# AUJobsScraper — Codebase Guide

## Project Overview

A Python library that scrapes Australian job boards and returns structured `JobPosting` objects. Consumers import the library and call scrapers; this repo does not include a database layer or UI.

**Supported platforms**: Seek, GradConnection, Prosple, Indeed

---

## Architecture

```
aujobsscraper/           # Installable library (pip install -e .)
  __init__.py            # Lazy public API: JobPosting, Location, *Scraper classes
  config.py              # ScraperSettings (pydantic-settings, SCRAPER_* env vars)
  models/
    job.py               # JobPosting — the canonical output model
    location.py          # Location (city, state)
    fingerprint.py       # FingerprintGenerator — deduplication hash
  scrapers/
    base_scraper.py      # BaseScraper — shared browser setup, concurrency, collect/validate
    seek_scraper.py
    gradconnection_scraper.py
    prosple_scraper.py
    indeed_scraper.py
  utils/
    scraper_utils.py     # normalize_locations()
    salary_parser.py     # Salary extraction helpers
    constants.py         # Shared lookup tables (states, etc.)

scripts/
  run_all_scrapers.py    # CLI: run any/all scrapers in preview mode (--scrapers, --output)

tests/
  unit/                  # Pure-unit tests (no network)
  integration/           # Live network tests (slow, opt-in)

docs/
  plans/                 # Historical design docs — read-only reference
  salary_extraction.md
```

---

## Key Design Decisions

### Async generator interface
`BaseScraper.scrape(skip_urls)` is an **async generator** that yields `List[JobPosting]` — one batch per listing page. Callers iterate with `async for batch in scraper.scrape()`. This keeps memory bounded for large runs.

### skip_urls deduplication
Each scraper accepts `skip_urls: Set[str]` so the orchestrator can pass already-seen URLs and prevent cross-scraper duplicates without a database.

### Configuration via environment
All tunable knobs live in `ScraperSettings` (`config.py`) and are read from `SCRAPER_*` env vars. Callers load their own `.env` before importing — this library never calls `dotenv.load_dotenv()`.

### No LLM fields in JobPosting
`JobPosting` only carries fields a scraper can populate directly. Downstream enrichment (LLM extraction, classification) is the consumer's responsibility.

---

## Adding a New Scraper

1. Create `aujobsscraper/scrapers/<name>_scraper.py`
2. Subclass `BaseScraper` and implement:
   - `scrape(self, skip_urls=None) -> AsyncGenerator[List[JobPosting], None]`
   - `_process_job(self, page, url: str) -> None`
   - Use `self._build_job_posting(...)` and `self._collect_job(...)` from the base
3. Export from `aujobsscraper/__init__.py` (add to `__all__` and `_EXPORT_TO_MODULE`)
4. Register in `scripts/run_all_scrapers.py` (`DEFAULT_SCRAPERS` tuple and `_build_scraper`)
5. Add unit tests under `tests/unit/test_<name>_scraper.py`

---

## Commands

```bash
# Install in editable mode (required before running tests or scripts)
pip install -e .

# Run all scrapers (preview mode — first page per keyword)
python scripts/run_all_scrapers.py
python scripts/run_all_scrapers.py --scrapers seek,prosple --output results/out.json

# Run tests
pytest tests/unit/          # fast, no network
pytest tests/integration/   # slow, requires network
pytest                      # all
```

---

## Environment Variables

All optional — defaults are in `config.py`.

| Variable | Default | Purpose |
|---|---|---|
| `SCRAPER_SEARCH_KEYWORDS` | `["software engineer", ...]` | JSON array of search terms |
| `SCRAPER_MAX_PAGES` | `20` | Max listing pages per keyword |
| `SCRAPER_DAYS_FROM_POSTED` | `2` | Recency filter (regular runs) |
| `SCRAPER_INITIAL_RUN` | `false` | Use wider recency window |
| `SCRAPER_CONCURRENCY` | `5` | Concurrent job-page fetches |
| `SCRAPER_INDEED_HOURS_OLD` | `72` | Indeed recency filter |
| `SCRAPER_INDEED_RESULTS_WANTED` | `20` | Indeed results per term |

---

## Conventions

- **Naming**: scraper files are `<platform>_scraper.py`; test files are `test_<module>.py`
- **Logging**: each scraper gets `logging.getLogger(f"Scraper-{platform_name}")` — do not use `print()` inside the library
- **Pydantic models**: prefer `model_config = ConfigDict(...)` over inner `class Config` (existing `Location`/`JobPosting` have a deprecation warning — fix when touching those files)
- **No relative imports** inside the library; always use absolute `aujobsscraper.*` imports
- **scripts/** is not part of the installed package — it's runnable entry points only

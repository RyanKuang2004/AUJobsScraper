# Design: Salary Parsing Fix + Prosple/Indeed Initial Run

**Date:** 2026-02-25

## Problem Summary

Three related bugs:

1. **Salary validation crash** — GradConnection (and Prosple) pass raw salary dicts with string values like `"60,000"` to `JobPosting`, causing Pydantic `float_parsing` errors. The `salary` field must always be `{"annual_min": float, "annual_max": float}`.

2. **Prosple no initial run logic** — Prosple always paginates up to `max_pages` regardless of `settings.initial_run`. On regular runs it should limit to a small number of pages (recent jobs only).

3. **Indeed no initial run logic** — Indeed uses a fixed `hours_old` (default 72h) with no differentiation for initial vs regular runs. On initial run it should look back much further (2000 hours ≈ 83 days).

---

## Fix 1: Salary Parsing

### GradConnection (`gradconnection_scraper._extract_salary`)

**Root cause:** `normalize_salary("60,000 - 80,000")` sometimes returns `None` (the sanity check `min_sal < 10000` can fail if parsing goes wrong), and a separate code path was passing the raw `{"min_salary": "60,000", "max_salary": "80,000", "details": ""}` dict through to `JobPosting`.

**Fix:** Parse `min_salary`/`max_salary` directly with comma stripping and explicit `float()` conversion. Skip `details` key — only produce `{"annual_min": float, "annual_max": float}`.

```python
min_salary = salary.get("min_salary")
max_salary = salary.get("max_salary")
if min_salary is not None or max_salary is not None:
    def _safe_float(v):
        if v is None:
            return None
        try:
            return float(str(v).replace(",", "").strip())
        except (ValueError, TypeError):
            return None
    low = _safe_float(min_salary)
    high = _safe_float(max_salary)
    if low is not None and high is not None:
        return {"annual_min": min(low, high), "annual_max": max(low, high)}
```

### Prosple (`prosple_scraper._extract_salary`)

**Root cause:** `float(min_value)` called directly on JSON-LD `minValue`/`maxValue` which may be comma-formatted strings like `"70,000"`.

**Fix:** Strip commas before `float()` conversion, same safe helper pattern.

### JobPosting model

Add `description=` kwarg to all `Field()` definitions as specified. No structural change.

---

## Fix 2: Prosple Initial Run

**Approach:** Add `prosple_regular_max_pages: int = Field(default=3)` to `ScraperSettings`. In `ProspleScraper.scrape()`, select page limit based on `settings.initial_run`:

```python
max_pages = settings.max_pages if settings.initial_run else settings.prosple_regular_max_pages
```

This mirrors Seek's pattern: initial run = full depth (20 pages), regular run = shallow (3 pages, recent listings only).

---

## Fix 3: Indeed Initial Run

**Approach:** Add `indeed_initial_hours_old: int = Field(default=2000)` to `ScraperSettings`. In `IndeedScraper.__init__()`, select `hours_old` based on `settings.initial_run`:

```python
if hours_old is not None:
    self.hours_old = hours_old
elif settings.initial_run:
    self.hours_old = settings.indeed_initial_hours_old  # 2000
else:
    self.hours_old = settings.indeed_hours_old  # 72
```

---

## Files Changed

| File | Change |
|------|--------|
| `aujobsscraper/models/job.py` | Add `description=` to Field() calls |
| `aujobsscraper/config.py` | Add `prosple_regular_max_pages`, `indeed_initial_hours_old` |
| `aujobsscraper/scrapers/gradconnection_scraper.py` | Fix `_extract_salary` float conversion |
| `aujobsscraper/scrapers/prosple_scraper.py` | Fix `_extract_salary` float conversion + add initial run page limit |
| `aujobsscraper/scrapers/indeed_scraper.py` | Add initial run `hours_old` selection |
| `tests/unit/test_gradconnection_scraper.py` | Update/add salary tests |
| `tests/unit/test_prosple_scraper.py` | Update/add salary + initial run tests |
| `tests/unit/test_indeed_scraper.py` | Add initial run hours_old test |

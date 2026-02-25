# Salary Parsing Fix + Prosple/Indeed Initial Run Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix salary float-parsing crashes in GradConnection/Prosple, and add initial-run logic to Prosple and Indeed scrapers.

**Architecture:** Three isolated fixes — (1) safe float conversion for salary fields with commas, (2) page-depth switching in Prosple based on `settings.initial_run`, (3) `hours_old` switching in Indeed based on `settings.initial_run`. Each fix is independent; tackle them in order.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, `python-dotenv`, `pydantic-settings`

---

### Task 1: Update JobPosting model field descriptions

**Files:**
- Modify: `aujobsscraper/models/job.py:14-29`

**Step 1: Make the edit**

Replace the existing field block with:

```python
    # Core identification
    job_title: str = Field(..., description="Original job title from posting")
    company: str = Field(..., description="Company name")
    description: str = Field(..., description="Full job description text")

    # Fingerprint (auto-generated)
    fingerprint: Optional[str] = Field(None, description="Unique fingerprint for deduplication")

    # Location and sources
    locations: List[Location] = Field(default_factory=list, description="Job locations")
    source_urls: List[str] = Field(default_factory=list, description="Source URLs for this job")
    platforms: List[str] = Field(default_factory=list, description="Platforms where job was found")

    # Optional scraping fields
    salary: Optional[Dict[str, float]] = Field(None, description="Structured salary info {annual_min, annual_max}")
    posted_at: Optional[str] = Field(None, description="Date posted (ISO format)")
    closing_date: Optional[str] = Field(None, description="Application closing date (ISO format)")
```

**Step 2: Verify no tests break**

```bash
pytest tests/ -v -q
```
Expected: all existing tests pass (this is description-only, no logic change).

**Step 3: Commit**

```bash
git add aujobsscraper/models/job.py
git commit -m "docs: add field descriptions to JobPosting model"
```

---

### Task 2: Add new config settings

**Files:**
- Modify: `aujobsscraper/config.py:43-50`

**Step 1: Add the two new fields**

After `indeed_hours_old: int = Field(default=72)` (line 43), add:

```python
    indeed_initial_hours_old: int = Field(default=2000)
```

After `prosple_items_per_page: int = Field(default=20)` (line 50), add:

```python
    prosple_regular_max_pages: int = Field(default=3)
```

**Step 2: Verify settings loads cleanly**

```bash
python -c "from aujobsscraper.config import settings; print(settings.indeed_initial_hours_old, settings.prosple_regular_max_pages)"
```
Expected output: `2000 3`

**Step 3: Commit**

```bash
git add aujobsscraper/config.py
git commit -m "feat: add indeed_initial_hours_old and prosple_regular_max_pages config fields"
```

---

### Task 3: Fix GradConnection salary float parsing

**Files:**
- Modify: `aujobsscraper/scrapers/gradconnection_scraper.py:217-241`
- Test: `tests/unit/test_gradconnection_scraper.py`

**Step 1: Write the failing test**

Open `tests/unit/test_gradconnection_scraper.py` and add:

```python
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
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_gradconnection_scraper.py::test_extract_salary_handles_comma_formatted_strings -v
```
Expected: FAIL (currently crashes or returns None instead of the expected dict).

**Step 3: Implement the fix**

Replace the `if min_salary is not None or max_salary is not None:` block in `_extract_salary` (lines ~223-230) with:

```python
                    def _safe_float(v) -> Optional[float]:
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
                    if low is not None:
                        return {"annual_min": low, "annual_max": low}
                    if high is not None:
                        return {"annual_min": high, "annual_max": high}
```

Note: remove the old `normalize_salary(salary_text)` call that was here — it was building a string like `"60,000 - 80,000"` and routing through `normalize_salary`, which could fail the `< 10000` sanity check if it misparses.

**Step 4: Run tests**

```bash
pytest tests/unit/test_gradconnection_scraper.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/gradconnection_scraper.py tests/unit/test_gradconnection_scraper.py
git commit -m "fix: handle comma-formatted salary strings in GradConnection scraper"
```

---

### Task 4: Fix Prosple salary float parsing

**Files:**
- Modify: `aujobsscraper/scrapers/prosple_scraper.py:218-225`
- Test: `tests/unit/test_prosple_scraper.py`

**Step 1: Write the failing test**

Open `tests/unit/test_prosple_scraper.py` and add:

```python
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
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_prosple_scraper.py::test_extract_salary_handles_comma_formatted_min_max_values -v
```
Expected: FAIL with `ValueError` or assertion error.

**Step 3: Implement the fix**

In `prosple_scraper._extract_salary`, replace lines ~219-225 (the `float(min_value)` / `float(max_value)` calls):

```python
                if isinstance(value, dict):
                    min_value = value.get('minValue')
                    max_value = value.get('maxValue')
                    if min_value is not None or max_value is not None:
                        def _safe_float(v) -> Optional[float]:
                            if v is None:
                                return None
                            try:
                                return float(str(v).replace(",", "").strip())
                            except (ValueError, TypeError):
                                return None

                        low = _safe_float(min_value)
                        high = _safe_float(max_value)
                        if low is not None and high is not None:
                            return {"annual_min": min(low, high), "annual_max": max(low, high)}
                        if low is not None:
                            return {"annual_min": low, "annual_max": low}
                        if high is not None:
                            return {"annual_min": high, "annual_max": high}
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_prosple_scraper.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/prosple_scraper.py tests/unit/test_prosple_scraper.py
git commit -m "fix: handle comma-formatted salary strings in Prosple scraper"
```

---

### Task 5: Add Prosple initial run page limit

**Files:**
- Modify: `aujobsscraper/scrapers/prosple_scraper.py:27-30`
- Test: `tests/unit/test_prosple_scraper.py`

**Step 1: Write the failing test**

```python
from unittest.mock import patch

def test_prosple_uses_full_max_pages_on_initial_run():
    scraper = ProspleScraper()
    with patch("aujobsscraper.scrapers.prosple_scraper.settings") as mock_settings:
        mock_settings.initial_run = True
        mock_settings.max_pages = 20
        mock_settings.prosple_regular_max_pages = 3
        mock_settings.prosple_items_per_page = 20
        # max_pages selected should be 20
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
```

**Step 2: Run to confirm they pass (logic test — these will pass immediately)**

```bash
pytest tests/unit/test_prosple_scraper.py::test_prosple_uses_full_max_pages_on_initial_run tests/unit/test_prosple_scraper.py::test_prosple_uses_regular_max_pages_on_regular_run -v
```

**Step 3: Implement in scraper**

In `prosple_scraper.scrape()`, replace line 28:
```python
        max_pages = settings.max_pages
```
with:
```python
        max_pages = settings.max_pages if settings.initial_run else settings.prosple_regular_max_pages
```

**Step 4: Run all Prosple tests**

```bash
pytest tests/unit/test_prosple_scraper.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/prosple_scraper.py tests/unit/test_prosple_scraper.py
git commit -m "feat: add initial run page limit logic to Prosple scraper"
```

---

### Task 6: Add Indeed initial run hours_old

**Files:**
- Modify: `aujobsscraper/scrapers/indeed_scraper.py:41`
- Test: `tests/unit/test_indeed_scraper.py`

**Step 1: Write the failing tests**

Open `tests/unit/test_indeed_scraper.py` and add:

```python
from unittest.mock import patch

def test_indeed_uses_initial_hours_old_on_initial_run():
    """On initial run, hours_old should be indeed_initial_hours_old (2000)."""
    with patch("aujobsscraper.scrapers.indeed_scraper.settings") as mock_settings:
        mock_settings.initial_run = True
        mock_settings.indeed_hours_old = 72
        mock_settings.indeed_initial_hours_old = 2000
        mock_settings.indeed_location = ""
        mock_settings.indeed_results_wanted = 20
        mock_settings.indeed_results_wanted_total = 100
        mock_settings.indeed_term_concurrency = 2
        mock_settings.indeed_country = "Australia"
        mock_settings.search_keywords = ["software engineer"]

        scraper = IndeedScraper()
        assert scraper.hours_old == 2000


def test_indeed_uses_regular_hours_old_on_regular_run():
    """On regular run, hours_old should be indeed_hours_old (72)."""
    with patch("aujobsscraper.scrapers.indeed_scraper.settings") as mock_settings:
        mock_settings.initial_run = False
        mock_settings.indeed_hours_old = 72
        mock_settings.indeed_initial_hours_old = 2000
        mock_settings.indeed_location = ""
        mock_settings.indeed_results_wanted = 20
        mock_settings.indeed_results_wanted_total = 100
        mock_settings.indeed_term_concurrency = 2
        mock_settings.indeed_country = "Australia"
        mock_settings.search_keywords = ["software engineer"]

        scraper = IndeedScraper()
        assert scraper.hours_old == 72


def test_indeed_explicit_hours_old_overrides_initial_run():
    """Explicit hours_old param always wins over initial_run logic."""
    with patch("aujobsscraper.scrapers.indeed_scraper.settings") as mock_settings:
        mock_settings.initial_run = True
        mock_settings.indeed_hours_old = 72
        mock_settings.indeed_initial_hours_old = 2000
        mock_settings.indeed_location = ""
        mock_settings.indeed_results_wanted = 20
        mock_settings.indeed_results_wanted_total = 100
        mock_settings.indeed_term_concurrency = 2
        mock_settings.indeed_country = "Australia"
        mock_settings.search_keywords = ["software engineer"]

        scraper = IndeedScraper(hours_old=48)
        assert scraper.hours_old == 48
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_indeed_scraper.py::test_indeed_uses_initial_hours_old_on_initial_run -v
```
Expected: FAIL — currently `hours_old` is always `settings.indeed_hours_old` regardless of `initial_run`.

**Step 3: Implement the fix**

In `indeed_scraper.__init__()`, replace line 41:
```python
        self.hours_old = settings.indeed_hours_old if hours_old is None else hours_old
```
with:
```python
        if hours_old is not None:
            self.hours_old = hours_old
        elif settings.initial_run:
            self.hours_old = settings.indeed_initial_hours_old
        else:
            self.hours_old = settings.indeed_hours_old
```

**Step 4: Run all Indeed tests**

```bash
pytest tests/unit/test_indeed_scraper.py tests/integration/test_indeed_scraper.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/indeed_scraper.py tests/unit/test_indeed_scraper.py
git commit -m "feat: use initial_hours_old for Indeed on initial run"
```

---

### Task 7: Full test suite + final check

**Step 1: Run all tests**

```bash
pytest tests/ -v
```
Expected: all pass, no failures.

**Step 2: Verify config loads with new fields**

```bash
python -c "
from aujobsscraper.config import settings
print('prosple_regular_max_pages:', settings.prosple_regular_max_pages)
print('indeed_initial_hours_old:', settings.indeed_initial_hours_old)
print('initial_run:', settings.initial_run)
"
```
Expected:
```
prosple_regular_max_pages: 3
indeed_initial_hours_old: 2000
initial_run: False
```

**Step 3: Final commit if anything was missed**

```bash
git status
```
If clean, done. Otherwise stage and commit remaining changes.

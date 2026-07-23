# description_markdown Field Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new, purely additive `description_markdown` field to `JobPosting`, populated via the `markdownify` library, so consumers get high-fidelity Markdown for display without touching the existing `description` field.

**Architecture:** A new `html_to_markdown()` utility wraps `markdownify` with fixed formatting options and swallows conversion errors. Each scraper that currently extracts raw HTML and immediately collapses it via `remove_html_tags()` (Seek, GradConnection, Prosple) is refactored to extract the raw HTML once into a shared helper, then feed that same HTML to both `remove_html_tags()` (existing `description`) and `html_to_markdown()` (new `description_markdown`). Indeed already receives markdown-formatted text from `jobspy`, so it just copies `description` into `description_markdown` — no new conversion needed there.

**Tech Stack:** Python 3.12, BeautifulSoup4 + lxml, `markdownify` (new dependency), pydantic, pytest + pytest-asyncio.

## Global Constraints

- `description` field content/format must not change for any scraper.
- No raw HTML is persisted as a stored field — only `description` and `description_markdown`.
- `html_to_markdown()` must never raise — on any conversion failure it returns `""`.
- `description_markdown` is `Optional[str]`, defaults to `None`, and is never required by `JobPosting.validate()`.
- Follow existing project conventions: absolute `aujobsscraper.*` imports, no `print()`, loggers via `logging.getLogger(f"Scraper-{platform_name}")` (already established, not touched by this plan).

---

### Task 1: Add `markdownify` dependency and `html_to_markdown()` utility

**Files:**
- Modify: `pyproject.toml`
- Modify: `aujobsscraper/utils/scraper_utils.py`
- Modify: `aujobsscraper/utils/__init__.py`
- Test: `tests/unit/test_scraper_utils.py`

**Interfaces:**
- Produces: `html_to_markdown(html: str) -> str` in `aujobsscraper.utils.scraper_utils`, re-exported from `aujobsscraper.utils`. Returns `""` for empty/falsy input and on any internal conversion exception. Never raises.

- [ ] **Step 1: Add the dependency**

Edit `pyproject.toml` — add `"markdownify>=0.13.0",` to the `dependencies` list (after `"python-jobspy>=1.1.82",`):

```toml
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "playwright>=1.40.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.1.0",
    "python-jobspy>=1.1.82",
    "markdownify>=0.13.0",
]
```

Then install it into the active environment:

Run: `pip install -e .`
Expected: install succeeds, `markdownify` appears in `pip show markdownify`.

- [ ] **Step 2: Write the failing tests**

Add to `tests/unit/test_scraper_utils.py` (append at end of file; keep the existing `from aujobsscraper.utils.scraper_utils import remove_html_tags, normalize_locations` import line and add a second import line above the new tests):

```python
from aujobsscraper.utils.scraper_utils import html_to_markdown


def test_html_to_markdown_converts_headings_and_lists():
    html = """
    <div>
      <h2>What You'll Do</h2>
      <ul>
        <li>Build APIs</li>
        <li>Review code</li>
      </ul>
    </div>
    """

    result = html_to_markdown(html)

    assert "## What You'll Do" in result
    assert "- Build APIs" in result
    assert "- Review code" in result


def test_html_to_markdown_preserves_links_and_emphasis():
    html = "<p>Apply via <a href='https://example.com/apply'>this link</a> and bring <em>enthusiasm</em>.</p>"

    result = html_to_markdown(html)

    assert "[this link](https://example.com/apply)" in result
    assert "_enthusiasm_" in result or "*enthusiasm*" in result


def test_html_to_markdown_strips_script_and_style_tags():
    html = "<div><style>.x{color:red}</style><script>alert('x')</script><p>Real content</p></div>"

    result = html_to_markdown(html)

    assert "Real content" in result
    assert "alert" not in result
    assert "color:red" not in result


def test_html_to_markdown_returns_empty_string_for_empty_input():
    assert html_to_markdown("") == ""
    assert html_to_markdown(None) == ""


def test_html_to_markdown_never_raises_on_malformed_html():
    result = html_to_markdown("<div><p>Unclosed paragraph<div>Nested badly</div>")
    assert isinstance(result, str)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_scraper_utils.py -v -k html_to_markdown`
Expected: FAIL — `ImportError: cannot import name 'html_to_markdown'`

- [ ] **Step 4: Implement `html_to_markdown()`**

Edit `aujobsscraper/utils/scraper_utils.py` — add the import at the top (alongside the existing `from bs4 import BeautifulSoup`) and the new function directly after `remove_html_tags()` (after line 110, before `def extract_salary_from_text`):

```python
from markdownify import markdownify as _markdownify
```

```python
def html_to_markdown(html: str) -> str:
    """
    Convert HTML content into Markdown using the markdownify library.

    Args:
        html: HTML content as a string

    Returns:
        Markdown text, or "" if input is empty or conversion fails.
    """
    if not html:
        return ""

    try:
        soup = BeautifulSoup(html, 'lxml')
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        return _markdownify(str(soup), heading_style="ATX", bullets="-").strip()
    except Exception:
        return ""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_scraper_utils.py -v -k html_to_markdown`
Expected: 5 passed

- [ ] **Step 6: Export from the utils package**

Edit `aujobsscraper/utils/__init__.py`:

```python
from aujobsscraper.utils.scraper_utils import (
    normalize_locations,
    remove_html_tags,
    html_to_markdown,
    calculate_posted_date,
    normalize_salary,
    extract_salary_from_text,
)

__all__ = [
    "normalize_locations",
    "remove_html_tags",
    "html_to_markdown",
    "calculate_posted_date",
    "normalize_salary",
    "extract_salary_from_text",
]
```

- [ ] **Step 7: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all tests pass (no regressions).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml aujobsscraper/utils/scraper_utils.py aujobsscraper/utils/__init__.py tests/unit/test_scraper_utils.py
git commit -m "feat: add html_to_markdown utility using markdownify"
```

---

### Task 2: Add `description_markdown` field to `JobPosting`

**Files:**
- Modify: `aujobsscraper/models/job.py`
- Test: `tests/unit/test_models.py`

**Interfaces:**
- Consumes: none (pure model change).
- Produces: `JobPosting.description_markdown: Optional[str]`, default `None`, not required by `JobPosting.validate()`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_models.py`:

```python
def test_job_posting_description_markdown_defaults_to_none():
    posting = JobPosting(
        job_title="Backend Engineer",
        company="Acme",
        description="A sufficiently long description for validation purposes.",
        locations=[],
        source_urls=["https://example.com/job/1"],
        platforms=["seek"],
    )
    assert posting.description_markdown is None


def test_job_posting_description_markdown_accepts_value():
    posting = JobPosting(
        job_title="Backend Engineer",
        company="Acme",
        description="A sufficiently long description for validation purposes.",
        description_markdown="## Responsibilities\n- Build things",
        locations=[],
        source_urls=["https://example.com/job/1"],
        platforms=["seek"],
    )
    assert posting.description_markdown == "## Responsibilities\n- Build things"


def test_job_posting_validate_does_not_require_description_markdown():
    posting = JobPosting(
        job_title="Backend Engineer",
        company="Acme",
        description="A sufficiently long description for validation purposes.",
        locations=[Location(city="Sydney", state="NSW")],
        source_urls=["https://example.com/job/1"],
        platforms=["seek"],
    )
    assert posting.validate() == []
```

Check the top of `tests/unit/test_models.py` already imports `JobPosting` and `Location`; if `Location` is not imported, add `from aujobsscraper.models.location import Location` alongside the existing `JobPosting` import.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_models.py -v -k description_markdown`
Expected: FAIL — `TypeError: JobPosting() got an unexpected keyword argument 'description_markdown'` (or pydantic validation error to that effect)

- [ ] **Step 3: Add the field**

Edit `aujobsscraper/models/job.py` — add the new field directly after the existing `description` field (line 16):

```python
    description: str = Field(..., description="Full job description text")
    description_markdown: Optional[str] = Field(
        None, description="Job description converted from HTML to Markdown for display"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_models.py -v -k description_markdown`
Expected: 3 passed

- [ ] **Step 5: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add aujobsscraper/models/job.py tests/unit/test_models.py
git commit -m "feat: add description_markdown field to JobPosting"
```

---

### Task 3: Thread `description_markdown` through `base_scraper._build_job_posting`

**Files:**
- Modify: `aujobsscraper/scrapers/base_scraper.py`
- Test: `tests/unit/test_base_scraper.py`

**Interfaces:**
- Consumes: `JobPosting.description_markdown` (Task 2).
- Produces: `BaseScraper._build_job_posting(..., description_markdown: Optional[str] = None, **optional_fields)` — callers pass it as a regular kwarg like `salary`/`posted_at`/`closing_date`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_base_scraper.py`:

```python
def test_build_job_posting_passes_through_description_markdown():
    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield

    scraper = MinimalScraper("test")
    posting = scraper._build_job_posting(
        job_title="Backend Engineer",
        company="Acme",
        raw_locations=["Sydney"],
        source_url="https://seek.com.au/job/1",
        description="A sufficiently long description for validation purposes.",
        description_markdown="## Responsibilities\n- Build things",
    )
    assert posting.description_markdown == "## Responsibilities\n- Build things"


def test_build_job_posting_defaults_description_markdown_to_none():
    class MinimalScraper(BaseScraper):
        async def scrape(self, skip_urls=None):
            raise NotImplementedError
            yield

    scraper = MinimalScraper("test")
    posting = scraper._build_job_posting(
        job_title="Backend Engineer",
        company="Acme",
        raw_locations=["Sydney"],
        source_url="https://seek.com.au/job/1",
        description="A sufficiently long description for validation purposes.",
    )
    assert posting.description_markdown is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_base_scraper.py -v -k description_markdown`
Expected: FAIL — `AssertionError: None != '## Responsibilities\n- Build things'` (the field is accepted as an unused kwarg in `**optional_fields` today but never passed to `JobPosting`, so it stays `None` even when supplied)

- [ ] **Step 3: Thread it through**

Edit `aujobsscraper/scrapers/base_scraper.py` — in `_build_job_posting` (lines 35-45), add the field to the `JobPosting(...)` construction:

```python
        return JobPosting(
            job_title=job_title,
            company=company,
            description=description,
            description_markdown=optional_fields.get("description_markdown"),
            locations=location_objs,
            source_urls=[source_url],
            platforms=[self.platform],
            salary=optional_fields.get("salary"),
            posted_at=optional_fields.get("posted_at"),
            closing_date=optional_fields.get("closing_date"),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_base_scraper.py -v -k description_markdown`
Expected: 2 passed

- [ ] **Step 5: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add aujobsscraper/scrapers/base_scraper.py tests/unit/test_base_scraper.py
git commit -m "feat: thread description_markdown through _build_job_posting"
```

---

### Task 4: Populate `description_markdown` in `SeekScraper`

**Files:**
- Modify: `aujobsscraper/scrapers/seek_scraper.py`
- Test: `tests/unit/test_seek_scraper.py`

**Interfaces:**
- Consumes: `html_to_markdown` (Task 1), `_build_job_posting(..., description_markdown=...)` (Task 3).
- Produces: `SeekScraper._get_description_html(soup) -> str` (raw HTML, reused internally) and `SeekScraper._extract_description_markdown(soup) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_seek_scraper.py`:

```python
def test_extract_description_markdown_converts_job_ad_details():
    scraper = SeekScraper()
    soup = BeautifulSoup(
        '<div data-automation="jobAdDetails"><h2>About the role</h2>'
        '<ul><li>Ship features</li></ul></div>',
        "lxml",
    )

    markdown = scraper._extract_description_markdown(soup)

    assert "## About the role" in markdown
    assert "- Ship features" in markdown


def test_extract_description_and_markdown_share_same_source_element():
    scraper = SeekScraper()
    soup = BeautifulSoup(
        '<div data-automation="jobAdDetails"><p>Great <a href="https://example.com">opportunity</a></p></div>',
        "lxml",
    )

    plain = scraper._extract_description(soup)
    markdown = scraper._extract_description_markdown(soup)

    assert "opportunity" in plain
    assert "[opportunity](https://example.com)" in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_seek_scraper.py -v -k description_markdown`
Expected: FAIL — `AttributeError: 'SeekScraper' object has no attribute '_extract_description_markdown'`

- [ ] **Step 3: Implement the helper and wire it in**

Edit `aujobsscraper/scrapers/seek_scraper.py`:

Add `html_to_markdown` to the existing import block (lines 10-15):

```python
from aujobsscraper.utils.scraper_utils import (
    remove_html_tags,
    html_to_markdown,
    calculate_posted_date,
    normalize_locations,
    normalize_salary
)
```

Replace `_extract_description` (lines 135-138) with a shared raw-HTML helper plus two thin extractors:

```python
    def _get_description_html(self, soup) -> str:
        elem = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        return str(elem) if elem else str(soup.find("body"))

    def _extract_description(self, soup) -> str:
        return remove_html_tags(self._get_description_html(soup))

    def _extract_description_markdown(self, soup) -> str:
        return html_to_markdown(self._get_description_html(soup))
```

Update the `_build_job_posting` call in `_process_job` (lines 103-111) to pass the new field:

```python
            job_posting = self._build_job_posting(
                job_title=self._extract_title(soup),
                company=self._extract_company(soup),
                raw_locations=[self._extract_location(soup)],
                source_url=job_url,
                description=self._extract_description(soup),
                description_markdown=self._extract_description_markdown(soup),
                salary=normalize_salary(self._extract_salary(soup)),
                posted_at=self._extract_posted_date(soup),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_seek_scraper.py -v -k description_markdown`
Expected: 2 passed

- [ ] **Step 5: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add aujobsscraper/scrapers/seek_scraper.py tests/unit/test_seek_scraper.py
git commit -m "feat: populate description_markdown in SeekScraper"
```

---

### Task 5: Populate `description_markdown` in `GradConnectionScraper`

**Files:**
- Modify: `aujobsscraper/scrapers/gradconnection_scraper.py`
- Test: `tests/unit/test_gradconnection_scraper.py`

**Interfaces:**
- Consumes: `html_to_markdown` (Task 1), `_build_job_posting(..., description_markdown=...)` (Task 3).
- Produces: `GradConnectionScraper._get_description_html(soup) -> str` and `GradConnectionScraper._extract_description_markdown(soup) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_gradconnection_scraper.py` (add `from bs4 import BeautifulSoup` at the top if not already imported):

```python
def test_extract_description_markdown_converts_campaign_content():
    scraper = GradConnectionScraper()
    soup = BeautifulSoup(
        '<div class="campaign-content-container"><h2>Overview</h2>'
        '<ul><li>Graduate program</li></ul></div>',
        "lxml",
    )

    markdown = scraper._extract_description_markdown(soup)

    assert "## Overview" in markdown
    assert "- Graduate program" in markdown


def test_extract_description_markdown_falls_back_to_body():
    scraper = GradConnectionScraper()
    soup = BeautifulSoup("<body><p>Fallback <em>text</em></p></body>", "lxml")

    markdown = scraper._extract_description_markdown(soup)

    assert "Fallback" in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_gradconnection_scraper.py -v -k description_markdown`
Expected: FAIL — `AttributeError: 'GradConnectionScraper' object has no attribute '_extract_description_markdown'`

- [ ] **Step 3: Implement the helper and wire it in**

Edit `aujobsscraper/scrapers/gradconnection_scraper.py`:

Add `html_to_markdown` to the existing import block (lines 10-15):

```python
from aujobsscraper.utils.scraper_utils import (
    remove_html_tags,
    html_to_markdown,
    extract_salary_from_text,
    normalize_salary,
    normalize_locations,
)
```

Replace `_extract_description` (lines 280-287) with a shared raw-HTML helper plus two thin extractors:

```python
    def _get_description_html(self, soup) -> str:
        desc_elem = soup.select_one("div.campaign-content-container")
        if desc_elem:
            return str(desc_elem)
        desc_elem = soup.select_one("div.job-description-container")
        if desc_elem:
            return str(desc_elem)
        return str(soup.body)

    def _extract_description(self, soup) -> str:
        return remove_html_tags(self._get_description_html(soup))

    def _extract_description_markdown(self, soup) -> str:
        return html_to_markdown(self._get_description_html(soup))
```

Update the `extracted` dict in `_process_job` (lines 135-143) to include the new key:

```python
            extracted = {
                "title": title,
                "company": company,
                "locations": self._extract_locations(soup, json_data),
                "description": self._extract_description(soup),
                "description_markdown": self._extract_description_markdown(soup),
                "salary": self._extract_salary(soup, json_data),
                "posted_at": self._extract_posted_date(soup),
                "closing_date": self._extract_closing_date(soup, json_data),
            }
```

Update the `_build_job_posting` call (lines 145-154) to pass it through:

```python
            job_posting = self._build_job_posting(
                job_title=extracted["title"],
                company=extracted["company"],
                raw_locations=extracted["locations"],
                source_url=job_url,
                description=extracted["description"],
                description_markdown=extracted["description_markdown"],
                salary=extracted.get("salary"),
                posted_at=extracted.get("posted_at"),
                closing_date=extracted.get("closing_date"),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_gradconnection_scraper.py -v -k description_markdown`
Expected: 2 passed

- [ ] **Step 5: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add aujobsscraper/scrapers/gradconnection_scraper.py tests/unit/test_gradconnection_scraper.py
git commit -m "feat: populate description_markdown in GradConnectionScraper"
```

---

### Task 6: Populate `description_markdown` in `ProspleScraper`

**Files:**
- Modify: `aujobsscraper/scrapers/prosple_scraper.py`
- Test: `tests/unit/test_prosple_scraper.py`

**Interfaces:**
- Consumes: `html_to_markdown` (Task 1), `_build_job_posting(..., description_markdown=...)` (Task 3).
- Produces: `ProspleScraper._get_description_html(soup, json_data) -> str` and `ProspleScraper._extract_description_markdown(soup, json_data) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_prosple_scraper.py` (add `from bs4 import BeautifulSoup` at the top if not already imported):

```python
def test_extract_description_markdown_uses_json_ld_description():
    scraper = ProspleScraper()
    json_data = {"description": "<h2>About</h2><ul><li>Grad rotation</li></ul>"}
    soup = BeautifulSoup("<body></body>", "lxml")

    markdown = scraper._extract_description_markdown(soup, json_data)

    assert "## About" in markdown
    assert "- Grad rotation" in markdown


def test_extract_description_markdown_falls_back_to_body_when_no_json():
    scraper = ProspleScraper()
    soup = BeautifulSoup("<body><p>Fallback <strong>role</strong></p></body>", "lxml")

    markdown = scraper._extract_description_markdown(soup, None)

    assert "Fallback" in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_prosple_scraper.py -v -k description_markdown`
Expected: FAIL — `AttributeError: 'ProspleScraper' object has no attribute '_extract_description_markdown'`

- [ ] **Step 3: Implement the helper and wire it in**

Edit `aujobsscraper/scrapers/prosple_scraper.py`:

Add `html_to_markdown` to the existing import block (lines 9-14):

```python
from aujobsscraper.utils.scraper_utils import (
    remove_html_tags,
    html_to_markdown,
    extract_salary_from_text,
    normalize_salary,
    normalize_locations,
)
```

Replace `_extract_description` (lines 273-278) with a shared raw-HTML helper plus two thin extractors — note `_extract_salary` (line 264) already calls `_extract_description(soup, json_data)`, so its signature must stay unchanged:

```python
    def _get_description_html(self, soup, json_data: Optional[Dict]) -> str:
        if json_data:
            description_html = json_data.get('description', "")
            if description_html:
                return description_html
        return str(soup.body) if soup.body else ""

    def _extract_description(self, soup, json_data: Optional[Dict]) -> str:
        return remove_html_tags(self._get_description_html(soup, json_data))

    def _extract_description_markdown(self, soup, json_data: Optional[Dict]) -> str:
        return html_to_markdown(self._get_description_html(soup, json_data))
```

Update the `extracted` dict in `_process_job` (lines 146-154) to include the new key:

```python
            extracted = {
                "title": title,
                "company": company,
                "locations": self._extract_locations(soup, json_data),
                "description": self._extract_description(soup, json_data),
                "description_markdown": self._extract_description_markdown(soup, json_data),
                "salary": self._extract_salary(soup, json_data),
                "posted_at": self._extract_posted_date(json_data),
                "closing_date": self._extract_closing_date(json_data),
            }
```

Update the `_build_job_posting` call (lines 156-165) to pass it through:

```python
            job_posting = self._build_job_posting(
                job_title=extracted["title"],
                company=extracted["company"],
                raw_locations=extracted["locations"],
                source_url=job_url,
                description=extracted["description"],
                description_markdown=extracted["description_markdown"],
                salary=extracted.get("salary"),
                posted_at=extracted.get("posted_at"),
                closing_date=extracted.get("closing_date"),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_prosple_scraper.py -v -k description_markdown`
Expected: 2 passed

- [ ] **Step 5: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add aujobsscraper/scrapers/prosple_scraper.py tests/unit/test_prosple_scraper.py
git commit -m "feat: populate description_markdown in ProspleScraper"
```

---

### Task 7: Populate `description_markdown` in `IndeedScraper`

**Files:**
- Modify: `aujobsscraper/scrapers/indeed_scraper.py`
- Test: `tests/unit/test_indeed_scraper.py`

**Interfaces:**
- Consumes: `JobPosting.description_markdown` (Task 2). No new HTML conversion — `jobspy` already returns markdown-formatted `description` text, so this task copies it directly.
- Produces: no new methods; `format_jobpost` now also sets `description_markdown`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_indeed_scraper.py`:

```python
def test_format_jobpost_copies_description_into_description_markdown():
    scraper = IndeedScraper()
    job_post = {
        "title": "Software Engineer",
        "company": "Acme",
        "location": {"city": "Sydney", "state": "NSW", "country": "Australia"},
        "job_url": "https://indeed.com/job/1",
        "description": "## Responsibilities\n- Build backend services in Python.",
    }

    posting = scraper.format_jobpost(job_post)

    assert posting is not None
    assert posting.description_markdown == posting.description
    assert posting.description_markdown == "## Responsibilities\n- Build backend services in Python."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_indeed_scraper.py -v -k description_markdown`
Expected: FAIL — `AssertionError: None != '## Responsibilities\n- Build backend services in Python.'`

- [ ] **Step 3: Wire it in**

Edit `aujobsscraper/scrapers/indeed_scraper.py` — in `format_jobpost` (lines 122-131), add `description_markdown=description` to the `JobPosting(...)` construction:

```python
        return JobPosting(
            job_title=title,
            company=company,
            description=description,
            description_markdown=description,
            locations=locations,
            source_urls=[source_url] if source_url else [],
            platforms=[self.platform],
            salary=salary,
            posted_at=posted_at,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_indeed_scraper.py -v -k description_markdown`
Expected: 1 passed

- [ ] **Step 5: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add aujobsscraper/scrapers/indeed_scraper.py tests/unit/test_indeed_scraper.py
git commit -m "feat: populate description_markdown in IndeedScraper"
```

---

## Final Verification

- [ ] Run the entire unit suite one more time end-to-end: `pytest tests/unit/ -v` — expect all green.
- [ ] Run `python scripts/run_all_scrapers.py --scrapers seek --output /tmp/seek_preview.json` (or any single scraper) and manually inspect the output JSON to confirm `description_markdown` is present and non-empty alongside `description`.

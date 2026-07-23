# Design: `description_markdown` field on JobPosting

Date: 2026-07-23

## Problem

`JobPosting.description` is populated by each scraper via `remove_html_tags()`
(Seek, GradConnection, Prosple) or directly from `jobspy` (Indeed). It is a
hand-rolled, partial HTML→text converter: it handles headings, bold-as-heading,
lists, and paragraphs, but drops links, italics, tables, and nested list
structure. Consumers who want to render the description (e.g. in a web UI)
have no clean Markdown to work with.

## Goal

Add a new, purely additive field — `description_markdown` — populated via a
proper HTML→Markdown library, so consumers get high-fidelity Markdown without
changing the existing `description` field's behavior or format.

## Non-goals

- Do not change `description`'s existing content or format.
- Do not retain raw HTML as a stored field.
- Do not change scraper output ordering, dedup, or fingerprinting behavior.

## Design

### 1. Dependency

Add `markdownify` to `pyproject.toml` dependencies.

### 2. New utility

`aujobsscraper/utils/scraper_utils.py`:

```python
def html_to_markdown(html: str) -> str:
    """Convert HTML content into Markdown using markdownify.

    Returns "" for empty input. Falls back to "" if conversion fails
    on malformed HTML rather than raising.
    """
```

Configuration: ATX heading style (`#`), `-` for bullets, strip `script`/`style`
tags. Wrapped in try/except — a Markdown conversion failure must never fail
the whole scrape.

Exported from `aujobsscraper/utils/__init__.py` alongside `remove_html_tags`.

### 3. Model change

`aujobsscraper/models/job.py`:

```python
description_markdown: Optional[str] = Field(
    None, description="Job description converted from HTML to Markdown for display"
)
```

Defaults to `None`. Not included in `JobPosting.validate()` requirements —
purely a nice-to-have display field, never blocks collection.

### 4. `base_scraper._build_job_posting`

Accept `description_markdown` as an optional kwarg (via `**optional_fields`,
consistent with `salary`/`posted_at`/`closing_date`) and pass through to
`JobPosting(...)`.

### 5. Per-scraper changes

**Seek** (`seek_scraper.py`): `_extract_description` currently does
`raw = str(elem) if elem else str(soup.find("body")); return remove_html_tags(raw)`.
Change to return both: keep existing plain-text return for `description`, and
separately compute `html_to_markdown(raw)` for `description_markdown`. Pass
both through `_build_job_posting`.

**GradConnection** (`gradconnection_scraper.py`): same pattern —
`_extract_description` selects `div.campaign-content-container` /
`div.job-description-container` / `soup.body` as raw HTML before calling
`remove_html_tags`. Compute `html_to_markdown` on the same raw HTML string.

**Prosple** (`prosple_scraper.py`): `_extract_description` already extracts
`description_html` from JSON or `soup.body`. Same pattern: convert that same
raw HTML with `html_to_markdown` in addition to `remove_html_tags`.

For all three, the simplest implementation is: change `_extract_description`
to return a small tuple/dict `{"description": ..., "description_markdown": ...}`
(or add a sibling method) so the raw HTML is only extracted once and reused
for both conversions.

**Indeed** (`indeed_scraper.py`): uses `jobspy.scrape_jobs`, which does not
expose the raw HTML to us — by the time we see `job_post["description"]` it's
already been converted by jobspy (which defaults to Markdown-formatted
descriptions). Rather than re-deriving Markdown from already-processed text,
set `description_markdown = description` directly in `format_jobpost`.

### 6. Testing

- Unit tests for `html_to_markdown()`: headings, bold/italic, ordered/unordered
  lists (including nested), links, tables, empty input, malformed HTML
  (verify no exception, returns `""`).
- One test per scraper (Seek, GradConnection, Prosple) asserting
  `description_markdown` is populated and differs from `description` for a
  representative HTML fixture.
- One test for Indeed asserting `description_markdown == description`.

## Error handling

`html_to_markdown()` catches conversion exceptions internally and returns
`""` (empty string ⇒ treated as falsy/absent for display purposes), consistent
with `JobPosting.description_markdown` being `Optional[str]`. A conversion
failure must never raise out of a scraper's job-processing path.

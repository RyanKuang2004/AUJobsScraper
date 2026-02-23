# Jobly - Australian Job Market Scraper

Jobly is a Python package of Playwright-based scrapers for Australian job boards. It collects job postings from multiple sources and normalizes common fields such as title, company, location, salary, and posting dates so downstream processing is consistent.

**Overview**
- Purpose: Automated collection of Australian job listings from major boards.
- Scope: Scrapes public job listing pages and returns structured `JobPosting` objects.
- Sources: Seek, GradConnection, Prosple.

**Requirements**
- Python 3.12+
- Playwright browsers installed (Chromium is used by default)

**Installation**
1. Create and activate a virtual environment (recommended).
2. Install the package and dependencies:
```bash
pip install -e .
```
3. Install Playwright browsers:
```bash
playwright install
```

**Usage**
Run a scraper module directly:
```bash
python -m aujobsscraper.scrapers.seek_scraper
python -m aujobsscraper.scrapers.gradconnection_scraper
python -m aujobsscraper.scrapers.prosple_scraper
python -m aujobsscraper.scrapers.indeedscraper
```

**Configuration**
Configuration is managed via environment variables prefixed with `SCRAPER_`. Below are common examples:
```bash
SCRAPER_SEARCH_KEYWORDS="['software engineer','data scientist']"
SCRAPER_MAX_PAGES=5
SCRAPER_DAYS_FROM_POSTED=3
SCRAPER_INITIAL_RUN=true
```

**Notes**
- The scrapers rely on the public HTML structure of each job board, which can change without notice.
- Network conditions and site rate-limiting may affect scrape reliability.



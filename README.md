# Jobly - Australian Job Market Scraper

Jobly is a Python package of Playwright-based scrapers for Australian job boards. It collects job postings from multiple sources and normalizes common fields such as title, company, location, salary, and posting dates so downstream processing is consistent.

**Overview**
- Purpose: Automated collection of Australian job listings from major boards.
- Scope: Scrapes public job listing pages and returns structured `JobPosting` objects.
- Sources: Seek, GradConnection, Prosple, Indeed.

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

Run all scrapers:
```bash
python scripts/run_all_scrapers.py
python scripts/run_all_scrapers.py -o results/jobs.json
```

Run individual scrapers:
```bash
python -m aujobsscraper.scrapers.seek_scraper
python -m aujobsscraper.scrapers.gradconnection_scraper
python -m aujobsscraper.scrapers.prosple_scraper
python -m aujobsscraper.scrapers.indeed_scraper
```

**Configuration**
Configuration is managed via environment variables prefixed with `SCRAPER_`. Below are common examples:
```bash
SCRAPER_SEARCH_KEYWORDS="['software engineer','data scientist']"
SCRAPER_MAX_PAGES=5
SCRAPER_DAYS_FROM_POSTED=3
SCRAPER_INITIAL_RUN=true
```

**Salary Extraction**

The Indeed scraper uses a two-tier salary extraction strategy:
1. **JobSpy fields** (`min_amount`/`max_amount`): Used when present; normalized to annual via interval multiplier.
2. **Description fallback** (`SalaryParser`): When JobSpy fields are absent, salary is parsed from the job description text using regex patterns for ranges (`$76,000 - $85,000`) and single values (`$80,000 per year`). Escaped HTML characters (`\$`, `\-`) are cleaned before parsing. Salaries outside $10–$1,000,000/year are rejected.

**Notes**
- The scrapers rely on the public HTML structure of each job board, which can change without notice.
- Network conditions and site rate-limiting may affect scrape reliability.



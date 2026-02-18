# Jobly - Australian Job Market Scraper

Jobly is a Python package of Playwright-based scrapers for Australian job boards. It collects job postings from Seek, GradConnection, and Prosple, normalizing fields like title, company, location, salary, and dates.

## Run
1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies with `pip install -e .`.
3. Install browsers with `playwright install`.
4. Run a scraper module directly:
```bash
python -m aujobsscraper.scrapers.seek_scraper
python -m aujobsscraper.scrapers.gradconnection_scraper
python -m aujobsscraper.scrapers.prosple_scraper
```

Optional configuration via environment variables (prefix `SCRAPER_`):
```bash
SCRAPER_SEARCH_KEYWORDS="['software engineer','data scientist']"
SCRAPER_MAX_PAGES=5
SCRAPER_DAYS_FROM_POSTED=3
SCRAPER_INITIAL_RUN=true
```



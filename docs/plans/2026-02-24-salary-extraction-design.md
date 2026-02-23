# Salary Extraction from Job Description Design

**Date:** 2026-02-24
**Author:** Claude
**Status:** Approved

## Overview

Enhance the Indeed scraper to extract salary information from job description text as a fallback when `min_amount` and `max_amount` from JobSpy are both None. Use a hybrid approach combining regex patterns for common cases with lightweight rule-based parsing for edge cases.

## Problem Statement

The current Indeed scraper relies on `min_amount` and `max_amount` fields from JobSpy's output. However, these fields are frequently `None`, resulting in missing salary data. Salary information is often present in the job description text itself (typically in the first few sentences), such as:

```
$76,000 - $85,000 per year + Superannuation
$121,755 - $132,713 + 15.4% super
```

## Solution Design

### Architecture

**Components:**

1. **SalaryParser utility module** (`aujobsscraper/utils/salary_parser.py`)
   - Reusable across all scrapers
   - Primary method: `extract_salary(description: str) -> Optional[Dict[str, float]]`
   - Helper methods for different pattern types

2. **Enhanced IndeedScraper** (`aujobsscraper/scrapers/indeed_scraper.py`)
   - Modify `_extract_salary()` to fallback to SalaryParser when job_post fields are None
   - Pass job description text to parser

### Data Flow

```
format_jobpost()
  → _extract_salary(job_post)
    → Try min_amount/max_amount from job_post
      → If both None: call SalaryParser.extract_salary(description)
        → Regex matching for patterns
        → Lightweight rule-based parsing for edge cases
        → Normalize to annual_min/annual_max
        → Return dict or None
      → If found: normalize to annual and return
```

## Salary Patterns to Support

### Range Patterns
- `$76,000 - $85,000 per year`
- `$50-$60 hourly`
- `80k-100k + super`

### Single Values
- `$100,000 per year`
- `$50 hourly`

### Time Intervals
- hourly, daily, weekly, monthly, yearly, annual, annum
- Shorthand: per hour, /hr, /yr, per year

### Currency and Superannuation
- `$` symbol for amounts
- `+ super`, `+ Superannuation` (ignore, don't affect calculation)
- Handle escaped characters from scraped HTML (e.g., `\$76,000`, `\-\-`)

## Implementation Details

### Regex Patterns

**Currency ranges:**
```python
r'\$?\s*([\d,]+)\s*[-–to]\s*\$?([\d,]+)'
```

**Single amounts:**
```python
r'\$?\s*([\d,]+)(?:k|K)?\s*(?:per|/)?\s*(hour|hr|week|month|year|annual|annum)'
```

**Pattern features:**
- Handle "k/K" suffix (e.g., 80k → 80000)
- Support en-dash and em-dash in ranges
- Support "to", "-", "–" as range separators
- Optional currency symbols

### LightWeight Parsing

- Extract first 3-5 sentences/lines from description
- Look for dollar symbols and numeric patterns
- Handle escaped backslashes from scraped HTML
- Use first valid match found

### Normalization

- Convert all intervals to annual using existing `_interval_multiplier()` logic
  - Hourly: × 2080
  - Daily: × 260
  - Weekly: × 52
  - Monthly: × 12
  - Yearly: × 1

- Handle ranges with min/max ordering
- Return standard format: `{"annual_min": float, "annual_max": float}`

### Error Handling

**Robustness measures:**
- Return `None` if no valid salary pattern found
- Handle malformed/malicious input gracefully
- Log warnings when parsing fails for debugging
- Validate extracted amounts are reasonable (e.g., >0, <$1M annual)

**Edge cases:**
- Description is empty or None
- Multiple salary mentions (use first valid one)
- Ambiguous intervals (default to yearly if unclear)
- Non-Australian currency symbols (ignore)

## Testing Strategy

### Unit Tests for SalaryParser

**Test cases:**
- Range patterns: `$76,000 - $85,000 per year`, `$50-$60 hourly`
- Single values: `$100,000`, `$50 per hour`
- Edge cases: empty strings, malformed input, no salary
- Normalization: hourly/daily/weekly/monthly to annual conversion
- Escaped characters: `\$76,000`, `\-\-`

### Integration Tests

**Test scenarios:**
- Full IndeedScraper flow with sample job data
- Fallback behavior when min_amount/max_amount are None
- Original behavior when min_amount/max_amount are present
- Jobs with and without salary information

### Test Data

- Use sample descriptions from current `results/jobs.json`
- Include jobs with salary in description
- Include jobs without salary information
- Test various salary formats and intervals

## File Structure

```
aujobsscraper/
├── utils/
│   ├── __init__.py
│   ├── scraper_utils.py
│   └── salary_parser.py  (NEW)
├── scrapers/
│   └── indeed_scraper.py  (MODIFIED)
└── tests/
    ├── unit/
    │   └── test_salary_parser.py  (NEW)
    └── integration/
        └── test_indeed_scraper.py  (MODIFIED)
```

## Success Criteria

1. Salary extraction from descriptions works for common patterns
2. Fallback only triggers when min_amount/max_amount are both None
3. All values normalized to annual_min/annual_max format
4. Unit tests cover core patterns and edge cases
5. Integration tests verify end-to-end functionality
6. No breaking changes to existing behavior

## Next Steps

Invoke `writing-plans` skill to create detailed implementation plan.

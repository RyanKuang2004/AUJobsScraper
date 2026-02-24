# Salary Extraction

## Overview

`SalaryParser` (`aujobsscraper/utils/salary_parser.py`) extracts salary information from free-text job descriptions and normalizes it to an annual figure.

It is used by `IndeedScraper` as a fallback when JobSpy's structured `min_amount`/`max_amount` fields are `None`.

## Extraction Strategy

### IndeedScraper two-tier approach

```
job_post.min_amount / max_amount present?
  Yes → use JobSpy values × interval multiplier
  No  → call SalaryParser.extract_salary(description)
```

### SalaryParser logic

1. Clean escaped HTML entities (`\$` → `$`, `\-` → `-`, `\.` → `.`)
2. Restrict search to the first 5 sentences or 1000 characters
3. Try **range pattern** first: `$76,000 - $85,000`, `76000–85000`, `$80k to $90k`
4. Fall back to **single value pattern**: `$80,000 per year`, `$45/hr`
5. Detect interval from surrounding context (hourly/daily/weekly/monthly/yearly)
6. Annualize using standard multipliers
7. Reject values outside $10–$1,000,000 per year

## Interval Multipliers

| Interval | Multiplier |
|----------|-----------|
| hourly   | × 2080    |
| daily    | × 260     |
| weekly   | × 52      |
| monthly  | × 12      |
| yearly   | × 1       |

## Return Value

```python
{"annual_min": float, "annual_max": float}
# or None if no salary found / outside reasonable range
```

For a single-value match, `annual_min == annual_max`.

## Examples

| Input | Output |
|-------|--------|
| `$76,000 \- $85,000 per year` | `{"annual_min": 76000.0, "annual_max": 85000.0}` |
| `$80,000 - $90,000` | `{"annual_min": 80000.0, "annual_max": 90000.0}` |
| `$45 per hour` | `{"annual_min": 93600.0, "annual_max": 93600.0}` |
| `$6,000 per month` | `{"annual_min": 72000.0, "annual_max": 72000.0}` |
| `-$50,000 per year` | `None` (negative prefix rejected) |
| `Competitive salary` | `None` (no numeric match) |

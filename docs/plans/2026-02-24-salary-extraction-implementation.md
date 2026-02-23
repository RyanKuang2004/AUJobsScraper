# Salary Extraction from Job Description Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract salary information from job description text as a fallback when min_amount/max_amount from JobSpy are None.

**Architecture:** Create a reusable SalaryParser utility module with regex + lightweight rule-based parsing. Enhance IndeedScraper to use this parser as fallback. All salaries normalized to annual_min/annual_max format.

**Tech Stack:** Python 3.12+, regex, pytest, pydantic, existing JobSpy integration

---

### Task 1: Create SalaryParser module stub

**Files:**
- Create: `aujobsscraper/utils/salary_parser.py`

**Step 1: Write the failing test**

Create: `tests/unit/test_salary_parser.py`

```python
import pytest
from aujobsscraper.utils.salary_parser import SalaryParser


def test_extract_salary_returns_dict_for_valid_input():
    description = "$76,000 - $85,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert "annual_min" in result
    assert "annual_max" in result


def test_extract_salary_returns_none_for_empty_string():
    result = SalaryParser.extract_salary("")
    assert result is None


def test_extract_salary_returns_none_for_no_salary():
    result = SalaryParser.extract_salary("No salary information here")
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_salary_parser.py -v`
Expected: FAIL with "module 'aujobsscraper.utils.salary_parser' not found"

**Step 3: Write minimal implementation**

Create: `aujobsscraper/utils/salary_parser.py`

```python
from typing import Optional, Dict


class SalaryParser:
    """Extract salary information from job description text."""

    @staticmethod
    def extract_salary(description: str) -> Optional[Dict[str, float]]:
        """Extract salary from description and normalize to annual.

        Args:
            description: Job description text

        Returns:
            Dict with 'annual_min' and 'annual_max' floats, or None if not found
        """
        if not description or not isinstance(description, str):
            return None
        return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_salary_parser.py::test_extract_salary_returns_none_for_empty_string -v`
Expected: PASS

Run: `pytest tests/unit/test_salary_parser.py::test_extract_salary_returns_none_for_no_salary -v`
Expected: PASS

Run: `pytest tests/unit/test_salary_parser.py::test_extract_salary_returns_dict_for_valid_input -v`
Expected: FAIL (returns None instead of dict)

**Step 5: Commit**

```bash
git add aujobsscraper/utils/salary_parser.py tests/unit/test_salary_parser.py
git commit -m "feat: add SalaryParser stub with basic tests"
```

---

### Task 2: Implement range pattern regex

**Files:**
- Modify: `aujobsscraper/utils/salary_parser.py`

**Step 1: Write the failing test**

Add to: `tests/unit/test_salary_parser.py`

```python
def test_extract_salary_range_with_dollars():
    description = "$76,000 - $85,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 76000.0
    assert result["annual_max"] == 85000.0


def test_extract_salary_range_without_dollars():
    description = "76,000 - 85,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 76000.0
    assert result["annual_max"] == 85000.0


def test_extract_salary_range_with_en_dash():
    description = "$76,000 – $85,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 76000.0
    assert result["annual_max"] == 85000.0


def test_extract_salary_range_with_to():
    description = "$76,000 to $85,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 76000.0
    assert result["annual_max"] == 85000.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_salary_parser.py -k "range" -v`
Expected: FAIL - all tests return None

**Step 3: Write minimal implementation**

Modify: `aujobsscraper/utils/salary_parser.py`

```python
from typing import Optional, Dict
import re


class SalaryParser:
    """Extract salary information from job description text."""

    # Currency range pattern: $X - $Y or X - Y
    RANGE_PATTERN = re.compile(
        r'\$?\s*([\d,]+)\s*[-–to]\s*\$?([\d,]+)',
        re.IGNORECASE
    )

    @staticmethod
    def extract_salary(description: str) -> Optional[Dict[str, float]]:
        """Extract salary from description and normalize to annual.

        Args:
            description: Job description text

        Returns:
            Dict with 'annual_min' and 'annual_max' floats, or None if not found
        """
        if not description or not isinstance(description, str):
            return None

        # Try range pattern first
        range_match = SalaryParser._extract_range(description)
        if range_match:
            min_val, max_val, interval = range_match
            annual_min = SalaryParser._to_annual(min_val, interval)
            annual_max = SalaryParser._to_annual(max_val, interval)
            return {
                "annual_min": min(annual_min, annual_max),
                "annual_max": max(annual_min, annual_max),
            }

        return None

    @staticmethod
    def _extract_range(text: str) -> Optional[tuple[float, float, str]]:
        """Extract salary range and interval from text.

        Returns:
            Tuple of (min, max, interval) or None
        """
        match = SalaryParser.RANGE_PATTERN.search(text)
        if not match:
            return None

        min_str = match.group(1).replace(',', '')
        max_str = match.group(2).replace(',', '')

        try:
            min_val = float(min_str)
            max_val = float(max_str)
        except ValueError:
            return None

        # Look for interval in surrounding text (50 chars before/after)
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].lower()

        interval = SalaryParser._detect_interval(context)
        return (min_val, max_val, interval)

    @staticmethod
    def _detect_interval(text: str) -> str:
        """Detect salary interval from text.

        Returns:
            'hourly', 'daily', 'weekly', 'monthly', or 'yearly'
        """
        text = text.lower()
        if 'hour' in text or '/hr' in text or 'hrly' in text:
            return 'hourly'
        if 'day' in text:
            return 'daily'
        if 'week' in text or 'wk' in text:
            return 'weekly'
        if 'month' in text or 'mo' in text or 'mth' in text:
            return 'monthly'
        if 'year' in text or '/yr' in text or 'annual' in text or 'annum' in text:
            return 'yearly'
        return 'yearly'  # Default

    @staticmethod
    def _to_annual(amount: float, interval: str) -> float:
        """Convert amount to annual salary.

        Args:
            amount: Salary amount
            interval: 'hourly', 'daily', 'weekly', 'monthly', or 'yearly'

        Returns:
            Annualized amount
        """
        multipliers = {
            'hourly': 2080,
            'daily': 260,
            'weekly': 52,
            'monthly': 12,
            'yearly': 1,
        }
        return amount * multipliers.get(interval, 1)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_salary_parser.py -k "range" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add aujobsscraper/utils/salary_parser.py tests/unit/test_salary_parser.py
git commit -m "feat: implement salary range pattern extraction"
```

---

### Task 3: Handle escaped characters from HTML

**Files:**
- Modify: `aujobsscraper/utils/salary_parser.py`

**Step 1: Write the failing test**

Add to: `tests/unit/test_salary_parser.py`

```python
def test_extract_salary_with_escaped_dollar():
    description = "* Executive Level 1 (SITOC)\n* \\$121,755 \\- \\$132,713 \\+ 15\\.4% super"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 121755.0
    assert result["annual_max"] == 132713.0


def test_extract_salary_with_escaped_hyphen():
    description = "\\$76,000 \\- \\$85,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 76000.0
    assert result["annual_max"] == 85000.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_salary_parser.py -k "escaped" -v`
Expected: FAIL - escaped characters not matched

**Step 3: Write minimal implementation**

Modify: `aujobsscraper/utils/salary_parser.py`

```python
# Add after imports, inside class SalaryParser:

    @staticmethod
    def extract_salary(description: str) -> Optional[Dict[str, float]]:
        """Extract salary from description and normalize to annual.

        Args:
            description: Job description text

        Returns:
            Dict with 'annual_min' and 'annual_max' floats, or None if not found
        """
        if not description or not isinstance(description, str):
            return None

        # Clean escaped HTML characters
        cleaned = description.replace('\\$', '$').replace('\\-', '-').replace('\\.', '.')

        # Try range pattern first
        range_match = SalaryParser._extract_range(cleaned)
        if range_match:
            min_val, max_val, interval = range_match
            annual_min = SalaryParser._to_annual(min_val, interval)
            annual_max = SalaryParser._to_annual(max_val, interval)
            return {
                "annual_min": min(annual_min, annual_max),
                "annual_max": max(annual_min, annual_max),
            }

        return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_salary_parser.py -k "escaped" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add aujobsscraper/utils/salary_parser.py tests/unit/test_salary_parser.py
git commit -m "feat: handle escaped HTML characters in salary extraction"
```

---

### Task 4: Implement single value pattern

**Files:**
- Modify: `aujobsscraper/utils/salary_parser.py`

**Step 1: Write the failing test**

Add to: `tests/unit/test_salary_parser.py`

```python
def test_extract_salary_single_value_with_dollar():
    description = "$100,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 100000.0
    assert result["annual_max"] == 100000.0


def test_extract_salary_single_value_hourly():
    description = "$50 per hour"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 104000.0  # 50 * 2080
    assert result["annual_max"] == 104000.0


def test_extract_salary_single_value_monthly():
    description = "$8,000 per month"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 96000.0  # 8000 * 12
    assert result["annual_max"] == 96000.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_salary_parser.py -k "single" -v`
Expected: FAIL - single values not extracted

**Step 3: Write minimal implementation**

Modify: `aujobsscraper/utils/salary_parser.py`

```python
# Add pattern after RANGE_PATTERN:
    SINGLE_VALUE_PATTERN = re.compile(
        r'\$?\s*([\d,]+)(?:k|K)?\s*(?:per|/)?\s*(hour|hr|week|month|year|annual|annum)?',
        re.IGNORECASE
    )

# Add inside extract_salary() method, after range check but before return None:

        # Try single value pattern
        single_match = SalaryParser._extract_single_value(cleaned)
        if single_match:
            val, interval = single_match
            annual = SalaryParser._to_annual(val, interval)
            return {
                "annual_min": annual,
                "annual_max": annual,
            }

# Add new method after _extract_range:

    @staticmethod
    def _extract_single_value(text: str) -> Optional[tuple[float, str]]:
        """Extract single salary value and interval from text.

        Returns:
            Tuple of (value, interval) or None
        """
        match = SalaryParser.SINGLE_VALUE_PATTERN.search(text)
        if not match:
            return None

        val_str = match.group(1).replace(',', '')

        try:
            val = float(val_str)
        except ValueError:
            return None

        # Check for k/K suffix (e.g., 80k -> 80000)
        if 'k' in match.group(0).lower():
            val *= 1000

        # Look for interval in surrounding text
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].lower()

        interval = SalaryParser._detect_interval(context)
        return (val, interval)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_salary_parser.py -k "single" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add aujobsscraper/utils/salary_parser.py tests/unit/test_salary_parser.py
git commit -m "feat: implement single value salary extraction"
```

---

### Task 5: Only search first few sentences

**Files:**
- Modify: `aujobsscraper/utils/salary_parser.py`

**Step 1: Write the failing test**

Add to: `tests/unit/test_salary_parser.py`

```python
def test_extract_salary_only_from_first_sentences():
    long_desc = (
        "$80,000 per year\n\n"
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "This is a very long job description with many sentences. "
        "There is another mention of $100,000 here that should not be picked up "
        "because it's not in the first few sentences."
    )
    result = SalaryParser.extract_salary(long_desc)
    assert result is not None
    assert result["annual_min"] == 80000.0
    assert result["annual_max"] == 80000.0


def test_extract_salary_from_line_list():
    # Mimic jobspy description format with bullet points
    description = (
        "* Executive Level 1 (SITOC)\n"
        "* $121,755 \\- $132,713 \\+ 15.4% super\n"
        "* Adelaide, Brisbane, Canberra\n\n"
        "This is the rest of the description..."
    )
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 121755.0
    assert result["annual_max"] == 132713.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_salary_parser.py -k "first_sentences" -v`
Expected: FAIL - searches entire description, picks wrong value

**Step 3: Write minimal implementation**

Modify: `aujobsscraper/utils/salary_parser.py`

```python
# Add new constant after SINGLE_VALUE_PATTERN:
    MAX_SENTENCES_TO_SEARCH = 5
    MAX_CHARS_TO_SEARCH = 1000

# Modify extract_salary() method to limit search scope:

    @staticmethod
    def extract_salary(description: str) -> Optional[Dict[str, float]]:
        """Extract salary from description and normalize to annual.

        Args:
            description: Job description text

        Returns:
            Dict with 'annual_min' and 'annual_max' floats, or None if not found
        """
        if not description or not isinstance(description, str):
            return None

        # Clean escaped HTML characters
        cleaned = description.replace('\\$', '$').replace('\\-', '-').replace('\\.', '.')

        # Limit search to first few sentences
        search_text = SalaryParser._get_first_sentences(cleaned)

        # Try range pattern first
        range_match = SalaryParser._extract_range(search_text)
        if range_match:
            min_val, max_val, interval = range_match
            annual_min = SalaryParser._to_annual(min_val, interval)
            annual_max = SalaryParser._to_annual(max_val, interval)
            return {
                "annual_min": min(annual_min, annual_max),
                "annual_max": max(annual_min, annual_max),
            }

        # Try single value pattern
        single_match = SalaryParser._extract_single_value(search_text)
        if single_match:
            val, interval = single_match
            annual = SalaryParser._to_annual(val, interval)
            return {
                "annual_min": annual,
                "annual_max": annual,
            }

        return None

# Add new method after _detect_interval:

    @staticmethod
    def _get_first_sentences(text: str) -> str:
        """Extract first few sentences from text for salary search.

        Returns:
            First N sentences or first N characters, whichever is shorter
        """
        # Limit by character count first
        if len(text) <= SalaryParser.MAX_CHARS_TO_SEARCH:
            return text

        # Try to split by sentence boundaries
        sentences = []
        current = text[:SalaryParser.MAX_CHARS_TO_SEARCH * 2]  # Look a bit further

        # Split by common sentence delimiters
        for delimiter in ['.\n', '!\n', '?\n', '.\n\n', '. ', '! ', '? ']:
            if delimiter in current:
                split = current.split(delimiter, SalaryParser.MAX_SENTENCES_TO_SEARCH)
                sentences = split
                break

        if not sentences:
            # Fallback to character limit
            return text[:SalaryParser.MAX_CHARS_TO_SEARCH]

        result = delimiter.join(sentences[:SalaryParser.MAX_SENTENCES_TO_SEARCH])
        return result[:SalaryParser.MAX_CHARS_TO_SEARCH]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_salary_parser.py -k "first_sentences or line_list" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add aujobsscraper/utils/salary_parser.py tests/unit/test_salary_parser.py
git commit -m "feat: limit salary search to first few sentences"
```

---

### Task 6: Add validation for reasonable salary ranges

**Files:**
- Modify: `aujobsscraper/utils/salary_parser.py`

**Step 1: Write the failing test**

Add to: `tests/unit/test_salary_parser.py`

```python
def test_extract_salary_rejects_zero():
    description = "$0 per year"
    result = SalaryParser.extract_salary(description)
    assert result is None


def test_extract_salary_rejects_negative():
    description = "-$50,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is None


def test_extract_salary_rejects_excessive():
    description = "$10,000,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is None


def test_extract_salary_accepts_reasonable_range():
    description = "$50,000 - $500,000 per year"
    result = SalaryParser.extract_salary(description)
    assert result is not None
    assert result["annual_min"] == 50000.0
    assert result["annual_max"] == 500000.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_salary_parser.py -k "rejects or reasonable" -v`
Expected: FAIL - invalid values not rejected

**Step 3: Write minimal implementation**

Modify: `aujobsscraper/utils/salary_parser.py`

```python
# Add new constants at class level:
    MIN_REASONABLE_SALARY = 10.0  # $10 minimum
    MAX_REASONABLE_SALARY = 1000000.0  # $1M maximum

# Add new method after _get_first_sentences:

    @staticmethod
    def _is_reasonable_salary(annual_amount: float) -> bool:
        """Check if salary is within reasonable bounds.

        Args:
            annual_amount: Annualized salary amount

        Returns:
            True if salary is reasonable, False otherwise
        """
        return (
            SalaryParser.MIN_REASONABLE_SALARY <= annual_amount <= SalaryParser.MAX_REASONABLE_SALARY
        )

# Modify extract_salary() to validate results:

        # Try range pattern first
        range_match = SalaryParser._extract_range(search_text)
        if range_match:
            min_val, max_val, interval = range_match
            annual_min = SalaryParser._to_annual(min_val, interval)
            annual_max = SalaryParser._to_annual(max_val, interval)

            if SalaryParser._is_reasonable_salary(annual_min) and SalaryParser._is_reasonable_salary(annual_max):
                return {
                    "annual_min": min(annual_min, annual_max),
                    "annual_max": max(annual_min, annual_max),
                }

        # Try single value pattern
        single_match = SalaryParser._extract_single_value(search_text)
        if single_match:
            val, interval = single_match
            annual = SalaryParser._to_annual(val, interval)

            if SalaryParser._is_reasonable_salary(annual):
                return {
                    "annual_min": annual,
                    "annual_max": annual,
                }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_salary_parser.py -k "rejects or reasonable" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add aujobsscraper/utils/salary_parser.py tests/unit/test_salary_parser.py
git commit -m "feat: add validation for reasonable salary ranges"
```

---

### Task 7: Update IndeedScraper to use SalaryParser

**Files:**
- Modify: `aujobsscraper/scrapers/indeed_scraper.py`
- Test: `tests/integration/test_indeed_scraper.py`

**Step 1: Write the failing test**

Create/Modify: `tests/integration/test_indeed_scraper.py`

```python
import pytest
from unittest.mock import Mock, patch
from aujobsscraper.scrapers.indeed_scraper import IndeedScraper
from aujobsscraper.utils.salary_parser import SalaryParser


def test_extract_salary_uses_parser_when_jobspy_fields_none():
    """Test that salary parser is used as fallback when min_amount/max_amount are None."""
    scraper = IndeedScraper(search_term="test")

    # Mock job_post with None salary fields
    job_post = {
        "title": "Software Developer",
        "company": "Test Company",
        "description": "$80,000 - $90,000 per year",
        "location": "Sydney, NSW",
        "min_amount": None,
        "max_amount": None,
        "interval": None,
        "job_url": "https://test.com/job",
    }

    # Patch SalaryParser to verify it's called
    with patch.object(SalaryParser, 'extract_salary') as mock_extract:
        mock_extract.return_value = {"annual_min": 80000.0, "annual_max": 90000.0}

        result = scraper._extract_salary(job_post)

        # Verify parser was called with description
        mock_extract.assert_called_once_with(job_post["description"])

        # Verify correct result returned
        assert result is not None
        assert result["annual_min"] == 80000.0
        assert result["annual_max"] == 90000.0


def test_extract_salary_skips_parser_when_jobspy_fields_present():
    """Test that salary parser is NOT used when min_amount/max_amount have values."""
    scraper = IndeedScraper(search_term="test")

    # Mock job_post with salary fields present
    job_post = {
        "title": "Software Developer",
        "company": "Test Company",
        "description": "$100,000 per year",  # This should be ignored
        "location": "Sydney, NSW",
        "min_amount": 50000.0,
        "max_amount": 60000.0,
        "interval": "yearly",
        "job_url": "https://test.com/job",
    }

    # Patch SalaryParser to verify it's NOT called
    with patch.object(SalaryParser, 'extract_salary') as mock_extract:
        result = scraper._extract_salary(job_post)

        # Verify parser was NOT called
        mock_extract.assert_not_called()

        # Verify result from job_post fields is used
        assert result is not None
        assert result["annual_min"] == 50000.0
        assert result["annual_max"] == 60000.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_indeed_scraper.py -v`
Expected: FAIL - SalaryParser not imported, fallback logic not implemented

**Step 3: Write minimal implementation**

Modify: `aujobsscraper/scrapers/indeed_scraper.py`

```python
# Add import at top:
from aujobsscraper.utils.salary_parser import SalaryParser

# Modify _extract_salary method:

    def _extract_salary(self, job_post: dict[str, Any]) -> Optional[dict[str, float]]:
        min_amount = self._to_float(job_post.get("min_amount"))
        max_amount = self._to_float(job_post.get("max_amount"))

        # If jobspy has salary data, use it
        if min_amount is not None or max_amount is not None:
            low = min_amount if min_amount is not None else max_amount
            high = max_amount if max_amount is not None else min_amount
            if low is None or high is None:
                return None

            multiplier = self._interval_multiplier(job_post.get("interval"))
            annual_min = float(low) * multiplier
            annual_max = float(high) * multiplier

            return {
                "annual_min": min(annual_min, annual_max),
                "annual_max": max(annual_min, annual_max),
            }

        # Fallback: try parsing from description
        description = job_post.get("description")
        if description:
            return SalaryParser.extract_salary(description)

        return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_indeed_scraper.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add aujobsscraper/scrapers/indeed_scraper.py tests/integration/test_indeed_scraper.py
git commit -m "feat: integrate SalaryParser into IndeedScraper as fallback"
```

---

### Task 8: Add integration test with real job data

**Files:**
- Modify: `tests/integration/test_indeed_scraper.py`

**Step 1: Write the failing test**

Add to: `tests/integration/test_indeed_scraper.py`

```python
def test_format_jobpost_with_salary_in_description():
    """Test full job posting flow with salary in description."""
    scraper = IndeedScraper(search_term="test")

    job_post = {
        "title": "Software Developer",
        "company": "W.D.T. Engineers Pty Ltd",
        "description": (
            "**Boilermaker/Metal Fabricator**\n\n"
            "**W.D.T. Engineers Pty Ltd**\n\n"
            "**$76,000 \\- $85,000 per year \\+ Superannuation**\n\n"
            "**Permanent, Full-time (38 hours per week)**\n\n"
            "**Acacia Ridge QLD 4110**"
        ),
        "location": {"city": "Acacia Ridge", "state": "QLD", "country": "Australia"},
        "min_amount": None,
        "max_amount": None,
        "interval": None,
        "job_url": "https://au.indeed.com/viewjob?jk=test",
    }

    result = scraper.format_jobpost(job_post)

    assert result is not None
    assert result.job_title == "Software Developer"
    assert result.company == "W.D.T. Engineers Pty Ltd"
    assert result.salary is not None
    assert result.salary["annual_min"] == 76000.0
    assert result.salary["annual_max"] == 85000.0


def test_format_jobpost_without_salary():
    """Test job posting without any salary information."""
    scraper = IndeedScraper(search_term="test")

    job_post = {
        "title": "Volunteer Coordinator",
        "company": "Charity Org",
        "description": "This is a volunteer position with no salary.",
        "location": {"city": "Melbourne", "state": "VIC", "country": "Australia"},
        "min_amount": None,
        "max_amount": None,
        "interval": None,
        "job_url": "https://au.indeed.com/viewjob?jk=test",
    }

    result = scraper.format_jobpost(job_post)

    assert result is not None
    assert result.job_title == "Volunteer Coordinator"
    assert result.salary is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_indeed_scraper.py -k "with_salary_in_description or without_salary" -v`
Expected: FAIL - salary extraction not working for full flow

**Step 3: Write minimal implementation**

No code changes needed - existing implementation should work. Run tests to verify.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_indeed_scraper.py -k "with_salary_in_description or without_salary" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_indeed_scraper.py
git commit -m "test: add integration tests with real job data patterns"
```

---

### Task 9: Run full test suite and verify all pass

**Files:**
- None (validation task)

**Step 1: Run unit tests**

Run: `pytest tests/unit/test_salary_parser.py -v`
Expected: All tests PASS

**Step 2: Run integration tests**

Run: `pytest tests/integration/test_indeed_scraper.py -v`
Expected: All tests PASS

**Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git commit --allow-empty -m "test: verify full test suite passes"
```

---

### Task 10: Update documentation

**Files:**
- Modify: `README.md`
- Create: `docs/salary_extraction.md`

**Step 1: Update README.md**

Add to: `README.md` (after Usage section)

```markdown
**Salary Extraction**

The Indeed scraper automatically extracts salary information from job descriptions when available:

- Primary: Uses `min_amount`/`max_amount` from JobSpy API
- Fallback: Parses salary from job description text (first 5 sentences)

Supported formats:
- Ranges: `$76,000 - $85,000 per year`, `$50-$60 hourly`
- Single values: `$100,000 per year`, `$50 per hour`
- Intervals: hourly, daily, weekly, monthly, yearly
- Handles escaped HTML characters: `\$76,000`, `\-\-`

All salaries are normalized to annual format with `annual_min` and `annual_max` fields.
```

**Step 2: Create detailed documentation**

Create: `docs/salary_extraction.md`

```markdown
# Salary Extraction Documentation

## Overview

The salary extraction system combines data from JobSpy API with intelligent parsing of job descriptions to maximize salary coverage.

## Architecture

### SalaryParser Utility

Located in `aujobsscraper/utils/salary_parser.py`, this module provides:

- `extract_salary(description: str) -> Optional[Dict[str, float]]`
- Regex-based pattern matching
- Support for ranges and single values
- Interval normalization (hourly/daily/weekly/monthly → annual)
- HTML character escaping handling

### IndeedScraper Integration

The scraper uses a two-tier approach:

1. **Primary**: JobSpy's `min_amount`/`max_amount` fields
2. **Fallback**: SalaryParser when JobSpy fields are None

## Supported Formats

### Salary Ranges
```
$76,000 - $85,000 per year
$50-$60 hourly
80k-100k + super
```

### Single Values
```
$100,000 per year
$50 per hour
$8,000 monthly
```

### Intervals
- Hourly: ×2080 (based on 40hr week, 52 weeks)
- Daily: ×260
- Weekly: ×52
- Monthly: ×12
- Yearly: ×1

## Validation

Extracted salaries must be:
- Greater than $10 annually
- Less than $1,000,000 annually

## Usage Example

```python
from aujobsscraper.scrapers.indeed_scraper import IndeedScraper

scraper = IndeedScraper(search_term="software engineer")
jobs = await scraper.scrape()

# Job salary will be extracted from JobSpy or description
for job in jobs:
    if job.salary:
        print(f"{job.job_title}: ${job.salary['annual_min']:,.f} - ${job.salary['annual_max']:,.f}")
```
```

**Step 3: Commit documentation**

```bash
git add README.md docs/salary_extraction.md
git commit -m "docs: add salary extraction documentation"
```

---

### Task 11: Manual verification with real data

**Files:**
- None (verification task)

**Step 1: Run scraper on test data**

Run: `python -m aujobsscraper.scrapers.indeed_scraper --search-term "software engineer" --results-wanted 10`

**Step 2: Check salary extraction**

Run: `python -c "import json; data = json.load(open('results/jobs.json')); jobs = data.get('scraper_results', [])[0].get('jobs', []); print(f'Total jobs: {len(jobs)}'); print(f'Jobs with salary: {sum(1 for j in jobs if j.get(\"salary\"))}'); [print(f\"\\n{j['job_title']}: {j.get('salary', 'None')}\") for j in jobs[:5]]"`

**Step 3: Verify quality**

Check that:
- Jobs with salary in description have salary extracted
- Jobs without salary have None
- Salaries are reasonable (not zero, not excessive)
- Annual values are correctly calculated

**Step 4: Commit**

```bash
git commit --allow-empty -m "qa: manual verification with real job data"
```

---

## Summary

This implementation plan:

1. ✅ Creates a reusable SalaryParser utility
2. ✅ Supports range and single value patterns
3. ✅ Handles multiple time intervals with normalization
4. ✅ Validates reasonable salary ranges
5. ✅ Integrates as fallback in IndeedScraper
6. ✅ Includes comprehensive unit and integration tests
7. ✅ Documents the feature

**Estimated completion time:** 1-2 hours following TDD workflow

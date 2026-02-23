from typing import Optional, Dict
import re


class SalaryParser:
    """Extract salary information from job description text."""

    # Currency range pattern: $X - $Y or X - Y
    RANGE_PATTERN = re.compile(
        r'\$?\s*([\d,]+)\s*[-–to]+\s*\$?([\d,]+)',
        re.IGNORECASE
    )
    # Single value pattern: $X
    SINGLE_VALUE_PATTERN = re.compile(
        r'\$?\s*([\d,]+)(?:k|K)?\s*(?:per|/)?\s*(hour|hr|week|month|year|annual|annum)?',
        re.IGNORECASE
    )
    MAX_SENTENCES_TO_SEARCH = 5
    MAX_CHARS_TO_SEARCH = 1000

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

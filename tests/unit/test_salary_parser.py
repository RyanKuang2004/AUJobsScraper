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

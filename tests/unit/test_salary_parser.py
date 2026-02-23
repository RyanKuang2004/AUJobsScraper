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

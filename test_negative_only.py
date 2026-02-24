import sys
sys.path.insert(0, '.')
from aujobsscraper.utils.salary_parser import SalaryParser

# Test the exact string from the test
description = "-$50,000 per year"
print(f"Input: {repr(description)}")
print(f"Cleaned: {repr(description.replace('\\\\$', '$').replace('\\\\-', '-').replace('\\\\.', '.'))}")

result = SalaryParser.extract_salary(description)
print(f"Result: {result}")

if result is not None:
    print(f"ERROR: Expected None but got {result}")
    sys.exit(1)
else:
    print("PASS: Got None as expected")

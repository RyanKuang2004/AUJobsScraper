"""
Test script to verify Graduate Program classification works correctly.
"""

from jobly.utils.scraper_utils import extract_job_role

# Test cases for Graduate Program classification
test_cases = [
    # Cases that should be classified as "Graduate Program"
    ("ANAO Graduate Program", "Graduate Program"),
    ("Graduate Program - Multi-Discipline", "Graduate Program"),
    ("Graduate Development Programme", "Graduate Program"),
    ("Graduate Programme 2025", "Graduate Program"),
    ("Grad Program - Technology", "Graduate Program"),
    ("Technology Graduate Program", "Graduate Program"),
    ("Internship Program", "Graduate Program"),
    ("Software Engineering Internship Program", "Graduate Program"),
    
    # Cases that should NOT be classified as "Graduate Program"
    # (these should be classified based on their actual role after stop word removal)
    ("Graduate Software Engineer", "Software Developer"),  # "graduate" is seniority, not program
    ("Software Developer Graduate", "Software Developer"),
    ("Data Analyst", "Data Analyst"),
    ("AI Engineer", "AI Engineer"),
]

def test_graduate_program_classification():
    """Test that graduate program titles are correctly classified."""
    print("Testing Graduate Program Classification\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for title, expected_role in test_cases:
        actual_role = extract_job_role(title)
        status = "✓ PASS" if actual_role == expected_role else "✗ FAIL"
        
        if actual_role == expected_role:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | Title: {title:50} | Expected: {expected_role:25} | Got: {actual_role}")
    
    print("=" * 80)
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    return failed == 0

if __name__ == "__main__":
    success = test_graduate_program_classification()
    exit(0 if success else 1)

"""
Test script to validate AI/ML role classification improvements.
Tests the enhanced extract_job_role function against known misclassifications.
"""

from jobly.utils.scraper_utils import extract_job_role

# Test cases from user's actual data showing previous misclassifications
test_cases = [
    # Format: (job_title, expected_classification, previous_classification)
    ("Software Engineer - AI/ML", "AI Engineer", "Software Engineer"),
    ("AI / Machine Learning Developer (Azure AI, Cop...", "AI Engineer", "Software Engineer"),
    ("Principal Software Engineer - AI.", "AI Engineer", "Software Engineer"),
    ("AI Software Developer", "AI Engineer", "Software Engineer"),
    ("SailPoint Developer", "Software Engineer", "Software Engineer"),  # Should stay Software Engineer
    ("Adobe Developer - AEM, HTML, CSS, Java - Fed G...", "Software Engineer", "Software Engineer"),
    ("Sailpoint Developer", "Software Engineer", "Software Engineer"),
    ("Software Engineer II - Azure Container Registry", "Software Engineer", "Software Engineer"),  # Could be Cloud Engineer
    ("Senior Software Engineer (AIPS)", "Software Engineer", "Software Engineer"),
    ("AI Programmer – Racing NSW", "AI Engineer", "Software Engineer"),
    ("Principal Software Engineer - Gen AI", "AI Engineer", "Software Engineer"),
    ("Lead Software Engineer (AI) - $180K + Super + ...", "AI Engineer", "Software Engineer"),
    ("Software Trainer / Consultant", "Software Engineer", "Software Engineer"),
    ("Integration Developer - System Modernisation -...", "Software Engineer", "Software Engineer"),
    ("Ruby on Rails Developer", "Software Engineer", "Software Engineer"),
    ("Integration and AI Developer (Adelaide)", "AI Engineer", "Software Engineer"),
    ("AI Developer (Avatar & Conversational Systems)...", "AI Engineer", "Software Engineer"),
    ("Senior Machine Learning Developer", "Machine Learning Engineer", "Software Engineer"),
    ("AI Developer", "AI Engineer", "Software Engineer"),
    ("Senior/Staff Software Engineer – Video Streami...", "Software Engineer", "Software Engineer"),
    ("Full-Stack Software Engineer (AI-First)", "AI Engineer", "Software Engineer"),
    ("Junior/Senior Software Developer - Python, AI,...", "AI Engineer", "Software Engineer"),
    # Additional test cases
    ("Machine Learning Engineer", "Machine Learning Engineer", "Machine Learning Engineer"),
    ("Senior Machine Learning Engineer", "Machine Learning Engineer", "Machine Learning Engineer"),
    ("Python Engineer - AI/ML", "AI Engineer", "Machine Learning Engineer"),
    ("AI / ML Engineer", "AI Engineer", "Machine Learning Engineer"),
    ("ML Engineer - AI Search System", "Machine Learning Engineer", "Machine Learning Engineer"),
]

def run_tests():
    print("Testing AI/ML Classification Fix")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for job_title, expected, previous in test_cases:
        result = extract_job_role(job_title)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        # Show results - mark changes from previous classification
        changed_indicator = " (FIXED!)" if previous != expected and result == expected else ""
        
        print(f"\n{status}{changed_indicator}")
        print(f"  Title: {job_title[:60]}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        if previous != result and result != expected:
            print(f"  Previous: {previous}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"Success rate: {passed/len(test_cases)*100:.1f}%")
    
    if failed > 0:
        print("\nFailed tests need review!")
    else:
        print("\n✓ All tests passed!")

if __name__ == "__main__":
    run_tests()

"""
Tests for the extract_job_role function with taxonomy-based classification.
"""
import pytest
from jobly.utils.scraper_utils import extract_job_role


class TestJobRoleExtraction:
    """Test cases for job role classification."""
    
    def test_keyword_match_software_engineer(self):
        """Test direct keyword match for software engineer."""
        assert extract_job_role("Software Engineer") == "Software Engineer"
        assert extract_job_role("Backend Developer") == "Software Engineer"
        assert extract_job_role("Senior Software Engineer") == "Software Engineer"
        
    def test_keyword_match_full_stack(self):
        """Test full stack developer matching."""
        assert extract_job_role("Full Stack Developer") == "Full Stack Developer"
        assert extract_job_role("Fullstack Engineer") == "Full Stack Developer"
        
    def test_keyword_match_web_developer(self):
        """Test web developer matching with specific frameworks."""
        assert extract_job_role("React Developer") == "Web Developer"
        assert extract_job_role("Senior Frontend Developer") == "Web Developer"
        assert extract_job_role("Angular Developer") == "Web Developer"
        
    def test_keyword_match_mobile_developer(self):
        """Test mobile developer matching."""
        assert extract_job_role("iOS Developer") == "Mobile Developer"
        assert extract_job_role("Android Developer") == "Mobile Developer"
        assert extract_job_role("React Native Developer") == "Mobile Developer"
        
    def test_keyword_match_data_roles(self):
        """Test data engineering and analytics roles."""
        assert extract_job_role("Data Engineer") == "Data Engineer"
        assert extract_job_role("Data Scientist") == "Data Scientist"
        assert extract_job_role("Data Analyst") == "Data Analyst"
        assert extract_job_role("Power BI Analyst") == "Business Intelligence Analyst"
        
    def test_keyword_match_ai_ml(self):
        """Test AI and ML roles."""
        assert extract_job_role("Machine Learning Engineer") == "Machine Learning Engineer"
        assert extract_job_role("AI Engineer") == "AI Engineer"
        assert extract_job_role("NLP Engineer") == "NLP Engineer"
        
    def test_keyword_match_research_scientist(self):
        """Test research scientist including research assistant."""
        assert extract_job_role("Research Scientist") == "Research Scientist"
        assert extract_job_role("Research Assistant") == "Research Scientist"
        assert extract_job_role("Research Assistant - Eye Genetic Therapies") == "Research Scientist"
        
    def test_keyword_match_devops_cloud(self):
        """Test DevOps and cloud roles."""
        assert extract_job_role("DevOps Engineer") == "DevOps Engineer"
        assert extract_job_role("Site Reliability Engineer") == "DevOps Engineer"
        assert extract_job_role("AWS Cloud Engineer") == "Cloud Engineer"
        assert extract_job_role("Azure Engineer") == "Cloud Engineer"
        
    def test_keyword_match_qa_security(self):
        """Test QA and security roles."""
        assert extract_job_role("QA Engineer") == "QA Engineer"
        assert extract_job_role("Test Automation Engineer") == "QA Engineer"
        assert extract_job_role("Cyber Security Engineer") == "Cyber Security Engineer"
        assert extract_job_role("Security Analyst") == "Cyber Security Engineer"
        
    def test_keyword_match_management(self):
        """Test management and strategy roles."""
        assert extract_job_role("Engineering Manager") == "Engineering Manager"
        assert extract_job_role("Product Manager") == "Product Manager"
        assert extract_job_role("Business Analyst") == "Business Analyst"
        assert extract_job_role("Solutions Architect") == "Solutions Architect"
        
    def test_keyword_match_specialized(self):
        """Test specialized/niche roles."""
        assert extract_job_role("Quantitative Analyst") == "Quantitative Analyst"
        assert extract_job_role("GIS Analyst") == "GIS Analyst"
        assert extract_job_role("Technical Writer") == "Technical Writer"
        assert extract_job_role("Sales Engineer") == "Sales Engineer"
        
    def test_company_name_removal(self):
        """Test that company names are removed from titles."""
        assert extract_job_role("Google Software Engineer", company_name="Google") == "Software Engineer"
        assert extract_job_role("Atlassian Backend Developer", company_name="Atlassian") == "Software Engineer"
        assert extract_job_role("Microsoft Cloud Engineer", company_name="Microsoft") == "Cloud Engineer"
        
    def test_seniority_removal(self):
        """Test that seniority terms are removed."""
        assert extract_job_role("Senior Software Engineer") == "Software Engineer"
        assert extract_job_role("Junior Data Analyst") == "Data Analyst"
        assert extract_job_role("Lead DevOps Engineer") == "DevOps Engineer"
        assert extract_job_role("Principal Machine Learning Engineer") == "Machine Learning Engineer"
        
    def test_graduate_internship_removal(self):
        """Test that graduate and internship terms are removed."""
        assert extract_job_role("Graduate Software Engineer") == "Software Engineer"
        assert extract_job_role("Software Engineering Internship") == "Software Engineer"
        assert extract_job_role("Data Science Graduate Program") == "Data Scientist"
        
    def test_year_removal(self):
        """Test that years and year ranges are removed."""
        assert extract_job_role("Software Engineer 2025") == "Software Engineer"
        assert extract_job_role("Graduate Program 2025/26 - Data Analyst") == "Data Analyst"
        
    def test_embedding_fallback(self):
        """Test embedding-based matching for titles without exact keywords."""
        # These should use embedding similarity
        result = extract_job_role("Coder")  # Should match Software Engineer via embedding
        assert result in ["Software Engineer", "Specialized"]
        
        result = extract_job_role("Algorithm Engineer")  # Should match AI/ML role
        assert result in ["AI Engineer", "Machine Learning Engineer", "Software Engineer", "Specialized"]
        
    def test_low_confidence_specialized(self):
        """Test that unrelated job titles return 'Specialized'."""
        # Titles completely outside tech/engineering domain with very low semantic similarity
        assert extract_job_role("Chef") == "Specialized"
        assert extract_job_role("Nurse") == "Specialized"
        assert extract_job_role("Plumber") == "Specialized"
        assert extract_job_role("Hairdresser") == "Specialized"
        
    def test_empty_title(self):
        """Test handling of empty or None titles."""
        assert extract_job_role("") == "Specialized"
        assert extract_job_role(None) == "Specialized"
        
    def test_complex_title_cleaning(self):
        """Test complex titles with multiple noise elements."""
        title = "Senior Graduate Software Engineer (Backend) - Google 2025/26"
        result = extract_job_role(title, company_name="Google")
        assert result == "Software Engineer"
        
    def test_longest_keyword_match(self):
        """Test that longest/most specific keyword is preferred."""
        # "machine learning engineer" should match before just "engineer"
        assert extract_job_role("Machine Learning Engineer") == "Machine Learning Engineer"
        # "full stack" should match before "developer"
        assert extract_job_role("Full Stack Developer") == "Full Stack Developer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

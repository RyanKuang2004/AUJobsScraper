"""Tests for SeekScraper class."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from bs4 import BeautifulSoup
from jobly.scrapers.seek_scraper import SeekScraper


@pytest.fixture
def seek_scraper(mock_env_vars):
    """Create a SeekScraper instance for testing."""
    with patch('jobly.scrapers.base_scraper.JobDatabase'):
        scraper = SeekScraper()
        scraper.db = MagicMock()
        return scraper


@pytest.fixture
def sample_job_html():
    """Sample HTML for a job posting."""
    return """
    <html>
        <body>
            <h1 data-automation="job-detail-title">Senior Python Developer</h1>
            <span data-automation="advertiser-name">Tech Company Pty Ltd</span>
            <span data-automation="job-detail-location">Sydney NSW</span>
            <span data-automation="job-detail-salary">$120,000 - $150,000 per year</span>
            <div data-automation="jobAdDetails">
                <h2>About the Role</h2>
                <p>We are looking for an experienced Python developer to join our team.</p>
                <h3>Requirements:</h3>
                <ul>
                    <li>5+ years of Python experience</li>
                    <li>Experience with Django and Flask</li>
                    <li>Strong SQL skills</li>
                </ul>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_listing_html():
    """Sample HTML for job listings page."""
    return """
    <html>
        <body>
            <div>
                <a data-automation="jobTitle" href="/job/12345?ref=search">Python Developer</a>
                <a data-automation="jobTitle" href="/job/67890?ref=search">Senior Python Engineer</a>
                <a data-automation="jobTitle" href="https://www.seek.com.au/job/11111?ref=search">Lead Developer</a>
            </div>
        </body>
    </html>
    """


class TestSeekScraper:
    """Test suite for SeekScraper."""

    def test_init(self, seek_scraper):
        """Test SeekScraper initialization."""
        assert seek_scraper.platform == "seek"
        assert seek_scraper.base_url == "https://www.seek.com.au"

    def test_remove_html_tags(self, seek_scraper):
        """Test HTML tag removal."""
        html_content = "<h1>Title</h1><p>This is a <strong>test</strong>.</p>"
        result = seek_scraper._remove_html_tags(html_content)
        # BeautifulSoup adds newlines for block elements
        assert "Title" in result
        assert "This is a" in result
        assert "test" in result
        # Verify no HTML tags remain
        assert "<" not in result and ">" not in result

    def test_remove_html_tags_empty(self, seek_scraper):
        """Test HTML tag removal with empty content."""
        result = seek_scraper._remove_html_tags("")
        assert result == ""

    def test_remove_html_tags_none(self, seek_scraper):
        """Test HTML tag removal with None content."""
        result = seek_scraper._remove_html_tags(None)
        assert result == ""

    @pytest.mark.parametrize("title,expected_seniority", [
        ("Senior Python Developer", "Senior"),
        ("Lead Software Engineer", "Senior"),
        ("Principal Architect", "Senior"),
        ("Manager - Development", "Senior"),
        ("Junior Developer", "Junior"),
        ("Graduate Software Engineer", "Junior"),
        ("Entry Level Programmer", "Junior"),
        ("Intermediate Developer", "Intermediate"),
        ("Mid-Level Engineer", "Intermediate"),
        ("Software Developer", "N/A"),
        ("Full Stack Engineer", "N/A"),
    ])
    def test_determine_seniority(self, seek_scraper, title, expected_seniority):
        """Test seniority determination from job titles."""
        result = seek_scraper._determine_seniority(title)
        assert result == expected_seniority

    @pytest.mark.asyncio
    async def test_get_job_links_success(self, seek_scraper, sample_listing_html):
        """Test extracting job links from listing page."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value=sample_listing_html)
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            links = await seek_scraper._get_job_links(mock_page, "https://seek.com.au/jobs")
        
        assert len(links) == 3
        # The scraper strips query parameters from relative URLs before making them absolute
        assert links[0] == "https://www.seek.com.au/job/12345"
        assert links[1] == "https://www.seek.com.au/job/67890"
        # Absolute URLs are kept as-is (including query params)
        assert links[2] == "https://www.seek.com.au/job/11111?ref=search"

    @pytest.mark.asyncio
    async def test_get_job_links_no_results(self, seek_scraper):
        """Test handling of no search results."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html><body>No matching search results</body></html>")
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            links = await seek_scraper._get_job_links(mock_page, "https://seek.com.au/jobs")
        
        assert links == []

    @pytest.mark.asyncio
    async def test_get_job_links_error(self, seek_scraper):
        """Test error handling in job link extraction."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            links = await seek_scraper._get_job_links(mock_page, "https://seek.com.au/jobs")
        
        assert links == []

    @pytest.mark.asyncio
    async def test_process_job_success(self, seek_scraper, sample_job_html):
        """Test successful job processing."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value=sample_job_html)
        
        seek_scraper.save_job = MagicMock(return_value={"id": 1})
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await seek_scraper._process_job(mock_page, "https://seek.com.au/job/12345")
        
        # Verify save_job was called
        assert seek_scraper.save_job.called
        
        # Get the job data that was passed to save_job
        job_data = seek_scraper.save_job.call_args[0][0]
        
        # Verify all fields are extracted correctly
        assert job_data["job_title"] == "Senior Python Developer"
        assert job_data["company"] == "Tech Company Pty Ltd"
        assert job_data["locations"] == ["Sydney NSW"]
        assert job_data["source_urls"] == ["https://seek.com.au/job/12345"]
        assert job_data["salary"] == "$120,000 - $150,000 per year"
        assert job_data["seniority"] == "Senior"
        assert job_data["platforms"] == ["seek"]
        assert job_data["llm_analysis"] is None
        assert "Python developer" in job_data["description"]

    @pytest.mark.asyncio
    async def test_process_job_minimal_data(self, seek_scraper):
        """Test job processing with minimal/missing data."""
        minimal_html = "<html><body></body></html>"
        
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value=minimal_html)
        
        seek_scraper.save_job = MagicMock(return_value={"id": 1})
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await seek_scraper._process_job(mock_page, "https://seek.com.au/job/12345")
        
        job_data = seek_scraper.save_job.call_args[0][0]
        
        # Verify defaults are used for missing fields
        assert job_data["job_title"] == "Unknown Title"
        assert job_data["company"] == "Unknown Company"
        assert job_data["locations"] == ["Australia"]
        assert job_data["salary"] is None

    @pytest.mark.asyncio
    async def test_process_job_error_handling(self, seek_scraper):
        """Test error handling during job processing."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Page load failed"))
        
        # Should not raise exception
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await seek_scraper._process_job(mock_page, "https://seek.com.au/job/12345")


@pytest.mark.asyncio
async def test_extract_all_fields_demonstration(seek_scraper, sample_job_html):
    """
    Demonstration test that prints all extracted fields from a job posting.
    This test is useful for verifying what data is being extracted.
    """
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value=sample_job_html)
    
    seek_scraper.save_job = MagicMock(return_value={"id": 1})
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await seek_scraper._process_job(mock_page, "https://seek.com.au/job/12345")
    
    # Get the extracted job data
    job_data = seek_scraper.save_job.call_args[0][0]
    
    # Print all extracted fields
    print("\n" + "="*80)
    print("EXTRACTED JOB FIELDS DEMONSTRATION")
    print("="*80)
    print(f"\n📋 Job Title: {job_data['job_title']}")
    print(f"🏢 Company: {job_data['company']}")
    print(f"📍 Locations: {', '.join(job_data['locations'])}")
    print(f"🔗 Source URLs: {', '.join(job_data['source_urls'])}")
    print(f"💰 Salary: {job_data['salary']}")
    print(f"👔 Seniority: {job_data['seniority']}")
    print(f"🌐 Platforms: {', '.join(job_data['platforms'])}")
    print(f"🤖 LLM Analysis: {job_data['llm_analysis']}")
    print(f"\n📄 Description (first 200 chars):\n{job_data['description'][:200]}...")
    print("\n" + "="*80)
    print("\n✅ All fields extracted successfully!")
    print("="*80 + "\n")
    
    # Verify all expected fields are present
    expected_fields = [
        "job_title", "company", "locations", "source_urls",
        "description", "salary", "seniority", "llm_analysis", "platforms"
    ]
    
    for field in expected_fields:
        assert field in job_data, f"Missing field: {field}"

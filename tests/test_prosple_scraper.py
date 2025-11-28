import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from bs4 import BeautifulSoup
from jobly.scrapers.prosple_scraper import ProspleScraper

@pytest.fixture
def scraper():
    with patch("jobly.scrapers.prosple_scraper.BaseScraper.__init__"):
        scraper = ProspleScraper()
        scraper.logger = MagicMock()
        scraper.db = MagicMock()
        scraper.save_job = MagicMock()
        return scraper

@pytest.mark.asyncio
async def test_get_job_links(scraper):
    mock_page = AsyncMock()
    
    # Mock HTML content for list page
    html_content = """
    <div>
        <h2 class="sc-dOfePm dyaRTx heading sc-692f12d5-0 bTRRDW">
            <a href="/graduate-employers/company-a/jobs/job-1">Job 1</a>
        </h2>
        <div>
            <span>AUD 60,000 - 70,000 / Year</span>
        </div>
        
        <h2 class="sc-dOfePm dyaRTx heading sc-692f12d5-0 bTRRDW">
            <a href="https://other.com/job-2">Job 2</a>
        </h2>
    </div>
    """
    mock_page.content.return_value = html_content
    
    links = await scraper._get_job_links(mock_page, "http://test.url")
    
    assert len(links) == 2
    assert links[0]['url'] == "https://au.prosple.com/graduate-employers/company-a/jobs/job-1"
    assert links[0]['salary'] is None
    assert links[1]['url'] == "https://other.com/job-2"
    assert links[1]['salary'] is None

@pytest.mark.asyncio
async def test_process_job(scraper):
    mock_page = AsyncMock()
    
    # Mock HTML content for job page
    html_content = """
    <html>
        <body>
            <h1>Graduate Developer</h1>
            <a href="/graduate-employers/tech-corp">Tech Corp</a>
            <header>Sydney, NSW</header>
            <main>
                <div>Opportunity details</div>
                <p>We are looking for a developer.</p>
            </main>
        </body>
    </html>
    """
    mock_page.content.return_value = html_content
    
    job_info = {
        "url": "https://au.prosple.com/job-1",
        "salary": "AUD 65k"
    }
    
    await scraper._process_job(mock_page, job_info)
    
    scraper.save_job.assert_called_once()
    saved_data = scraper.save_job.call_args[0][0]
    
    assert saved_data['job_title'] == "Graduate Developer"
    assert saved_data['company'] == "Tech Corp"
    assert saved_data['salary'] == "AUD 65k"
    assert "We are looking for a developer" in saved_data['description']
    assert saved_data['seniority'] == "Junior" # Graduate -> Junior
    assert saved_data['posted_at'] is None

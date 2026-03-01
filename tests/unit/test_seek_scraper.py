import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aujobsscraper.scrapers.seek_scraper import SeekScraper


def test_seek_scrape_is_async_generator():
    scraper = SeekScraper()
    gen = scraper.scrape()
    assert inspect.isasyncgen(gen)


@pytest.mark.asyncio
async def test_seek_scrape_yields_one_batch_per_page():
    """Each call to process_jobs_concurrently produces one yielded batch."""
    scraper = SeekScraper()

    # Simulate two pages: page 1 → 2 jobs, page 2 → 1 job, page 3 → empty (stop)
    link_responses = [
        ["https://seek.com.au/job/1", "https://seek.com.au/job/2"],
        ["https://seek.com.au/job/3"],
        [],
    ]
    link_call_count = 0

    async def fake_get_job_links(page, url):
        nonlocal link_call_count
        links = link_responses[min(link_call_count, len(link_responses) - 1)]
        link_call_count += 1
        return links

    async def fake_process_jobs_concurrently(context, urls):
        for url in urls:
            job = MagicMock()
            job.job_title = f"Job from {url}"
            scraper._results.append(job)

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch.object(scraper, '_get_job_links', fake_get_job_links), \
         patch.object(scraper, 'process_jobs_concurrently', fake_process_jobs_concurrently), \
         patch('aujobsscraper.scrapers.seek_scraper.async_playwright') as mock_pw:
        mock_pw.return_value.__aenter__.return_value = mock_p
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        batches = []
        async for batch in scraper.scrape():
            batches.append(list(batch))

    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


@pytest.mark.asyncio
async def test_seek_scrape_skips_known_urls():
    scraper = SeekScraper()
    skip_urls = {"https://seek.com.au/job/1"}

    async def fake_get_job_links(page, url):
        return ["https://seek.com.au/job/1", "https://seek.com.au/job/2"]

    processed_urls = []

    async def fake_process_jobs_concurrently(context, urls):
        processed_urls.extend(urls)
        for url in urls:
            job = MagicMock()
            scraper._results.append(job)

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch.object(scraper, '_get_job_links', fake_get_job_links), \
         patch.object(scraper, 'process_jobs_concurrently', fake_process_jobs_concurrently), \
         patch('aujobsscraper.scrapers.seek_scraper.async_playwright') as mock_pw:
        mock_pw.return_value.__aenter__.return_value = mock_p
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch('aujobsscraper.scrapers.seek_scraper.settings') as mock_settings:
            mock_settings.initial_run = False
            mock_settings.search_keywords = ["software engineer"]
            mock_settings.max_pages = 1
            mock_settings.days_from_posted = 7
            mock_settings.initial_days_from_posted = 30
            mock_settings.concurrency = 2

            async for _ in scraper.scrape(skip_urls=skip_urls):
                pass

    assert "https://seek.com.au/job/1" not in processed_urls
    assert "https://seek.com.au/job/2" in processed_urls

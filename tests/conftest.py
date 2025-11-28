"""Test configuration and fixtures for pytest."""

import pytest
from unittest.mock import Mock, MagicMock
import os


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = MagicMock()
    
    # Mock table responses
    table_mock = MagicMock()
    client.table.return_value = table_mock
    
    # Chain methods
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.execute.return_value = Mock(data=[])
    
    return client


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key-123")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


@pytest.fixture
def sample_job_data():
    """Sample job posting data for testing."""
    return {
        "job_title": "Senior Python Developer",
        "company": "Tech Company",
        "locations": ["Sydney, NSW"],
        "source_urls": ["https://seek.com.au/job/123"],
        "description": "We are looking for a senior Python developer...",
        "salary": "$120,000 - $150,000",
        "seniority": "Senior",
        "platforms": ["seek"]
    }

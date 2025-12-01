"""Tests for update_seek_titles migration script."""

import pytest
from unittest.mock import MagicMock, patch
from scripts.update_seek_titles import SeekTitleUpdater


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    with patch('scripts.update_seek_titles.JobDatabase') as mock_db:
        yield mock_db


@pytest.fixture
def sample_seek_jobs():
    """Sample Seek job data."""
    return [
        {
            'id': '1',
            'company': 'Tech Corp',
            'job_title': 'Senior Python Developer (Remote) - 2025',
            'fingerprint': 'tech corp|senior python developer (remote) - 2025',
            'platforms': ['seek']
        },
        {
            'id': '2',
            'company': 'Data Inc',
            'job_title': 'Graduate Machine Learning Engineer - Sydney',
            'fingerprint': 'data inc|graduate machine learning engineer - sydney',
            'platforms': ['seek']
        },
        {
            'id': '3',
            'company': 'Cloud Solutions',
            'job_title': 'Cloud Engineer',  # Already clean
            'fingerprint': 'cloud solutions|cloud engineer',
            'platforms': ['seek']
        },
    ]


class TestSeekTitleUpdater:
    """Test suite for SeekTitleUpdater."""
    
    def test_init_dry_run_mode(self):
        """Test initialization in dry-run mode."""
        with patch('scripts.update_seek_titles.JobDatabase'):
            updater = SeekTitleUpdater(dry_run=True)
            assert updater.dry_run is True
            assert updater.stats['total_jobs'] == 0
            assert updater.stats['titles_changed'] == 0
    
    def test_init_live_mode(self):
        """Test initialization in live mode."""
        with patch('scripts.update_seek_titles.JobDatabase'):
            updater = SeekTitleUpdater(dry_run=False)
            assert updater.dry_run is False
    
    def test_clean_title_removes_noise(self):
        """Test that clean_title removes noise from job titles."""
        with patch('scripts.update_seek_titles.JobDatabase'):
            updater = SeekTitleUpdater()
            
            # Test various noisy titles
            assert updater.clean_title('Senior Python Developer (Remote) - 2025') == 'Python Developer'
            assert updater.clean_title('Graduate Machine Learning Engineer - Sydney') == 'Machine Learning Engineer'
            # Cloud Engineer - Azure: "Azure" is kept as a modifier, "- Azure" is removed
            result = updater.clean_title('Cloud Engineer - Azure')
            # The dash separator and location/company info should be cleaned
            assert 'Cloud Engineer' in result or result == 'Azure Cloud Engineer'
    
    def test_clean_title_handles_already_clean(self):
        """Test that already clean titles remain unchanged."""
        with patch('scripts.update_seek_titles.JobDatabase'):
            updater = SeekTitleUpdater()
            
            assert updater.clean_title('Cloud Engineer') == 'Cloud Engineer'
            assert updater.clean_title('Software Developer') == 'Software Developer'
    
    def test_clean_title_handles_unknown(self):
        """Test that Unknown Title is not modified."""
        with patch('scripts.update_seek_titles.JobDatabase'):
            updater = SeekTitleUpdater()
            
            assert updater.clean_title('Unknown Title') == 'Unknown Title'
            assert updater.clean_title('') == ''
    
    def test_generate_fingerprint(self):
        """Test fingerprint generation."""
        with patch('scripts.update_seek_titles.JobDatabase'):
            updater = SeekTitleUpdater()
            
            # Test using the actual static method (not mocked)
            from jobly.db.job_database import JobDatabase
            fingerprint = JobDatabase._generate_fingerprint('Tech Corp', 'Python Developer')
            assert fingerprint == 'tech corp|python developer'
            
            fingerprint = JobDatabase._generate_fingerprint('DATA INC', 'Machine Learning Engineer')
            assert fingerprint == 'data inc|machine learning engineer'
    
    def test_update_job_dry_run(self):
        """Test that update_job doesn't modify database in dry-run mode."""
        with patch('scripts.update_seek_titles.JobDatabase'):
            updater = SeekTitleUpdater(dry_run=True)
            
            # Should return True without calling database
            result = updater.update_job('job-id-123', 'New Title', 'new|fingerprint')
            assert result is True
    
    @patch('scripts.update_seek_titles.JobDatabase')
    def test_fetch_seek_jobs(self, mock_db_class, sample_seek_jobs):
        """Test fetching Seek jobs from database."""
        # Setup mock
        mock_db_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.data = sample_seek_jobs
        mock_db_instance.supabase.table.return_value.select.return_value.contains.return_value.execute.return_value = mock_response
        mock_db_class.return_value = mock_db_instance
        
        updater = SeekTitleUpdater()
        jobs = updater.fetch_seek_jobs()
        
        assert len(jobs) == 3
        assert all('seek' in job['platforms'] for job in jobs)
    
    @patch('scripts.update_seek_titles.JobDatabase')
    def test_process_jobs_counts_changes(self, mock_db_class, sample_seek_jobs):
        """Test that process_jobs correctly counts changes."""
        # Setup mock
        mock_db_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.data = sample_seek_jobs
        mock_db_instance.supabase.table.return_value.select.return_value.contains.return_value.execute.return_value = mock_response
        mock_db_class.return_value = mock_db_instance
        
        updater = SeekTitleUpdater(dry_run=True)
        updater.process_jobs()
        
        # Two titles should change, one should remain the same
        assert updater.stats['total_jobs'] == 3
        assert updater.stats['titles_changed'] == 2  # Jobs 1 and 2
        assert updater.stats['titles_unchanged'] == 1  # Job 3
        assert updater.stats['errors'] == 0
    
    @patch('scripts.update_seek_titles.JobDatabase')
    def test_process_jobs_stores_examples(self, mock_db_class, sample_seek_jobs):
        """Test that process_jobs stores example changes."""
        # Setup mock
        mock_db_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.data = sample_seek_jobs
        mock_db_instance.supabase.table.return_value.select.return_value.contains.return_value.execute.return_value = mock_response
        mock_db_class.return_value = mock_db_instance
        
        updater = SeekTitleUpdater(dry_run=True)
        updater.process_jobs()
        
        # Should have 2 examples (only changed titles)
        assert len(updater.examples) == 2
        assert updater.examples[0][0] == 'Tech Corp'  # company
        assert updater.examples[0][1] == 'Senior Python Developer (Remote) - 2025'  # old title
        assert updater.examples[0][2] == 'Python Developer'  # new title

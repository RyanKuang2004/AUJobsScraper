"""
Unit tests for scripts/run_scraper.py

Tests command-line argument parsing and scraper instantiation.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

# Add scripts directory to path for importing
from scripts.run_scraper import parse_args, SCRAPERS, main


class TestRunScraperArguments:
    """Test argument parsing for run_scraper.py"""
    
    def test_default_scraper_is_seek(self):
        """Test that the default scraper is 'seek' when no arguments provided."""
        with patch.object(sys, 'argv', ['run_scraper.py']):
            args = parse_args()
            assert args.scraper == 'seek'
    
    def test_seek_scraper_argument(self):
        """Test parsing --scraper seek argument."""
        with patch.object(sys, 'argv', ['run_scraper.py', '--scraper', 'seek']):
            args = parse_args()
            assert args.scraper == 'seek'
    
    def test_prosple_scraper_argument(self):
        """Test parsing --scraper prosple argument."""
        with patch.object(sys, 'argv', ['run_scraper.py', '--scraper', 'prosple']):
            args = parse_args()
            assert args.scraper == 'prosple'
    
    def test_gradconnection_scraper_argument(self):
        """Test parsing --scraper gradconnection argument."""
        with patch.object(sys, 'argv', ['run_scraper.py', '--scraper', 'gradconnection']):
            args = parse_args()
            assert args.scraper == 'gradconnection'
    
    def test_invalid_scraper_raises_error(self):
        """Test that an invalid scraper name raises SystemExit."""
        with patch.object(sys, 'argv', ['run_scraper.py', '--scraper', 'invalid']):
            with pytest.raises(SystemExit):
                parse_args()


class TestScraperRegistry:
    """Test scraper registry configuration"""
    
    def test_all_scrapers_registered(self):
        """Test that all scrapers are in the registry."""
        assert 'seek' in SCRAPERS
        assert 'prosple' in SCRAPERS
        assert 'gradconnection' in SCRAPERS
    
    def test_scraper_classes_are_valid(self):
        """Test that all registered scrapers are classes."""
        from jobly.scrapers import SeekScraper
        from jobly.scrapers.prosple_scraper import ProspleScraper
        from jobly.scrapers.gradconnection_scraper import GradConnectionScraper
        
        assert SCRAPERS['seek'] == SeekScraper
        assert SCRAPERS['prosple'] == ProspleScraper
        assert SCRAPERS['gradconnection'] == GradConnectionScraper


class TestMainFunction:
    """Test main function execution"""
    
    @patch('scripts.run_scraper.parse_args')
    @patch('scripts.run_scraper.SCRAPERS')
    def test_main_runs_correct_scraper(self, mock_scrapers, mock_parse_args):
        """Test that main function instantiates and runs the correct scraper."""
        # Mock the arguments
        mock_args = MagicMock()
        mock_args.scraper = 'seek'
        mock_parse_args.return_value = mock_args
        
        # Mock the scraper class and instance
        mock_scraper_instance = MagicMock()
        mock_scraper_class = MagicMock(return_value=mock_scraper_instance)
        mock_scrapers.__getitem__.return_value = mock_scraper_class
        
        # Run main
        result = main()
        
        # Verify the scraper was instantiated and run
        mock_scraper_class.assert_called_once()
        mock_scraper_instance.run.assert_called_once()
        assert result == 0
    
    @patch('scripts.run_scraper.parse_args')
    @patch('scripts.run_scraper.SCRAPERS')
    def test_main_handles_exceptions(self, mock_scrapers, mock_parse_args):
        """Test that main function handles exceptions and returns 1."""
        # Mock the arguments
        mock_args = MagicMock()
        mock_args.scraper = 'seek'
        mock_parse_args.return_value = mock_args
        
        # Mock scraper to raise exception
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.run.side_effect = Exception("Test error")
        mock_scraper_class = MagicMock(return_value=mock_scraper_instance)
        mock_scrapers.__getitem__.return_value = mock_scraper_class
        
        # Run main
        result = main()
        
        # Verify error handling
        assert result == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

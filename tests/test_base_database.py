"""Tests for BaseDatabase class."""

import pytest
from unittest.mock import patch, MagicMock
from jobly.db import BaseDatabase


def test_base_database_init_success(mock_env_vars):
    """Test successful initialization of BaseDatabase."""
    with patch('jobly.db.base_database.create_client') as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        
        db = BaseDatabase()
        
        assert db.supabase == mock_client
        mock_create.assert_called_once_with(
            "https://test.supabase.co",
            "test-key-123"
        )


def test_base_database_init_missing_env():
    """Test BaseDatabase raises error when env vars missing."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_KEY must be set"):
            BaseDatabase()

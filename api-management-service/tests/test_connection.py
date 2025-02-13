"""Tests for database connection and environment variable loading."""
import os
import pytest
from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from ..config import Settings, EnvironmentType
from ..database.connection import get_db, engine

def test_settings_from_env_variables():
    """Test loading settings from environment variables."""
    test_env = {
        "ENV": "testing",
        "DB_HOST": "test-host",
        "DB_PORT": "3307",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "REDIS_HOST": "redis-host"
    }
    
    with patch.dict(os.environ, test_env):
        settings = Settings()
        assert settings.ENV == EnvironmentType.TESTING
        assert settings.DB_HOST == "test-host"
        assert settings.DB_PORT == 3307
        assert settings.DB_NAME == "test_db"
        assert settings.DB_USER == "test_user"
        assert settings.DB_PASSWORD == "test_pass"
        assert settings.REDIS_HOST == "redis-host"

def test_database_url_construction():
    """Test correct construction of database URL."""
    test_env = {
        "DB_HOST": "test-host",
        "DB_PORT": "3306",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "REDIS_HOST": "redis-host"
    }
    
    with patch.dict(os.environ, test_env):
        settings = Settings()
        expected_url = "mysql+pymysql://test_user:test_pass@test-host:3306/test_db"
        assert settings.get_database_url() == expected_url

def test_connection_pool_settings():
    """Test database connection pool configuration."""
    test_env = {
        "DB_HOST": "test-host",
        "DB_PORT": "3306",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "DB_POOL_SIZE": "10",
        "DB_POOL_TIMEOUT": "60",
        "REDIS_HOST": "redis-host"
    }
    
    with patch.dict(os.environ, test_env):
        settings = Settings()
        assert settings.DB_POOL_SIZE == 10
        assert settings.DB_POOL_TIMEOUT == 60

def test_missing_required_settings():
    """Test error handling for missing required settings."""
    test_env = {
        "DB_HOST": "test-host",
        # Missing DB_NAME
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "REDIS_HOST": "redis-host"
    }
    
    with pytest.raises(ValueError):
        with patch.dict(os.environ, test_env, clear=True):
            Settings()

def test_invalid_environment_type():
    """Test validation of environment type."""
    test_env = {
        "ENV": "invalid",
        "DB_HOST": "test-host",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "REDIS_HOST": "redis-host"
    }
    
    with pytest.raises(ValueError):
        with patch.dict(os.environ, test_env):
            Settings()

def test_invalid_log_level():
    """Test validation of log level setting."""
    test_env = {
        "LOG_LEVEL": "INVALID",
        "DB_HOST": "test-host",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "REDIS_HOST": "redis-host"
    }
    
    with pytest.raises(ValueError):
        with patch.dict(os.environ, test_env):
            Settings()

def test_database_connection():
    """Test database connection using environment settings."""
    test_env = {
        "DB_HOST": "test-host",
        "DB_PORT": "3306",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "REDIS_HOST": "redis-host"
    }
    
    with patch.dict(os.environ, test_env):
        settings = Settings()
        with patch('sqlalchemy.create_engine') as mock_create_engine:
            # Mock the engine creation to avoid actual database connection
            mock_create_engine.return_value = engine
            
            # Test the get_db generator
            db = next(get_db())
            assert db is not None

def test_redis_url_construction():
    """Test correct construction of Redis URL with and without password."""
    # Test without password
    test_env = {
        "REDIS_HOST": "redis-host",
        "REDIS_PORT": "6379",
        "DB_HOST": "test-host",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass"
    }
    
    with patch.dict(os.environ, test_env):
        settings = Settings()
        assert settings.get_redis_url() == "redis://redis-host:6379/0"
    
    # Test with password
    test_env["REDIS_PASSWORD"] = "redis-pass"
    with patch.dict(os.environ, test_env):
        settings = Settings()
        assert settings.get_redis_url() == "redis://:redis-pass@redis-host:6379/0"
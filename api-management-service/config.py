"""Configuration management system for the API Management Service.

This module provides environment-specific configuration handling using Pydantic BaseSettings.
It includes settings for database, Redis, API rate limits, caching, and logging.
"""

from typing import Optional
from pydantic import BaseSettings, Field, validator
import os
import logging
from enum import Enum

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

# PUBLIC_INTERFACE
class Settings(BaseSettings):
    """Main configuration settings class using Pydantic BaseSettings for validation."""
    
    # Environment Settings
    ENV: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT,
        description="Current environment (development/testing/production)"
    )
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    
    # Database Settings
    DB_HOST: str = Field(..., description="Amazon RDS host")
    DB_PORT: int = Field(default=3306, description="Database port")
    DB_NAME: str = Field(..., description="Database name")
    DB_USER: str = Field(..., description="Database username")
    DB_PASSWORD: str = Field(..., description="Database password")
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout in seconds")
    
    # Redis Settings
    REDIS_HOST: str = Field(..., description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    
    # API Settings
    API_RATE_LIMIT: int = Field(default=100, description="API rate limit per minute")
    API_RATE_LIMIT_BURST: int = Field(default=20, description="API rate limit burst size")
    API_TIMEOUT: int = Field(default=30, description="API timeout in seconds")
    
    # Cache Settings
    CACHE_TTL: int = Field(default=300, description="Cache TTL in seconds")
    CACHE_ENABLED: bool = Field(default=True, description="Enable/disable caching")
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate that the log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()

    @validator("ENV")
    def validate_environment(cls, v):
        """Validate the environment type."""
        if v not in EnvironmentType:
            raise ValueError(f"Invalid environment. Must be one of {list(EnvironmentType)}")
        return v

    def configure_logging(self):
        """Configure logging based on the settings."""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL),
            format=self.LOG_FORMAT,
            filename=self.LOG_FILE
        )

    def get_database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def get_redis_url(self) -> str:
        """Get the Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Create a global settings instance
settings = Settings()
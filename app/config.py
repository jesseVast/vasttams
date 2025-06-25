"""
Configuration management for TAMS API
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API settings
    api_title: str = "TAMS API"
    api_version: str = "6.0.0"
    api_description: str = "Time-addressable Media Store API"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # VAST store settings
    vast_data_dir: str = "./vast_data"
    
    # VAST Database settings
    vast_endpoint: str = "http://localhost:8080"
    vast_access_key: str = "test-access-key"
    vast_secret_key: str = "test-secret-key"
    vast_bucket: str = "tams-bucket"
    vast_schema: str = "tams-schema"
    
    # Database settings (for future use)
    database_url: Optional[str] = None
    
    # Security settings
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Storage settings
    storage_type: str = "http_object_store"
    storage_base_url: str = "https://storage.example.com"
    
    # Webhook settings
    webhook_timeout: int = 30
    webhook_retry_attempts: int = 3
    
    # S3 settings for flow segment storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "tams-segments"
    s3_use_ssl: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def update_settings(**kwargs):
    """Update settings (for testing)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    
    for key, value in kwargs.items():
        if hasattr(_settings, key):
            setattr(_settings, key, value) 
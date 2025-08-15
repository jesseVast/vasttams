"""Configuration management for TAMS application"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os
import json

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_CORS_ORIGINS = ["*"]
DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
DEFAULT_CORS_HEADERS = ["*"]
DEFAULT_PRESIGNED_URL_TIMEOUT = 3600


class Settings(BaseSettings):
    """Application settings"""
    
    # API settings
    api_title: str = "TAMS API"
    api_version: str = "7.0"
    api_description: str = "Time-addressable Media Store API"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = Field(default=DEFAULT_PORT, description="Application port")
    debug: bool = True
    
    # VAST Database settings
    #vast_endpoint: str = "http://100.100.0.1:9090"
    vast_endpoint: str = "http://172.200.204.90"
    vast_access_key: str = "SRSPW0DQT9T70Y787U68"
    vast_secret_key: str = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    vast_bucket: str = "jthaloor-db"
    vast_schema: str = "tams"
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
    
    # S3 settings for flow segment storage
    #s3_endpoint_url: str = "http://100.100.0.2:9090"
    s3_endpoint_url: str = "http://172.200.204.91"
    s3_access_key_id: str = "SRSPW0DQT9T70Y787U68"
    s3_secret_access_key: str = "WkKLxvG7YkAdSMuHjFsZG5Ou7BS1mDQGnr"
    s3_bucket_name: str = "jthaloor-s3"
    s3_use_ssl: bool = False
    s3_presigned_url_timeout: int = Field(default=DEFAULT_PRESIGNED_URL_TIMEOUT, description="Presigned URL timeout in seconds (default: 1 hour)")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = "TAMS_"  # Environment variables will be prefixed with TAMS_

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load configuration from mounted file if it exists
        self._load_mounted_config()

    def _load_mounted_config(self):
        """Load configuration from mounted config file"""
        config_file_path = "/etc/tams/config.json"
        if os.path.exists(config_file_path):
            try:
                with open(config_file_path, 'r') as f:
                    config_data = json.load(f)
                
                # Update settings with mounted config (takes precedence over defaults)
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                        
            except (json.JSONDecodeError, IOError) as e:
                # Log error but continue with default values
                print(f"Warning: Could not load mounted config file: {e}")


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
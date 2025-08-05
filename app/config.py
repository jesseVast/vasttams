"""
Configuration management for TAMS API
"""

import os
import json
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
    debug: bool = True
    
    # VAST Database settings
    vast_endpoint: str = "http://100.100.0.1:9090"
    vast_access_key: str = "SRSPW0DQT9T70Y787U68"
    vast_secret_key: str = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    vast_bucket: str = "tamsdb"
    vast_schema: str = "tams"
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
    
    # S3 settings for flow segment storage
    s3_endpoint_url: str = "http://100.100.0.2:9090"
    s3_access_key_id: str = "SRSPW0DQT9T70Y787U68"
    s3_secret_access_key: str = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    s3_bucket_name: str = "tamsbucket"
    s3_use_ssl: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

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
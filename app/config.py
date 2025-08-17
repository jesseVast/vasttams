"""Configuration management for TAMS application"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os

# Configuration Constants - Easy to adjust for troubleshooting
DEFAULT_PORT = 8000  # Default application port
DEFAULT_HOST = "0.0.0.0"  # Default host binding
DEFAULT_LOG_LEVEL = "INFO"  # Default logging level
DEFAULT_CORS_ORIGINS = ["*"]  # Default CORS origins
DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]  # Default CORS methods
DEFAULT_CORS_HEADERS = ["*"]  # Default CORS headers


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
    vast_endpoints: list[str] = [
        "http://172.200.204.90",
        "http://172.200.204.91", 
        "http://172.200.204.93",
        "http://172.200.204.92"
    ]
    vast_endpoint: str = "http://172.200.204.90"  # Keep for backward compatibility
    
    # Handle .env file override for vast_endpoints
    @property
    def vast_endpoints_resolved(self) -> list[str]:
        """Get vast_endpoints with fallback to vast_endpoint if needed"""
        # If vast_endpoints is loaded from .env as a string, parse it
        if isinstance(self.vast_endpoints, str):
            try:
                import ast
                return ast.literal_eval(self.vast_endpoints)
            except (ValueError, SyntaxError):
                # Fallback to single endpoint
                return [self.vast_endpoint]
        return self.vast_endpoints
    vast_access_key: str = "SRSPW0DQT9T70Y787U68"
    vast_secret_key: str = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    vast_bucket: str = "jthaloor-db"
    vast_schema: str = "tams7"
    
    # Logging settings
    log_level: str = Field(
        default="DEBUG" if os.getenv("ENVIRONMENT") == "development" else "INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s" if os.getenv("ENVIRONMENT") == "production" else "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
        description="Log message format"
    )
    
    # S3 settings for flow segment storage
    s3_endpoint_url: str = "http://172.200.204.90"
    s3_access_key_id: str = "SRSPW0DQT9T70Y787U68"
    s3_secret_access_key: str = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    s3_bucket_name: str = "jthaloor-s3"
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
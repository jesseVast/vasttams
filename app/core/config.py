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
# Removed - replaced with s3_presigned_url_upload_timeout and s3_presigned_url_download_timeout


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
    vast_schema: str = "tams7"
    
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
    s3_region: str = Field(
        default="us-east-1",
        description="S3 region for presigned URL generation (use us-east-1 for custom endpoints)",
        env="S3_REGION"
    )
    
    # Presigned URL configuration - Runtime configurable
    s3_presigned_url_upload_timeout: int = Field(
        default=3600, 
        description="Presigned URL timeout for upload operations in seconds (default: 1 hour)",
        env="S3_PRESIGNED_URL_UPLOAD_TIMEOUT"
    )
    
    s3_presigned_url_download_timeout: int = Field(
        default=3600, 
        description="Presigned URL timeout for download operations in seconds (default: 1 hour)",
        env="S3_PRESIGNED_URL_DOWNLOAD_TIMEOUT"
    )
    
    # Storage backend configuration for get_urls
    default_storage_backend_id: str = Field(
        default="default",
        description="Default storage backend ID for get_urls generation",
        env="DEFAULT_STORAGE_BACKEND_ID"
    )
    
    # TAMS storage path configuration
    tams_storage_path: str = Field(
        default="tams",
        description="Base path for TAMS media storage organization",
        env="TAMS_STORAGE_PATH"
    )
    
    # S3 TAMS root path (legacy support)
    s3_tams_root: str = Field(
        default="/tams",
        description="S3 TAMS root path for legacy compatibility",
        env="S3_TAMS_ROOT"
    )
    
    # get_urls configuration
    get_urls_max_count: int = Field(
        default=5,
        description="Maximum number of get_urls to generate per segment",
        env="GET_URLS_MAX_COUNT"
    )
    
    # Storage API settings
    flow_storage_default_limit: int = Field(
        default=10,
        description="Default limit for flow storage allocation when no limit is specified in the request",
        env="FLOW_STORAGE_DEFAULT_LIMIT"
    )
    
    segment_storage_default_limit: int = Field(
        default=10,
        description="Default limit for segment storage allocation when no limit is specified in the request",
        env="SEGMENT_STORAGE_DEFAULT_LIMIT"
    )
    
    async_deletion_threshold: int = Field(
        default=1000,
        description="Threshold for triggering async deletion workflow (number of segments)",
        env="ASYNC_DELETION_THRESHOLD"
    )
    
    # Table projections settings
    enable_table_projections: bool = Field(
        default=False,
        description="Enable table projections for improved query performance. Creates projections for: source(id), flow(id), segment(id,flow_id,object_id), object(id), flow_object_references(id)",
        env="ENABLE_TABLE_PROJECTIONS"
    )
    
    # TAMS API Compliance settings
    tams_compliance_mode: bool = Field(
        default=True,
        description="Enable strict TAMS API compliance mode",
        env="TAMS_COMPLIANCE_MODE"
    )
    
    tams_validation_level: str = Field(
        default="strict",
        description="TAMS validation level: strict, relaxed, or minimal",
        env="TAMS_VALIDATION_LEVEL"
    )
    
    # TAMS-specific validation settings
    enable_uuid_validation: bool = Field(
        default=True,
        description="Enable strict UUID validation according to TAMS specification",
        env="ENABLE_UUID_VALIDATION"
    )
    
    enable_timestamp_validation: bool = Field(
        default=True,
        description="Enable strict timestamp validation according to TAMS specification",
        env="ENABLE_TIMESTAMP_VALIDATION"
    )
    
    enable_content_format_validation: bool = Field(
        default=True,
        description="Enable strict content format URN validation according to TAMS specification",
        env="ENABLE_CONTENT_FORMAT_VALIDATION"
    )
    
    enable_mime_type_validation: bool = Field(
        default=True,
        description="Enable strict MIME type validation according to TAMS specification",
        env="ENABLE_MIME_TYPE_VALIDATION"
    )
    
    # TAMS error handling settings
    tams_error_reporting: bool = Field(
        default=True,
        description="Enable TAMS-specific error reporting and logging",
        env="TAMS_ERROR_REPORTING"
    )
    
    tams_audit_logging: bool = Field(
        default=True,
        description="Enable TAMS compliance audit logging",
        env="TAMS_AUDIT_LOGGING"
    )
    
    # TAMS performance settings
    tams_cache_enabled: bool = Field(
        default=True,
        description="Enable TAMS-specific caching for improved performance",
        env="TAMS_CACHE_ENABLED"
    )
    
    tams_cache_ttl: int = Field(
        default=300,
        description="TAMS cache TTL in seconds",
        env="TAMS_CACHE_TTL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = "TAMS_"  # Environment variables will be prefixed with TAMS_

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load configuration from mounted file if it exists
        self._load_mounted_config()
        # Validate TAMS-specific settings
        self._validate_tams_settings()
    
    def _validate_tams_settings(self):
        """Validate TAMS-specific configuration settings"""
        if self.tams_validation_level not in ["strict", "relaxed", "minimal"]:
            raise ValueError(f"Invalid TAMS validation level: {self.tams_validation_level}. Must be one of: strict, relaxed, minimal")
        
        if self.tams_cache_ttl < 0:
            raise ValueError("TAMS cache TTL cannot be negative")
        
        if self.tams_cache_ttl > 86400:  # 24 hours
            raise ValueError("TAMS cache TTL cannot exceed 24 hours (86400 seconds)")

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
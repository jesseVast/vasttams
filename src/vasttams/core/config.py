"""Configuration management for TAMS application"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os
import json

# Configuration Constants
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_CORS_ORIGINS = ["*"]
DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
DEFAULT_CORS_HEADERS = ["*"]


class Settings(BaseSettings):
    """Application settings"""
    
    # Configure environment variable prefix for TAMS variables
    model_config = {
        "env_prefix": "TAMS_",  # Environment variables will be prefixed with TAMS_
        "case_sensitive": False
    }
    
    # API settings
    api_title: str = "TAMS API"
    api_version: str = "7.0"
    api_description: str = "Time-addressable Media Store API"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = Field(default=DEFAULT_PORT, description="Application port")
    debug: bool = Field(default=False, description="Enable debug mode (should be False in production)")
    
    # VAST Database settings
    vast_endpoint: str = Field(default="http://localhost:9090",
        description="VAST database endpoint URL")
    vast_access_key: str = Field(default="",
        description="VAST database access key")
    vast_secret_key: str = Field(default="",
        description="VAST database secret key")
    vast_bucket: str = Field(default="tams",
        description="VAST database bucket name")
    vast_schema: str = Field(default="tams7",
        description="VAST database schema name")
    
    # Trino settings for vaststore SQL capabilities
    trino_host: str = Field(default="docker1",
        description="Trino server host")
    trino_port: int = Field(default=8080,
        description="Trino server port")
    trino_user: str = Field(default="admin",
        description="Trino username")
    trino_catalog: str = Field(default="vast",
        description="Trino catalog name")
    
    # VastStore settings
    vaststore_enable_trino: bool = Field(default=True,
        description="Enable Trino integration for vaststore SQL capabilities")
    vaststore_s3_chunk_size: int = Field(default=8 * 1024 * 1024,  # 8MB
        description="S3 multipart upload chunk size in bytes")
    vaststore_s3_max_concurrent_parts: int = Field(default=10,
        description="Maximum concurrent parts for S3 multipart uploads")
    
    # Logging settings
    log_level: str = Field(default="INFO",
        description="Application log level")
    log_format: str = Field(default="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
        description="Log message format")
    
    # S3 settings for flow segment storage
    s3_endpoint_url: str = Field(default="http://localhost:9000",
        description="S3-compatible storage endpoint URL")
    s3_access_key_id: str = Field(default="",
        description="S3 access key ID")
    s3_secret_access_key: str = Field(default="",
        description="S3 secret access key")
    s3_bucket_name: str = Field(default="tams",
        description="S3 bucket name for media storage")
    s3_root_path: Optional[str] = Field(default=None,
        description="S3 key prefix for all objects (e.g., /tams8-dev)")
    s3_use_ssl: bool = False
    s3_region: str = Field(default="us-east-1",
        description="S3 region for presigned URL generation (use us-east-1 for custom endpoints)")
    
    # Presigned URL configuration - Runtime configurable
    s3_presigned_url_upload_timeout: int = Field(default=3600, 
        description="Presigned URL timeout for upload operations in seconds (default: 1 hour)")
    
    s3_presigned_url_download_timeout: int = Field(default=3600, 
        description="Presigned URL timeout for download operations in seconds (default: 1 hour)")
    
    # Storage backend configuration for get_urls
    default_storage_backend_id: str = Field(default="default",
        description="Default storage backend ID for get_urls generation")
    
    # TAMS storage path configuration
    tams_storage_path: str = Field(default="tams",
        description="Base path for TAMS media storage organization")
    
    # S3 TAMS root path (legacy support)
    s3_tams_root: str = Field(default="/tams",
        description="S3 TAMS root path for legacy compatibility")
    
    # get_urls configuration
    get_urls_max_count: int = Field(default=5,
        description="Maximum number of get_urls to generate per segment")
    
    # Storage API settings
    flow_storage_default_limit: int = Field(default=10,
        description="Default limit for flow storage allocation when no limit is specified in the request")
    
    segment_storage_default_limit: int = Field(default=10,
        description="Default limit for segment storage allocation when no limit is specified in the request")
    
    async_deletion_threshold: int = Field(default=1000,
        description="Threshold for triggering async deletion workflow (number of segments)")
    
    # Table projections settings
    enable_table_projections: bool = Field(default=False,
        description="Enable table projections for improved query performance. Creates projections for: source(id), flow(id), segment(id,flow_id,object_id), object(id), flow_object_references(id)")
    
    # TAMS API Compliance settings
    tams_compliance_mode: bool = Field(default=True,
        description="Enable strict TAMS API compliance mode")
    
    tams_validation_level: str = Field(default="strict",
        description="TAMS validation level: strict, relaxed, or minimal")
    
    # TAMS-specific validation settings
    enable_uuid_validation: bool = Field(default=True,
        description="Enable strict UUID validation according to TAMS specification")
    
    enable_timestamp_validation: bool = Field(default=True,
        description="Enable strict timestamp validation according to TAMS specification")
    
    enable_content_format_validation: bool = Field(default=True,
        description="Enable strict content format URN validation according to TAMS specification")
    
    enable_mime_type_validation: bool = Field(default=True,
        description="Enable strict MIME type validation according to TAMS specification")
    
    # TAMS error handling settings
    tams_error_reporting: bool = Field(default=True,
        description="Enable TAMS-specific error reporting and logging")
    
    tams_audit_logging: bool = Field(default=True,
        description="Enable TAMS compliance audit logging")
    
    # TAMS performance settings
    tams_cache_enabled: bool = Field(default=True,
        description="Enable TAMS-specific caching for improved performance")
    
    tams_cache_ttl: int = Field(default=300,
        description="TAMS cache TTL in seconds")
    
    # Note: Environment variables are handled via Config class below
    # The BaseSettings class handles environment variable loading

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
        """Load configuration from mounted config file or local development config"""
        # Check for mounted config first (production)
        config_file_path = "/etc/tams/config.json"
        
        # If mounted config doesn't exist, check for local development config
        if not os.path.exists(config_file_path):
            config_file_path = "config/config.json"
        
        if os.path.exists(config_file_path):
            try:
                with open(config_file_path, 'r') as f:
                    config_data = json.load(f)
                
                # Update settings with config file (takes precedence over defaults)
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                        
            except (json.JSONDecodeError, IOError) as e:
                # Log error but continue with default values
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not load config file {config_file_path}: {e}")


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
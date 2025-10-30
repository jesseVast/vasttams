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
    
    # Telemetry settings
    telemetry_enabled: bool = Field(default=True,
        description="Enable telemetry collection")
    metrics_enabled: bool = Field(default=True,
        description="Enable metrics collection")
    tracing_enabled: bool = Field(default=True,
        description="Enable distributed tracing")
    jaeger_endpoint: Optional[str] = Field(default=None,
        description="Jaeger endpoint for trace export (host:port)")
    otlp_endpoint: Optional[str] = Field(default=None,
        description="OTLP endpoint for trace export (URL)")
    
    # Authentication settings
    secret_key: str = Field(default="your-secret-key-here-change-in-production",
        description="Secret key for JWT token generation")
    algorithm: str = Field(default="HS256",
        description="JWT algorithm for token generation")
    access_token_expire_minutes: int = Field(default=30,
        description="JWT access token expiration time in minutes")
    
    # Webhook settings
    webhook_timeout: int = Field(default=30,
        description="Webhook request timeout in seconds")
    webhook_retry_attempts: int = Field(default=3,
        description="Number of retry attempts for failed webhooks")
    
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
                
                # Load API settings
                if 'api' in config_data:
                    api = config_data['api']
                    if 'title' in api:
                        self.api_title = api['title']
                    if 'version' in api:
                        self.api_version = api['version']
                    if 'description' in api:
                        self.api_description = api['description']
                
                # Load server settings
                if 'server' in config_data:
                    server = config_data['server']
                    if 'host' in server:
                        self.host = server['host']
                    if 'port' in server:
                        self.port = server['port']
                    if 'debug' in server:
                        self.debug = server['debug']
                
                # Load database settings
                if 'database' in config_data:
                    db = config_data['database']
                    if 'vast' in db:
                        vast = db['vast']
                        if 'endpoint' in vast:
                            self.vast_endpoint = vast['endpoint']
                        if 'access_key' in vast:
                            self.vast_access_key = vast['access_key']
                        if 'secret_key' in vast:
                            self.vast_secret_key = vast['secret_key']
                        if 'bucket' in vast:
                            self.vast_bucket = vast['bucket']
                        if 'schema' in vast:
                            self.vast_schema = vast['schema']
                    
                    if 'trino' in db:
                        trino = db['trino']
                        if 'host' in trino:
                            self.trino_host = trino['host']
                        if 'port' in trino:
                            self.trino_port = trino['port']
                        if 'user' in trino:
                            self.trino_user = trino['user']
                        if 'catalog' in trino:
                            self.trino_catalog = trino['catalog']
                        if 'enabled' in trino:
                            self.vaststore_enable_trino = trino['enabled']
                    
                    if 'enable_table_projections' in db:
                        self.enable_table_projections = db['enable_table_projections']
                
                # Load logging settings
                if 'logging' in config_data:
                    logging_cfg = config_data['logging']
                    if 'level' in logging_cfg:
                        self.log_level = logging_cfg['level']
                    if 'format' in logging_cfg:
                        self.log_format = logging_cfg['format']
                
                # Load storage settings
                if 'storage' in config_data:
                    storage = config_data['storage']
                    if 'default_backend_id' in storage:
                        self.default_storage_backend_id = storage['default_backend_id']
                    if 'tams_storage_path' in storage:
                        self.tams_storage_path = storage['tams_storage_path']
                    if 'tams_root' in storage:
                        self.s3_tams_root = storage['tams_root']
                    if 'presigned_url' in storage:
                        presigned = storage['presigned_url']
                        if 'upload_timeout' in presigned:
                            self.s3_presigned_url_upload_timeout = presigned['upload_timeout']
                        if 'download_timeout' in presigned:
                            self.s3_presigned_url_download_timeout = presigned['download_timeout']
                    if 'get_urls_max_count' in storage:
                        self.get_urls_max_count = storage['get_urls_max_count']
                    if 'flow_storage_default_limit' in storage:
                        self.flow_storage_default_limit = storage['flow_storage_default_limit']
                    if 'segment_storage_default_limit' in storage:
                        self.segment_storage_default_limit = storage['segment_storage_default_limit']
                    if 'async_deletion_threshold' in storage:
                        self.async_deletion_threshold = storage['async_deletion_threshold']
                
                # Load storage backends and extract default backend for S3 client config
                if 'storage_backends' in config_data and isinstance(config_data['storage_backends'], list):
                    self._storage_backends_config = config_data['storage_backends']
                    backends = config_data['storage_backends']
                    if backends:
                        # Use the default backend for S3 client initialization
                        default_backend = next((b for b in backends if b.get('default_storage', False)), backends[0])
                        if 'endpoint_url' in default_backend:
                            self.s3_endpoint_url = default_backend['endpoint_url']
                        if 'access_key' in default_backend:
                            self.s3_access_key_id = default_backend['access_key']
                        if 'secret_key' in default_backend:
                            self.s3_secret_access_key = default_backend['secret_key']
                        if 'bucket_name' in default_backend:
                            self.s3_bucket_name = default_backend['bucket_name']
                        if 'root_path' in default_backend:
                            self.s3_root_path = default_backend['root_path']
                        if 'use_ssl' in default_backend:
                            self.s3_use_ssl = default_backend['use_ssl']
                        if 'region' in default_backend:
                            self.s3_region = default_backend['region']
                        if 'chunk_size' in default_backend:
                            self.vaststore_s3_chunk_size = default_backend['chunk_size']
                        if 'max_concurrent_parts' in default_backend:
                            self.vaststore_s3_max_concurrent_parts = default_backend['max_concurrent_parts']
                
                # Load TAMS compliance settings
                if 'tams_compliance' in config_data:
                    compliance = config_data['tams_compliance']
                    if 'enabled' in compliance:
                        self.tams_compliance_mode = compliance['enabled']
                    if 'validation_level' in compliance:
                        self.tams_validation_level = compliance['validation_level']
                    if 'uuid_validation' in compliance:
                        self.enable_uuid_validation = compliance['uuid_validation']
                    if 'timestamp_validation' in compliance:
                        self.enable_timestamp_validation = compliance['timestamp_validation']
                    if 'content_format_validation' in compliance:
                        self.enable_content_format_validation = compliance['content_format_validation']
                    if 'mime_type_validation' in compliance:
                        self.enable_mime_type_validation = compliance['mime_type_validation']
                    if 'error_reporting' in compliance:
                        self.tams_error_reporting = compliance['error_reporting']
                    if 'audit_logging' in compliance:
                        self.tams_audit_logging = compliance['audit_logging']
                    if 'cache_enabled' in compliance:
                        self.tams_cache_enabled = compliance['cache_enabled']
                    if 'cache_ttl' in compliance:
                        self.tams_cache_ttl = compliance['cache_ttl']
                
                # Load telemetry settings
                if 'telemetry' in config_data:
                    telemetry = config_data['telemetry']
                    if 'enabled' in telemetry:
                        self.telemetry_enabled = telemetry['enabled']
                    if 'metrics_enabled' in telemetry:
                        self.metrics_enabled = telemetry['metrics_enabled']
                    if 'tracing_enabled' in telemetry:
                        self.tracing_enabled = telemetry['tracing_enabled']
                    if 'jaeger_endpoint' in telemetry:
                        self.jaeger_endpoint = telemetry['jaeger_endpoint']
                    if 'otlp_endpoint' in telemetry:
                        self.otlp_endpoint = telemetry['otlp_endpoint']
                
                # Load authentication settings
                if 'authentication' in config_data:
                    auth = config_data['authentication']
                    if 'secret_key' in auth:
                        self.secret_key = auth['secret_key']
                    if 'algorithm' in auth:
                        self.algorithm = auth['algorithm']
                    if 'access_token_expire_minutes' in auth:
                        self.access_token_expire_minutes = auth['access_token_expire_minutes']
                
                # Load webhook settings
                if 'webhooks' in config_data:
                    webhooks = config_data['webhooks']
                    if 'timeout' in webhooks:
                        self.webhook_timeout = webhooks['timeout']
                    if 'retry_attempts' in webhooks:
                        self.webhook_retry_attempts = webhooks['retry_attempts']
                        
            except (json.JSONDecodeError, IOError) as e:
                # Log error but continue with default values
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not load config file {config_file_path}: {e}")
    
    @property
    def storage_backends_config(self) -> Optional[List[dict]]:
        """Get storage backends configuration array"""
        return getattr(self, '_storage_backends_config', None)


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
"""
TAMS Ingest Client Configuration

Configuration management for the TAMS Ingest Client module.
"""

import os
import toml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from .constants import (
    DEFAULT_TAMS_BASE_URL, DEFAULT_TAMS_TIMEOUT, DEFAULT_TAMS_RETRY_ATTEMPTS,
    DEFAULT_TAMS_VERIFY_SSL, DEFAULT_S3_BUCKET, DEFAULT_S3_PREFIX, DEFAULT_S3_REGION,
    DEFAULT_CHUNK_DURATION, DEFAULT_SEGMENT_OVERLAP, DEFAULT_VIDEO_CODEC, DEFAULT_AUDIO_CODEC
)


class TAMSApiConfig(BaseModel):
    """TAMS API configuration."""
    base_url: str = Field(default=DEFAULT_TAMS_BASE_URL, description="TAMS API base URL")
    api_key: Optional[str] = Field(default=None, description="TAMS API key")
    timeout: int = Field(default=DEFAULT_TAMS_TIMEOUT, description="API request timeout in seconds")
    retry_attempts: int = Field(default=DEFAULT_TAMS_RETRY_ATTEMPTS, description="Number of retry attempts")
    verify_ssl: bool = Field(default=DEFAULT_TAMS_VERIFY_SSL, description="Verify SSL certificates")


class S3Config(BaseModel):
    """S3 configuration for media uploads."""
    bucket: str = Field(default=DEFAULT_S3_BUCKET, description="S3 bucket name")
    prefix: str = Field(default=DEFAULT_S3_PREFIX, description="S3 key prefix")
    region: str = Field(default=DEFAULT_S3_REGION, description="S3 region")
    endpoint_url: Optional[str] = Field(default=None, description="S3 endpoint URL (for MinIO, etc.)")
    access_key: Optional[str] = Field(default=None, description="S3 access key")
    secret_key: Optional[str] = Field(default=None, description="S3 secret key")
    use_ssl: bool = Field(default=True, description="Use SSL for S3 connections")


class VideoProcessingConfig(BaseModel):
    """Video processing configuration."""
    chunk_duration: int = Field(default=DEFAULT_CHUNK_DURATION, description="Chunk duration in seconds")
    segment_overlap: int = Field(default=DEFAULT_SEGMENT_OVERLAP, description="Segment overlap in seconds")
    video_codec: str = Field(default=DEFAULT_VIDEO_CODEC, description="Default video codec")
    audio_codec: str = Field(default=DEFAULT_AUDIO_CODEC, description="Default audio codec")
    
    # Auto-detection settings
    auto_detect_codec: bool = Field(default=True, description="Auto-detect codec from video")
    auto_detect_resolution: bool = Field(default=True, description="Auto-detect resolution from video")
    auto_detect_framerate: bool = Field(default=True, description="Auto-detect framerate from video")
    auto_detect_bitrate: bool = Field(default=True, description="Auto-detect bitrate from video")
    
    # Processing options
    enable_thumbnails: bool = Field(default=False, description="Generate thumbnails for segments")
    thumbnail_interval: int = Field(default=10, description="Thumbnail generation interval in seconds")
    enable_metadata_extraction: bool = Field(default=True, description="Extract metadata from video")


class TAMSIngestConfig(BaseModel):
    """Main TAMS ingest client configuration."""
    # Core settings
    enable_logging: bool = Field(default=True, description="Enable detailed logging")
    log_level: str = Field(default="INFO", description="Logging level")
    max_concurrent_uploads: int = Field(default=5, description="Maximum concurrent S3 uploads")
    
    # Module configurations
    tams_api: TAMSApiConfig = Field(default_factory=TAMSApiConfig)
    s3: S3Config = Field(default_factory=S3Config)
    video_processing: VideoProcessingConfig = Field(default_factory=VideoProcessingConfig)
    
    # Default settings
    auto_create_source: bool = Field(default=True, description="Auto-create source if not exists")
    auto_create_flow: bool = Field(default=True, description="Auto-create flow if not exists")
    upload_to_s3: bool = Field(default=True, description="Upload segments to S3")
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @classmethod
    def from_toml(cls, config_path: str) -> 'TAMSIngestConfig':
        """Load configuration from TOML file."""
        try:
            with open(config_path, 'r') as f:
                config_data = toml.load(f)
            
            # Handle nested configurations
            if 'tams_ingest' in config_data:
                config_data = config_data['tams_ingest']
            
            return cls(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")
    
    @classmethod
    def from_env(cls) -> 'TAMSIngestConfig':
        """Load configuration from environment variables."""
        env_mapping = {
            'TAMS_BASE_URL': 'tams_api.base_url',
            'TAMS_API_KEY': 'tams_api.api_key',
            'TAMS_TIMEOUT': 'tams_api.timeout',
            'TAMS_RETRY_ATTEMPTS': 'tams_api.retry_attempts',
            'TAMS_VERIFY_SSL': 'tams_api.verify_ssl',
            'S3_BUCKET': 's3.bucket',
            'S3_PREFIX': 's3.prefix',
            'S3_REGION': 's3.region',
            'S3_ENDPOINT_URL': 's3.endpoint_url',
            'S3_ACCESS_KEY': 's3.access_key',
            'S3_SECRET_KEY': 's3.secret_key',
            'S3_USE_SSL': 's3.use_ssl',
            'CHUNK_DURATION': 'video_processing.chunk_duration',
            'SEGMENT_OVERLAP': 'video_processing.segment_overlap',
            'VIDEO_CODEC': 'video_processing.video_codec',
            'AUDIO_CODEC': 'video_processing.audio_codec',
            'LOG_LEVEL': 'log_level',
            'MAX_CONCURRENT_UPLOADS': 'max_concurrent_uploads',
            'AUTO_CREATE_SOURCE': 'auto_create_source',
            'AUTO_CREATE_FLOW': 'auto_create_flow',
            'UPLOAD_TO_S3': 'upload_to_s3'
        }
        
        config_data = {}
        
        # Load environment variables
        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Handle nested paths
                keys = config_path.split('.')
                current = config_data
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert value to appropriate type
                if key in ['timeout', 'retry_attempts', 'chunk_duration', 'segment_overlap', 'max_concurrent_uploads', 'thumbnail_interval']:
                    current[keys[-1]] = int(value)
                elif key in ['verify_ssl', 'use_ssl', 'auto_detect_codec', 'auto_detect_resolution', 'auto_detect_framerate', 'auto_detect_bitrate', 'enable_thumbnails', 'enable_metadata_extraction', 'auto_create_source', 'auto_create_flow', 'upload_to_s3', 'enable_logging']:
                    current[keys[-1]] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    current[keys[-1]] = value
        
        return cls(**config_data)
    
    def to_toml(self, config_path: str) -> None:
        """Save configuration to TOML file."""
        config_dict = self.model_dump()
        
        # Wrap in 'tams_ingest' section
        toml_data = {'tams_ingest': config_dict}
        
        with open(config_path, 'w') as f:
            toml.dump(toml_data, f)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    def get_s3_config(self) -> Dict[str, Any]:
        """Get S3 configuration as dictionary."""
        return self.s3.model_dump()
    
    def get_tams_api_config(self) -> Dict[str, Any]:
        """Get TAMS API configuration as dictionary."""
        return self.tams_api.model_dump()












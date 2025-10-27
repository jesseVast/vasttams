"""
Dependencies module for TAMS API.
Contains dependency injection functions to avoid circular imports.
"""
from fastapi import HTTPException
from vastdbmanager import VastDBManager
from vasts3 import S3Client, S3Config
from .config import get_settings

# Global storage instances
vast_db = None
s3_client = None

def get_vast_db() -> VastDBManager:
    """Get the global VastDBManager instance."""
    global vast_db
    if vast_db is None:
        settings = get_settings()
        vast_db = VastDBManager(
            endpoints=[settings.vast_endpoint],
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema,
            enable_trino=settings.vaststore_enable_trino,
            trino_host=settings.trino_host,
            trino_port=settings.trino_port,
            trino_user=settings.trino_user,
            trino_catalog=settings.trino_catalog
        )
    return vast_db

def get_s3_client() -> S3Client:
    """Get the global S3Client instance."""
    global s3_client
    if s3_client is None:
        settings = get_settings()
        config = S3Config(
            endpoint_url=settings.s3_endpoint_url,
            bucket_name=settings.s3_bucket_name,
            access_key=settings.s3_access_key_id,
            secret_key=settings.s3_secret_access_key,
            region=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            chunk_size=settings.vaststore_s3_chunk_size,
            max_concurrent_parts=settings.vaststore_s3_max_concurrent_parts
        )
        s3_client = S3Client(config)
    return s3_client

# Legacy compatibility (will be removed in Phase 4)
def get_vast_store():
    """Legacy compatibility - will be removed."""
    raise HTTPException(status_code=500, detail="VASTStore deprecated - use get_vast_db() and get_s3_client()")

def set_vast_store(store):
    """Legacy compatibility - will be removed."""
    raise HTTPException(status_code=500, detail="VASTStore deprecated - use get_vast_db() and get_s3_client()") 
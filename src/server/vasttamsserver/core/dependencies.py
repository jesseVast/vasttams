"""
Dependencies module for TAMS API.
Contains dependency injection functions to avoid circular imports.
"""
from fastapi import HTTPException
from vastdbmanager import VastDBManager
from vastdbmanager.model import VastDBManagerConfig
from vastdbmanager.core import VastDBConnectionConfig
from vastdbmanager.trino import TrinoConfig
from vasts3 import S3Client, S3Config
from .config import get_settings
from .cache import CacheService

# Global storage instances
vast_db = None
s3_client = None
cache_service = None

def get_vast_db() -> VastDBManager:
    """Get the global VastDBManager instance."""
    global vast_db
    if vast_db is None:
        settings = get_settings()
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Initializing VastDBManager with endpoint: {settings.vast_endpoint}")
        
        # Build VastDBConnectionConfig
        # Note: vector_support is True if vector_endpoint is configured (indicates vector operations are available)
        vector_support = bool(settings.vast_vector_endpoint)
        vastdb_config = VastDBConnectionConfig(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema,
            vector_support=vector_support
        )
        
        # Build TrinoConfig if Trino is enabled
        trino_config = None
        if settings.vaststore_enable_trino:
            trino_config = TrinoConfig(
                host=settings.trino_host,
                port=settings.trino_port,
                user=settings.trino_user,
                catalog=settings.trino_catalog,
                bucket=settings.vast_bucket,
                schema=settings.vast_schema
            )
            logger.debug(f"Trino configured: {settings.trino_host}:{settings.trino_port}/{settings.trino_catalog}")
        
        # Log vector endpoint if configured
        if settings.vast_vector_endpoint:
            logger.debug(f"Vector support enabled (endpoint: {settings.vast_vector_endpoint})")
        
        # Build VastDBManagerConfig
        manager_config = VastDBManagerConfig(
            vastdb_config=vastdb_config,
            trino_config=trino_config,
            enable_trino=settings.vaststore_enable_trino,
            auto_connect=True
        )
        
        vast_db = VastDBManager(manager_config)
    return vast_db

def get_s3_client() -> S3Client:
    """Get the global S3Client instance."""
    global s3_client
    if s3_client is None:
        settings = get_settings()
        config_params = {
            "endpoint_url": settings.s3_endpoint_url,
            "bucket_name": settings.s3_bucket_name,
            "access_key": settings.s3_access_key_id,
            "secret_key": settings.s3_secret_access_key,
            "region": settings.s3_region,
            "use_ssl": settings.s3_use_ssl,
            "chunk_size": settings.vaststore_s3_chunk_size,
            "max_concurrent_parts": settings.vaststore_s3_max_concurrent_parts
        }
        # Add key_prefix if s3_root_path is configured and S3Config supports it
        if hasattr(settings, 's3_root_path') and settings.s3_root_path:
            try:
                # Normalize key_prefix: strip leading/trailing slashes to avoid double slashes
                # The S3 client will handle adding slashes as needed
                key_prefix = settings.s3_root_path.strip('/')
                config_params["key_prefix"] = key_prefix
            except TypeError:
                # S3Config doesn't support key_prefix parameter
                pass
        config = S3Config(**config_params)
        s3_client = S3Client(config)
    return s3_client

# Legacy compatibility (will be removed in Phase 4)
def get_vast_store():
    """Legacy compatibility - will be removed."""
    raise HTTPException(status_code=500, detail="VASTStore deprecated - use get_vast_db() and get_s3_client()")

def set_vast_store(store):
    """Legacy compatibility - will be removed."""
    raise HTTPException(status_code=500, detail="VASTStore deprecated - use get_vast_db() and get_s3_client()")

def get_cache_service() -> CacheService:
    """Get the global CacheService instance."""
    global cache_service
    if cache_service is None:
        cache_service = CacheService()
    return cache_service 
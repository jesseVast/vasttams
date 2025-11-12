"""
GetUrl Factory

This module provides a factory for creating GetUrl objects for TAMS flow segments.
Separates URL generation concerns from segment storage operations.
Supports multi-threaded batch processing for improved performance.
"""

import logging
import uuid
import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import GetUrl
from ..common.storage.timestamp_utils import get_tams_timestamp

logger = logging.getLogger(__name__)


class GetUrlFactory:
    """Factory for creating GetUrl objects for TAMS flow segments with multi-threaded support"""
    
    def __init__(self, vast_db, s3_client, settings, max_workers: Optional[int] = None):
        """
        Initialize the GetUrl factory
        
        Args:
            vast_db: VAST database manager
            s3_client: S3 client for generating presigned URLs
            settings: Application settings
            max_workers: Maximum number of worker threads for parallel processing (default: 10)
        """
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = settings
        self.max_workers = max_workers or 10
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def __del__(self):
        """Cleanup thread pool executor on destruction"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
    
    async def create_get_urls_batch(
        self, 
        object_ids: List[str], 
        batch_size: int = 10
    ) -> Dict[str, Optional[List[GetUrl]]]:
        """
        Create GetUrl objects for multiple object_ids in parallel batches
        
        Args:
            object_ids: List of object identifiers
            batch_size: Number of objects to process in each batch (default: 10)
            
        Returns:
            Dictionary mapping object_id to List[GetUrl] or None if generation failed
        """
        results = {}
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(object_ids), batch_size):
            batch = object_ids[i:i + batch_size]
            
            # Create tasks for this batch
            tasks = [self.create_get_urls(obj_id) for obj_id in batch]
            
            # Execute batch in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Map results back to object_ids
            for obj_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to generate get_urls for object_id {obj_id}: {result}", exc_info=True)
                    results[obj_id] = None
                else:
                    results[obj_id] = result
        
        return results
    
    async def create_get_urls(self, object_id: str) -> Optional[List[GetUrl]]:
        """
        Create GetUrl objects for a given object_id
        
        Args:
            object_id: The media object identifier
            
        Returns:
            List of GetUrl objects, or None if generation failed
        """
        try:
            # Get the object to find its storage path and storage_id
            obj_dict = await self._get_object(object_id)
            
            # Extract storage metadata
            storage_path, storage_id, content_type = self._extract_storage_metadata(obj_dict, object_id)
            
            # Validate we have a storage path
            if not storage_path:
                if not obj_dict:
                    logger.error(
                        f"Object {object_id} not found in database when generating get_urls. "
                        f"This indicates orphaned segment references. Returning None for get_urls."
                    )
                    self._record_metrics("object_not_found")
                else:
                    logger.error(
                        f"Object {object_id} exists but has no storage_path in metadata and no created timestamp. "
                        f"Cannot reconstruct storage path. Returning None for get_urls."
                    )
                    self._record_metrics("missing_metadata")
                return None
            
            # Get storage backend information
            backend_info, relative_storage_path = await self._get_backend_info(storage_id, storage_path)
            
            # Generate presigned URL
            presigned_url = await self._generate_presigned_url(
                key=relative_storage_path,
                operation="get_object",
                expiration=self.settings.s3_presigned_url_download_timeout if hasattr(self.settings, 's3_presigned_url_download_timeout') else 3600,
                storage_backend=backend_info,
                content_type=content_type
            )
            
            if not presigned_url:
                return None
            
            # Resolve storage_id if not available
            if not storage_id:
                storage_id = await self._resolve_storage_id()
            
            # Create and return GetUrl object
            return [self._create_get_url_object(
                url=presigned_url,
                storage_id=storage_id,
                provider=self.settings.s3_provider if hasattr(self.settings, 's3_provider') else "aws",
                store_product=self.settings.s3_store_product if hasattr(self.settings, 's3_store_product') else "s3"
            )]
            
        except Exception as e:
            logger.error(f"Failed to generate get_urls for object {object_id}: {e}", exc_info=True)
            return None
    
    async def _get_object(self, object_id: str) -> Optional[Dict[str, Any]]:
        """Get object from database"""
        try:
            result = self.vast_db.query("objects").select("*").where(f"id = '{object_id}'").execute()
            
            # Handle VAST query result format
            obj_data = None
            if isinstance(result, dict) and 'data' in result and isinstance(result['data'], dict):
                # VAST tabular format: columns dict -> reconstruct first row
                columns = result['data']
                if not columns:
                    return None
                # Determine row count
                try:
                    row_count = len(next(iter(columns.values())))
                except StopIteration:
                    row_count = 0
                if row_count == 0:
                    return None
                obj_data = {}
                for col, values in columns.items():
                    if col != '$row_id':  # Skip internal row IDs
                        try:
                            obj_data[col] = values[0] if isinstance(values, list) and values else values
                        except Exception:
                            obj_data[col] = None
            elif isinstance(result, list) and result:
                first = result[0]
                obj_data = dict(first) if isinstance(first, dict) else first
            else:
                return None
            
            if not obj_data:
                return None
            
            # Parse metadata JSON string if present
            if 'metadata' in obj_data and isinstance(obj_data['metadata'], str):
                try:
                    import json
                    obj_data['metadata'] = json.loads(obj_data['metadata'])
                except (json.JSONDecodeError, TypeError):
                    obj_data['metadata'] = None
            
            return obj_data
        except Exception as e:
            logger.error("Failed to get object %s: %s", object_id, e, exc_info=True)
            return None
    
    def _extract_storage_metadata(self, obj_dict: Optional[Dict[str, Any]], object_id: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract storage path, storage_id, and content_type from object metadata
        
        Returns:
            Tuple of (storage_path, storage_id, content_type)
        """
        storage_path = None
        storage_id = None
        content_type = None
        
        if obj_dict:
            # Handle both Object model (with _internal_metadata) and raw dict
            metadata = None
            if hasattr(obj_dict, '_internal_metadata') and not isinstance(obj_dict, dict):
                metadata = obj_dict._internal_metadata
            elif isinstance(obj_dict, dict):
                metadata_raw = obj_dict.get('metadata', {})
                if isinstance(metadata_raw, str):
                    import json
                    try:
                        metadata = json.loads(metadata_raw)
                    except:
                        metadata = {}
                elif isinstance(metadata_raw, dict):
                    metadata = metadata_raw
            
            if metadata and isinstance(metadata, dict):
                storage_path = metadata.get('storage_path')
                storage_id = metadata.get('storage_id')
                content_type = metadata.get('content_type')
            
            # If no storage path in metadata, reconstruct from created timestamp
            if not storage_path:
                created = obj_dict.get('created') if isinstance(obj_dict, dict) else getattr(obj_dict, 'created', None)
                if created:
                    # Parse created timestamp if it's a string
                    if isinstance(created, str):
                        try:
                            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        except:
                            dt = get_tams_timestamp()
                    else:
                        dt = created if hasattr(created, 'year') else get_tams_timestamp()
                    
                    year = str(dt.year)
                    month = f"{dt.month:02d}"
                    date = f"{dt.day:02d}"
                    tams_path = self.settings.tams_storage_path.strip('/')
                    relative_path = f"{tams_path}/{year}/{month}/{date}/{object_id}"
                    
                    # Include root_path if storage_id is available
                    if storage_id:
                        try:
                            from ..storagebackends.service import StorageBackendService
                            backend_service = StorageBackendService(self.vast_db, self.s3_client)
                            # Note: This is async but we're in a sync context - need to handle this
                            # For now, we'll reconstruct without root_path if async is needed
                            # This is a limitation that should be addressed
                            storage_path = relative_path
                        except Exception as e:
                            logger.warning(f"Failed to load backend {storage_id} for path reconstruction: {e}")
                            storage_path = relative_path
                    else:
                        storage_path = relative_path
        
        return storage_path, storage_id, content_type
    
    async def _get_backend_info(self, storage_id: Optional[str], storage_path: str) -> tuple[Optional[Dict[str, Any]], str]:
        """
        Get storage backend information and calculate relative storage path
        
        If storage_path doesn't include root_path, try to prepend it from backend.
        
        Returns:
            Tuple of (backend_info dict, relative_storage_path for S3 key)
        """
        backend_info = None
        relative_storage_path = storage_path
        
        if storage_id:
            try:
                from ..storagebackends.service import StorageBackendService
                backend_service = StorageBackendService(self.vast_db, self.s3_client)
                backend = await backend_service.get_storage_backend(storage_id)
                if backend:
                    backend_info = backend.model_dump()
                    backend_root_path = backend.root_path
                    if backend_root_path:
                        backend_root_path = backend_root_path.strip('/')
                        # If storage_path already includes root_path, strip it for S3 key
                        if storage_path.startswith(backend_root_path + '/'):
                            relative_storage_path = storage_path[len(backend_root_path) + 1:]
                        elif storage_path == backend_root_path:
                            relative_storage_path = ""
                        # If storage_path doesn't include root_path, it's already relative
                        # (This happens when path was reconstructed from timestamp)
            except Exception as e:
                logger.warning(f"Failed to load storage backend {storage_id}: {e}")
        
        return backend_info, relative_storage_path
    
    async def _generate_presigned_url(
        self, 
        key: str, 
        operation: str, 
        expiration: int = 3600, 
        storage_backend: Optional[Dict[str, Any]] = None, 
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate presigned URL; prefer backend-specific endpoint/credentials if provided.
        Uses thread pool executor for blocking S3 operations.
        """
        try:
            import inspect
            http_method = 'GET' if operation.lower() in ('get', 'get_object') else 'PUT'
            final_content_type = content_type or 'application/octet-stream'
            
            # Only use storage_backend if it has valid credentials
            access_key = storage_backend.get('access_key') if storage_backend else None
            secret_key = storage_backend.get('secret_key') if storage_backend else None
            has_valid_credentials = (
                access_key and secret_key and 
                isinstance(access_key, str) and isinstance(secret_key, str) and
                access_key.strip() and secret_key.strip()
            )
            
            if storage_backend and has_valid_credentials:
                from vasts3 import S3Client, S3Config
                
                backend_root_path = storage_backend.get('root_path') or getattr(self.settings, 's3_root_path', None)
                key_prefix = backend_root_path.strip('/') if backend_root_path else None
                
                cfg = S3Config(
                    endpoint_url=storage_backend.get('endpoint_url') or self.settings.s3_endpoint_url or "",
                    bucket_name=storage_backend.get('bucket_name') or self.settings.s3_bucket_name,
                    access_key=access_key,
                    secret_key=secret_key,
                    region=storage_backend.get('region') or self.settings.s3_region,
                    use_ssl=bool(storage_backend.get('use_ssl') if storage_backend.get('use_ssl') is not None else self.settings.s3_use_ssl),
                    chunk_size=self.settings.vaststore_s3_chunk_size,
                    max_concurrent_parts=self.settings.vaststore_s3_max_concurrent_parts,
                    key_prefix=key_prefix or "",
                )
                tmp_client = S3Client(cfg)
                sig = inspect.signature(tmp_client.generate_presigned_url)
                supported = set(sig.parameters.keys())
                candidate_kwargs = {
                    'key': key,
                    'operation': operation,
                    'expires_in': expiration,
                    'expiration': expiration,
                    'method': http_method,
                    'http_method': http_method,
                    'content_type': final_content_type if http_method == 'PUT' else None,
                }
                candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
                kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
                # Use thread pool executor for blocking S3 operations
                # Use functools.partial to bind kwargs since run_in_executor doesn't accept **kwargs
                loop = asyncio.get_event_loop()
                bound_func = functools.partial(tmp_client.generate_presigned_url, **kwargs)
                return await loop.run_in_executor(self._executor, bound_func)
            
            # Fallback to default client
            sig = inspect.signature(self.s3_client.generate_presigned_url)
            supported = set(sig.parameters.keys())
            candidate_kwargs = {
                'key': key,
                'operation': operation,
                'expires_in': expiration,
                'expiration': expiration,
                'method': http_method,
                'http_method': http_method,
                'content_type': final_content_type if http_method == 'PUT' else None,
            }
            candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
            kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
            # Use thread pool executor for blocking S3 operations
            # Use functools.partial to bind kwargs since run_in_executor doesn't accept **kwargs
            loop = asyncio.get_event_loop()
            bound_func = functools.partial(self.s3_client.generate_presigned_url, **kwargs)
            return await loop.run_in_executor(self._executor, bound_func)
        except Exception as e:
            logger.error("Failed to generate presigned URL: %s", e, exc_info=True)
            return None
    
    async def _resolve_storage_id(self) -> str:
        """Resolve storage_id from default backend or generate UUID"""
        try:
            from ..storagebackends.service import StorageBackendService
            backend_service = StorageBackendService(self.vast_db, self.s3_client)
            backends = await backend_service.get_storage_backends()
            default_backend = next((b for b in backends if b.default_storage), None)
            if default_backend:
                logger.debug(f"Using default storage backend for get_urls: {default_backend.id}")
                return default_backend.id
        except Exception as e:
            logger.warning(f"Failed to get default storage backend: {e}")
        
        # Generate a valid TAMS UUID as last resort
        storage_id = str(uuid.uuid4())
        logger.warning(f"No storage_id found, generated UUID: {storage_id}")
        return storage_id
    
    def _create_get_url_object(
        self, 
        url: str, 
        storage_id: str, 
        provider: str, 
        store_product: str
    ) -> GetUrl:
        """Create a GetUrl object with TAMS-compliant fields"""
        return GetUrl(
            url=url,
            storage_id=storage_id,
            presigned=True,
            controlled=True,
            store_type="http_object_store",
            provider=provider,
            store_product=store_product,
            region="",  # Optional but may be required by model
            availability_zone=None,  # Optional
            label=None  # Optional
        )
    
    def _record_metrics(self, reason: str):
        """Record metrics for object fetch failures"""
        try:
            from ..core.telemetry import metrics
            metrics.object_fetch_failures_total.labels(reason=reason).inc()
        except Exception:
            pass  # Don't fail if metrics unavailable


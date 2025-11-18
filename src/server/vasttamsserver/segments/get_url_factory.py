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
            max_workers: Maximum number of worker threads for parallel processing (default: 50)
        """
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = settings
        self.max_workers = max_workers or 50  # Increased from 10 to 50 for better parallelism
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        # Cache for storage backends to avoid repeated lookups
        self._backend_cache: Dict[str, Dict[str, Any]] = {}
        self._backend_cache_ttl = 300  # 5 minutes TTL
        # Cache for the full list of storage backends (to avoid repeated SELECT * queries)
        self._all_backends_cache: Optional[List[Dict[str, Any]]] = None
        self._all_backends_cache_time: Optional[float] = None
    
    def __del__(self):
        """Cleanup thread pool executor on destruction"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
    
    async def create_get_urls_batch(
        self, 
        object_ids: List[str], 
        batch_size: int = 100
    ) -> Dict[str, Optional[List[GetUrl]]]:
        """
        Create GetUrl objects for multiple object_ids in parallel batches
        
        Optimized version that:
        - Fetches all objects in a single database query (batch query)
        - Processes batches in parallel (not sequentially)
        - Uses cached storage backends
        
        Args:
            object_ids: List of object identifiers
            batch_size: Number of objects to process in each parallel batch (default: 100)
            
        Returns:
            Dictionary mapping object_id to List[GetUrl] or None if generation failed
        """
        if not object_ids:
            return {}
        
        # Fetch ALL objects in a single database query (major optimization)
        objects_dict = await self._get_objects_batch(object_ids)
        logger.debug(f"Fetched {len(objects_dict)} objects out of {len(object_ids)} requested in batch query")
        
        # Create batches for parallel processing
        batches = [object_ids[i:i + batch_size] for i in range(0, len(object_ids), batch_size)]
        logger.debug(f"Processing {len(batches)} batches of up to {batch_size} objects each")
        
        # Process ALL batches in parallel (not sequentially)
        batch_tasks = [self._process_batch_with_cache(batch, objects_dict) for batch in batches]
        batch_results_list = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Merge results from all batches
        results = {}
        for i, batch_results in enumerate(batch_results_list):
            if isinstance(batch_results, Exception):
                logger.error(f"Batch {i+1} failed: {batch_results}", exc_info=True)
                # Mark all objects in this batch as failed
                batch_start = i * batch_size
                batch_end = min(batch_start + batch_size, len(object_ids))
                for obj_id in object_ids[batch_start:batch_end]:
                    results[obj_id] = None
            else:
                results.update(batch_results)
        
        return results
    
    async def _process_batch_with_cache(
        self, 
        batch: List[str], 
        objects_dict: Dict[str, Optional[Dict[str, Any]]]
    ) -> Dict[str, Optional[List[GetUrl]]]:
        """Process a single batch using cached object data"""
        tasks = [
            self._create_get_urls_cached(obj_id, objects_dict.get(obj_id)) 
            for obj_id in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for obj_id, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to generate get_urls for object_id {obj_id}: {result}", exc_info=True)
                results[obj_id] = None
            else:
                results[obj_id] = result
        
        return results
    
    async def _create_get_urls_cached(
        self, 
        object_id: str, 
        obj_dict: Optional[Dict[str, Any]]
    ) -> Optional[List[GetUrl]]:
        """Create get_urls using pre-fetched object data (avoids database query)"""
        try:
            # If object wasn't found in batch query, try individual query as fallback
            if not obj_dict:
                obj_dict = await self._get_object(object_id)
                if not obj_dict:
                    logger.warning(f"Object {object_id} not found in database")
                    return None
            
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
            
            # Get storage backend information (with caching)
            backend_info, relative_storage_path = await self._get_backend_info_cached(storage_id, storage_path)

            # Log path information for debugging
            backend_root_path = backend_info.get('root_path') if backend_info else None
            backend_root_path_stripped = backend_root_path.strip('/') if backend_root_path else ""
            bucket_name = backend_info.get('bucket_name') if backend_info else None
            logger.debug(
                f"[_create_get_urls_cached] Object {object_id}: "
                f"storage_path={storage_path}, relative_storage_path={relative_storage_path}, "
                f"backend_root_path={backend_root_path} (stripped: '{backend_root_path_stripped}'), "
                f"bucket_name={bucket_name}, storage_id={storage_id}"
            )

            # Check cache for presigned URL first (using object_id as key)
            cache_key = f"presigned_url:{object_id}"
            presigned_url = None

            try:
                from ..core.dependencies import get_cache_service
                cache_service = get_cache_service()
                cached_url = await cache_service.get(cache_key)
                if cached_url:
                    logger.debug(f"[_create_get_urls_cached] Cache hit for presigned URL: {object_id}")
                    presigned_url = cached_url
            except Exception as e:
                logger.debug(f"Failed to check cache for presigned URL {object_id}: {e}")

            # Generate presigned URL if not cached
            if not presigned_url:
                logger.debug(
                    f"[_create_get_urls_cached] Generating presigned URL for {object_id} with "
                    f"key='{relative_storage_path}', key_prefix='{backend_root_path_stripped}', "
                    f"bucket={bucket_name}"
                )
                presigned_url = await self._generate_presigned_url(
                    key=relative_storage_path,
                    operation="get_object",
                    expiration=self.settings.s3_presigned_url_download_timeout if hasattr(self.settings, 's3_presigned_url_download_timeout') else 3600,
                    storage_backend=backend_info,
                    content_type=content_type
                )
                
                # Cache the presigned URL with TTL matching expiration time
                if presigned_url:
                    try:
                        from ..core.dependencies import get_cache_service
                        cache_service = get_cache_service()
                        expiration_ttl = self.settings.s3_presigned_url_download_timeout if hasattr(self.settings, 's3_presigned_url_download_timeout') else 3600
                        await cache_service.set(cache_key, presigned_url, ttl=expiration_ttl)
                        logger.debug(f"[_create_get_urls_cached] Cached presigned URL for {object_id} (TTL: {expiration_ttl}s)")
                    except Exception as e:
                        logger.debug(f"Failed to cache presigned URL {object_id}: {e}")
                        # Don't fail if caching fails

            if presigned_url:
                logger.debug(f"[_create_get_urls_cached] Generated presigned URL for {object_id}: {presigned_url[:150]}...")
            else:
                logger.error(f"[_create_get_urls_cached] Failed to generate presigned URL for {object_id}")
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
    
    async def _get_objects_batch(self, object_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get multiple objects in a single database query (major performance optimization)
        
        This eliminates the N+1 query problem by fetching all objects at once.
        """
        if not object_ids:
            return {}
        
        try:
            # Build WHERE clause with IN operator for batch query
            # Escape single quotes in IDs to prevent SQL injection
            escaped_ids = [obj_id.replace("'", "''") for obj_id in object_ids]
            ids_str = "', '".join(escaped_ids)
            where_clause = f"id IN ('{ids_str}')"
            
            # Execute batch query in thread pool
            result = await asyncio.to_thread(
                lambda: self.vast_db.query("objects").select("*").where(where_clause).execute()
            )
            
            # Convert result to dictionary mapping object_id -> object_data
            objects_dict: Dict[str, Optional[Dict[str, Any]]] = {}
            
            # Handle VAST query result format
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # VAST tabular format: columns dict -> reconstruct rows
                    columns = data
                    if columns:
                        try:
                            row_count = len(next(iter(columns.values())))
                        except StopIteration:
                            row_count = 0
                        
                        for i in range(row_count):
                            obj_data = {}
                            obj_id = None
                            for col, values in columns.items():
                                if col != '$row_id':  # Skip internal row IDs
                                    try:
                                        value = values[i] if i < len(values) else None
                                        obj_data[col] = value
                                        if col == 'id':
                                            obj_id = value
                                    except Exception:
                                        obj_data[col] = None
                            
                            if obj_id:
                                # Parse metadata JSON string if present
                                if 'metadata' in obj_data and isinstance(obj_data['metadata'], str):
                                    try:
                                        import json
                                        obj_data['metadata'] = json.loads(obj_data['metadata'])
                                    except (json.JSONDecodeError, TypeError):
                                        obj_data['metadata'] = None
                                
                                objects_dict[obj_id] = obj_data
            elif isinstance(result, list):
                # List format
                for item in result:
                    if isinstance(item, dict):
                        obj_id = item.get('id')
                        if obj_id:
                            # Parse metadata JSON string if present
                            if 'metadata' in item and isinstance(item['metadata'], str):
                                try:
                                    import json
                                    item['metadata'] = json.loads(item['metadata'])
                                except (json.JSONDecodeError, TypeError):
                                    item['metadata'] = None
                            objects_dict[obj_id] = item
            
            # Mark missing objects as None
            for obj_id in object_ids:
                if obj_id not in objects_dict:
                    objects_dict[obj_id] = None
            
            logger.debug(f"Batch query returned {len([v for v in objects_dict.values() if v is not None])} objects out of {len(object_ids)} requested")
            return objects_dict
            
        except Exception as e:
            logger.error(f"Failed to batch fetch objects: {e}", exc_info=True)
            # Fallback: return empty dict, individual queries will be used
            return {obj_id: None for obj_id in object_ids}
    
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
            # Run blocking database query in thread pool to avoid blocking event loop
            # This is especially important in dev mode with single worker
            result = await asyncio.to_thread(
                lambda: self.vast_db.query("objects").select("*").where(f"id = '{object_id}'").execute()
            )
            
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
    
    async def _get_backend_info_cached(self, storage_id: Optional[str], storage_path: str) -> tuple[Optional[Dict[str, Any]], str]:
        """
        Get storage backend information with caching to avoid repeated lookups
        
        Returns:
            Tuple of (backend_info dict, relative_storage_path for S3 key)
        """
        backend_info = None
        relative_storage_path = storage_path
        
        if storage_id:
            # Check cache first
            if storage_id in self._backend_cache:
                backend_info = self._backend_cache[storage_id]
                logger.debug(f"Using cached backend info for storage_id: {storage_id}")
            else:
                # Fetch from database
                try:
                    from ..storagebackends.service import StorageBackendService
                    backend_service = StorageBackendService(self.vast_db, self.s3_client)
                    backend = await backend_service.get_storage_backend(storage_id)
                    if backend:
                        backend_info = backend.model_dump()
                        # Cache it
                        self._backend_cache[storage_id] = backend_info
                        logger.debug(f"Cached backend info for storage_id: {storage_id}")
                except Exception as e:
                    logger.warning(f"Failed to load storage backend {storage_id}: {e}")
            
            # Calculate relative path if backend_info is available
            if backend_info:
                backend_root_path = backend_info.get('root_path')
                if backend_root_path:
                    backend_root_path_stripped = backend_root_path.strip('/')
                    # If root_path is "/", backend_root_path_stripped will be empty string
                    # In this case, storage_path is already relative (doesn't include root_path)
                    if backend_root_path_stripped:
                        # If storage_path already includes root_path, strip it for S3 key
                        if storage_path.startswith(backend_root_path_stripped + '/'):
                            relative_storage_path = storage_path[len(backend_root_path_stripped) + 1:]
                            logger.debug(f"[_get_backend_info_cached] Stripped root_path '{backend_root_path_stripped}' from storage_path: {storage_path} -> {relative_storage_path}")
                        elif storage_path == backend_root_path_stripped:
                            relative_storage_path = ""
                            logger.debug(f"[_get_backend_info_cached] Storage path equals root_path, using empty relative path")
                        else:
                            # If storage_path doesn't include root_path, it's already relative
                            # (This happens when path was reconstructed from timestamp)
                            logger.debug(f"[_get_backend_info_cached] Storage path doesn't start with root_path, using as-is: {relative_storage_path}")
                    else:
                        # root_path is "/" (stripped to empty), storage_path is already relative
                        logger.debug(f"[_get_backend_info_cached] root_path is '/', storage_path is already relative: {relative_storage_path}")
        
        return backend_info, relative_storage_path
    
    async def _get_backend_info(self, storage_id: Optional[str], storage_path: str) -> tuple[Optional[Dict[str, Any]], str]:
        """
        Get storage backend information and calculate relative storage path
        
        If storage_path doesn't include root_path, try to prepend it from backend.
        
        Returns:
            Tuple of (backend_info dict, relative_storage_path for S3 key)
        """
        # Use cached version
        return await self._get_backend_info_cached(storage_id, storage_path)
    
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
                key_prefix = backend_root_path.strip('/') if backend_root_path else ""
                
                # Log S3 key construction details for debugging
                bucket_name = storage_backend.get('bucket_name') or self.settings.s3_bucket_name
                final_s3_key = f"{key_prefix}/{key}" if key_prefix else key
                logger.debug(
                    f"[_generate_presigned_url] Generating presigned URL - "
                    f"bucket: {bucket_name}, key_prefix: '{key_prefix}', key: '{key}', "
                    f"final_s3_key: '{final_s3_key}', operation: {operation}"
                )
                
                cfg = S3Config(
                    endpoint_url=storage_backend.get('endpoint_url') or self.settings.s3_endpoint_url or "",
                    bucket_name=bucket_name,
                    access_key=access_key,
                    secret_key=secret_key,
                    region=storage_backend.get('region') or self.settings.s3_region,
                    use_ssl=bool(storage_backend.get('use_ssl') if storage_backend.get('use_ssl') is not None else self.settings.s3_use_ssl),
                    chunk_size=self.settings.vaststore_s3_chunk_size,
                    max_concurrent_parts=self.settings.vaststore_s3_max_concurrent_parts,
                    key_prefix=key_prefix,
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
                presigned_url = await loop.run_in_executor(self._executor, bound_func)
                logger.debug(f"[_generate_presigned_url] Generated presigned URL (first 100 chars): {presigned_url[:100] if presigned_url else 'None'}...")
                return presigned_url
            
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
            import time
            current_time = time.time()
            
            # Check cache first (with TTL)
            if (self._all_backends_cache is not None and 
                self._all_backends_cache_time is not None and
                (current_time - self._all_backends_cache_time) < self._backend_cache_ttl):
                logger.debug("Using cached storage backends list")
                backends = self._all_backends_cache
            else:
                # Fetch from database and cache
                from ..storagebackends.service import StorageBackendService
                backend_service = StorageBackendService(self.vast_db, self.s3_client)
                backends_list = await backend_service.get_storage_backends()
                # Convert to dict format for caching
                backends = [b.model_dump() for b in backends_list]
                self._all_backends_cache = backends
                self._all_backends_cache_time = current_time
                logger.debug(f"Cached storage backends list ({len(backends)} backends)")
            
            default_backend = next((b for b in backends if b.get('default_storage')), None)
            if default_backend:
                storage_id = default_backend.get('id')
                if storage_id:
                    logger.debug(f"Using default storage backend for get_urls: {storage_id}")
                    return storage_id
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


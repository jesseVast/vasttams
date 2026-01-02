"""
Minimal Segments Router

This is a minimal working segments router that uses the new storage service architecture.
It provides basic endpoint structure that can be expanded later.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks, Response
from typing import List, Optional
from pydantic import ValidationError
from .models import FlowSegment
from ..service.storage_models import FlowStorage, FlowStoragePost
from ..common.storage import get_storage_service
from ..common.storage.interfaces import StorageInterface
from ..events import EventManager
from ..core.dependencies import get_vast_db, get_s3_client
from ..core.utils import log_pydantic_validation_error, safe_model_parse
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tams/v8.0/flows", tags=["segments"])


async def update_object_size_from_s3(object_id: str):
    """Background task to update object size from S3 after segment creation
    
    This function checks the database directly for size and storage_path to avoid
    race conditions with get_object() fallback updates. It only queries S3 if
    the size is still NULL/0 in the database.
    """
    try:
        import json
        from ..core.dependencies import get_vast_db, get_s3_client
        
        vast_db = get_vast_db()
        objects_table = vast_db.get_qualified_table_name("objects")
        
        # First, check if size is already set (avoid race condition and unnecessary S3 queries)
        check_sql = f"""
            SELECT size, metadata 
            FROM {objects_table} 
            WHERE id = '{object_id}'
        """
        check_result = vast_db.execute_sql(check_sql)
        
        # Parse result to check current size
        size = None
        metadata_str = None
        
        if isinstance(check_result, dict) and 'data' in check_result:
            data = check_result['data']
            if isinstance(data, dict):
                # Columnar format
                size_col = data.get('size', [])
                metadata_col = data.get('metadata', [])
                if size_col and len(size_col) > 0:
                    size = size_col[0]
                if metadata_col and len(metadata_col) > 0:
                    metadata_str = metadata_col[0]
            elif isinstance(data, list) and len(data) > 0:
                # Row-oriented format
                row = data[0]
                if isinstance(row, dict):
                    size = row.get('size')
                    metadata_str = row.get('metadata')
        elif isinstance(check_result, list) and len(check_result) > 0:
            row = check_result[0]
            if isinstance(row, dict):
                size = row.get('size')
                metadata_str = row.get('metadata')
        
        # If size is already set, skip S3 query (avoid race condition)
        if size is not None and size > 0:
            return
        
        # If no metadata, can't get storage_path
        if not metadata_str:
            logger.debug("Object %s has no metadata, skipping size update", object_id)
            return
        
        # Parse metadata to get storage_path
        try:
            if isinstance(metadata_str, str):
                metadata = json.loads(metadata_str)
            else:
                metadata = metadata_str
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("Object %s has invalid metadata format: %s", object_id, e)
            return
        
        storage_path = metadata.get('storage_path')
        if not storage_path:
            logger.debug("Object %s has no storage_path in metadata, skipping size update", object_id)
            return
        
        # Get storage_id if available to use backend-specific client
        storage_id = metadata.get('storage_id')
        relative_storage_path = storage_path
        s3_client = None
        
        # If storage_id is available, create backend-specific client
        if storage_id:
            try:
                from ..storagebackends.service import StorageBackendService
                from ..core.dependencies import get_vast_db
                from vasts3 import S3Client, S3Config
                from ..core.config import get_settings
                
                vast_db = get_vast_db()
                backend_service = StorageBackendService(vast_db, None)
                backend = await backend_service.get_storage_backend(storage_id)
                
                if backend:
                    settings = get_settings()
                    backend_root_path = backend.root_path
                    
                    # If storage_path includes root_path, strip it for use with key_prefix
                    if backend_root_path:
                        backend_root_path = backend_root_path.strip('/')
                        if storage_path.startswith(backend_root_path + '/'):
                            relative_storage_path = storage_path[len(backend_root_path) + 1:]
                        elif storage_path == backend_root_path:
                            relative_storage_path = ""
                    
                    # Create backend-specific S3Client
                    key_prefix = backend_root_path.strip('/') if backend_root_path else ""
                    cfg = S3Config(
                        endpoint_url=backend.endpoint_url or settings.s3_endpoint_url,
                        bucket_name=backend.bucket_name or settings.s3_bucket_name,
                        access_key=backend.access_key or settings.s3_access_key_id,
                        secret_key=backend.secret_key or settings.s3_secret_access_key,
                        region=backend.region or settings.s3_region,
                        use_ssl=backend.use_ssl if backend.use_ssl is not None else settings.s3_use_ssl,
                        chunk_size=settings.vaststore_s3_chunk_size,
                        max_concurrent_parts=settings.vaststore_s3_max_concurrent_parts,
                        key_prefix=key_prefix,
                    )
                    s3_client = S3Client(cfg)
            except Exception as e:
                logger.warning("Failed to create backend-specific client for object %s: %s, falling back to default", object_id, e)
        
        # Fallback to default client if backend-specific client wasn't created
        if not s3_client:
            s3_client = get_s3_client()
            if not s3_client:
                logger.debug("S3 client not available for object %s", object_id)
                return
        
        # Get object metadata using vasts3
        try:
            s3_metadata = s3_client.get_object_metadata(key=relative_storage_path)
            if not s3_metadata:
                logger.debug("Object %s not found in S3 at path: %s", object_id, storage_path)
                return
            
            # vasts3 returns 'content_length' (lowercase, underscore), not 'ContentLength'
            s3_size = 0
            if isinstance(s3_metadata, dict):
                s3_size = s3_metadata.get('content_length') or s3_metadata.get('ContentLength', 0) or 0
            elif hasattr(s3_metadata, 'content_length'):
                s3_size = s3_metadata.content_length
            elif hasattr(s3_metadata, 'ContentLength'):
                s3_size = s3_metadata.ContentLength
            
            if s3_size > 0:
                # Double-check size is still NULL/0 before updating (handle race condition)
                # Use atomic UPDATE with WHERE clause to ensure idempotency
                update_sql = f"""
                    UPDATE {objects_table} 
                    SET size = {s3_size} 
                    WHERE id = '{object_id}' AND (size IS NULL OR size = 0)
                """
                vast_db.execute_sql(update_sql)
                logger.debug("Updated size for object %s: %d bytes", object_id, s3_size)
        except Exception as s3_err:
            # Handle 404 errors gracefully - object may have been deleted or doesn't exist yet
            # This is expected in some scenarios (cleanup, test data, etc.)
            error_msg = str(s3_err).lower()
            if '404' in error_msg or 'not found' in error_msg:
                logger.debug("Object %s not found in S3 (expected in some scenarios): %s", object_id, relative_storage_path)
            else:
                logger.warning("Failed to get metadata from S3 for object %s: %s", object_id, s3_err)
            
    except Exception as e:
        # Log but don't fail - this is a background task
        logger.warning("Failed to update object size from S3 for object %s: %s", object_id, e)


async def update_object_metadata_with_filename(object_id: str, filename: str):
    """Background task to update object metadata with filename after segment creation
    
    This function updates the metadata JSON field in the objects table to include
    the filename. It preserves existing metadata fields (storage_path, content_type, storage_id).
    """
    try:
        import json
        from ..core.dependencies import get_vast_db
        
        vast_db = get_vast_db()
        objects_table = vast_db.get_qualified_table_name("objects")
        
        # Get existing metadata
        check_sql = f"""
            SELECT metadata 
            FROM {objects_table} 
            WHERE id = '{object_id}'
        """
        check_result = vast_db.execute_sql(check_sql)
        
        # Parse result to get current metadata
        metadata_str = None
        
        if isinstance(check_result, dict) and 'data' in check_result:
            data = check_result['data']
            if isinstance(data, dict):
                # Columnar format
                metadata_col = data.get('metadata', [])
                if metadata_col and len(metadata_col) > 0:
                    metadata_str = metadata_col[0]
            elif isinstance(data, list) and len(data) > 0:
                # Row-oriented format
                row = data[0]
                if isinstance(row, dict):
                    metadata_str = row.get('metadata')
        elif isinstance(check_result, list) and len(check_result) > 0:
            row = check_result[0]
            if isinstance(row, dict):
                metadata_str = row.get('metadata')
        
        # Parse existing metadata
        if metadata_str:
            try:
                if isinstance(metadata_str, str):
                    metadata = json.loads(metadata_str)
                else:
                    metadata = metadata_str
            except (json.JSONDecodeError, TypeError):
                # If metadata is invalid, create new dict with just filename
                metadata = {}
        else:
            # No existing metadata, create new dict
            metadata = {}
        
        # Update/add filename field
        metadata['filename'] = filename
        
        # Convert back to JSON string and update database
        updated_metadata = json.dumps(metadata)
        # Escape single quotes for SQL
        updated_metadata_escaped = updated_metadata.replace("'", "''")
        
        update_sql = f"""
            UPDATE {objects_table} 
            SET metadata = '{updated_metadata_escaped}'
            WHERE id = '{object_id}'
        """
        vast_db.execute_sql(update_sql)
        logger.debug("Updated metadata for object %s with filename: %s", object_id, filename)
        
    except Exception as e:
        # Log but don't fail - this is a background task
        logger.warning("Failed to update object metadata with filename for object %s: %s", object_id, e)

# HEAD endpoint
@router.head("/{flow_id}/segments")
async def head_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    object_id: Optional[str] = Query(None, description="Filter on object identifier"),
    reverse_order: bool = Query(False, description="Return segments in reverse time order"),
    verbose_storage: bool = Query(False, description="Include storage metadata in get_urls"),
    accept_get_urls: Optional[str] = Query(None, description="Comma-separated list of labels of flow segment get_urls to include"),
    accept_storage_ids: Optional[str] = Query(None, description="Comma-separated list of storage_id UUIDs to include"),
    presigned: Optional[bool] = Query(None, description="Filter presigned vs non-presigned URLs"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Limit number of results (max 1000)"),
    offset: Optional[int] = Query(None, description="Offset for pagination")
):
    """Return flow segments path headers"""
    return {}

# GET endpoint
@router.get("/{flow_id}/segments", response_model=List[FlowSegment])
async def list_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    object_id: Optional[str] = Query(None, description="Filter on object identifier"),
    reverse_order: bool = Query(False, description="Return segments in reverse time order"),
    verbose_storage: bool = Query(False, description="Include storage metadata in get_urls"),
    accept_get_urls: Optional[str] = Query(None, description="Comma-separated list of labels of flow segment get_urls to include"),
    accept_storage_ids: Optional[str] = Query(None, description="Comma-separated list of storage_id UUIDs to include"),
    presigned: Optional[bool] = Query(None, description="Filter presigned vs non-presigned URLs"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Limit number of results (max 1000)"),
    offset: Optional[int] = Query(None, description="Offset for pagination"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """List segments for a specific flow"""
    try:
        import time
        start_time = time.time()
        
        # Skip expensive get_urls generation only if accept_get_urls is explicitly set to empty string (per TAMS spec ADR-0023)
        # Generate get_urls by default for UI compatibility - only skip if explicitly requested with accept_get_urls=""
        # Note: Performance optimizations (batch queries, parallel processing, caching) make URL generation fast enough
        # that we can generate URLs even for initial loads without significant performance impact
        skip_get_urls_generation = accept_get_urls == ""
        
        # Log if we're generating URLs (for performance monitoring)
        if not skip_get_urls_generation:
            logger.debug(f"Generating get_urls for segments in flow {flow_id} (using optimized batch processing)")
        
        db_start = time.time()
        segments = await storage.get_flow_segments(flow_id, timerange, skip_get_urls_generation=skip_get_urls_generation)
        db_time = time.time() - db_start
        
        # Apply object_id filtering if specified
        filter_start = time.time()
        if object_id:
            segments = [s for s in segments if s.object_id == object_id]
        
        # Apply reverse order sorting if specified
        if reverse_order:
            # Sort by timerange value in descending order
            segments.sort(key=lambda s: s.timerange.value if s.timerange else "", reverse=True)
        else:
            # Sort by timerange value in ascending order (default)
            segments.sort(key=lambda s: s.timerange.value if s.timerange else "")
        filter_time = time.time() - filter_start
        
        # Apply verbose_storage filtering if specified
        if not verbose_storage:
            # Remove verbose storage metadata from get_urls
            from .models import GetUrl
            for segment in segments:
                if hasattr(segment, 'get_urls') and segment.get_urls:
                    # Keep only url, presigned, and label fields
                    filtered_urls = []
                    for url_info in segment.get_urls:
                        # Extract fields from GetUrl object or dict
                        if isinstance(url_info, GetUrl):
                            url = url_info.url
                            presigned = url_info.presigned
                            label = url_info.label
                            storage_id = url_info.storage_id
                            provider = url_info.provider
                            store_product = url_info.store_product
                        else:
                            url = url_info.get('url') if isinstance(url_info, dict) else getattr(url_info, 'url', None)
                            presigned = url_info.get('presigned') if isinstance(url_info, dict) else getattr(url_info, 'presigned', None)
                            label = url_info.get('label') if isinstance(url_info, dict) else getattr(url_info, 'label', None)
                            storage_id = url_info.get('storage_id') if isinstance(url_info, dict) else getattr(url_info, 'storage_id', '')
                            provider = url_info.get('provider') if isinstance(url_info, dict) else getattr(url_info, 'provider', '')
                            store_product = url_info.get('store_product') if isinstance(url_info, dict) else getattr(url_info, 'store_product', '')
                        
                        # Create GetUrl object with minimal fields (required fields must be present)
                        filtered_url = GetUrl(
                            url=url or '',
                            provider=provider or '',  # Required field
                            store_product=store_product or '',  # Required field
                            storage_id=storage_id or '',  # Required field
                            presigned=presigned,
                            label=label
                        )
                        filtered_urls.append(filtered_url)
                    segment.get_urls = filtered_urls
        
        # Apply URL filtering if specified
        from .models import GetUrl
        for segment in segments:
            if hasattr(segment, 'get_urls') and segment.get_urls:
                filtered_urls = []
                
                for url_info in segment.get_urls:
                    # Normalize url_info - extract fields from GetUrl object or dict
                    if isinstance(url_info, GetUrl):
                        url = url_info.url
                        label = url_info.label
                        storage_id = url_info.storage_id
                        url_presigned = url_info.presigned
                        provider = url_info.provider
                        store_product = url_info.store_product
                        store_type = url_info.store_type
                    else:
                        # Handle dict or other types
                        url = url_info.get('url') if isinstance(url_info, dict) else getattr(url_info, 'url', None)
                        label = url_info.get('label') if isinstance(url_info, dict) else getattr(url_info, 'label', None)
                        storage_id = url_info.get('storage_id') if isinstance(url_info, dict) else getattr(url_info, 'storage_id', None)
                        url_presigned = url_info.get('presigned') if isinstance(url_info, dict) else getattr(url_info, 'presigned', None)
                        provider = url_info.get('provider') if isinstance(url_info, dict) else getattr(url_info, 'provider', '')
                        store_product = url_info.get('store_product') if isinstance(url_info, dict) else getattr(url_info, 'store_product', '')
                        store_type = url_info.get('store_type') if isinstance(url_info, dict) else getattr(url_info, 'store_type', 'http_object_store')
                    
                    # Apply accept_get_urls filtering (by label)
                    if accept_get_urls:
                        url_labels = [label.strip() for label in accept_get_urls.split(',') if label.strip()]
                        if url_labels:  # Only filter if labels are specified
                            if label not in url_labels:
                                continue  # Skip this URL
                    
                    # Apply accept_storage_ids filtering (by storage_id)
                    if accept_storage_ids:
                        storage_ids = [sid.strip() for sid in accept_storage_ids.split(',') if sid.strip()]
                        if storage_ids:  # Only filter if storage IDs are specified
                            if storage_id not in storage_ids:
                                continue  # Skip this URL
                    
                    # Apply presigned filtering
                    if presigned is not None:
                        # presigned is the query parameter (bool), compare with URL's presigned value
                        if url_presigned != presigned:
                            continue  # Skip this URL
                    
                    # URL passed all filters - create GetUrl object
                    filtered_url = GetUrl(
                        url=url or '',
                        provider=provider or '',
                        store_product=store_product or '',
                        storage_id=storage_id or '',
                        presigned=url_presigned,
                        label=label,
                        store_type=store_type
                    )
                    filtered_urls.append(filtered_url)
                
                # Update segment with filtered URLs
                segment.get_urls = filtered_urls
        
        # Apply pagination if specified
        pagination_start = time.time()
        if offset is not None:
            segments = segments[offset:]
        
        # Enforce maximum limit of 1000 (safety check even though Query validation should catch it)
        if limit is not None:
            limit = min(limit, 1000)  # Cap at 1000
            segments = segments[:limit]
        pagination_time = time.time() - pagination_start
        
        # Log performance metrics
        total_time = time.time() - start_time
        logger.info(
            f"get_flow_segments performance - "
            f"DB+URLs: {db_time:.3f}s, "
            f"Filter+Sort: {filter_time:.3f}s, "
            f"Pagination: {pagination_time:.3f}s, "
            f"Total: {total_time:.3f}s, "
            f"Segments: {len(segments)}, "
            f"Skip URLs: {skip_get_urls_generation}"
        )
        
        return segments
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list segments for flow %s: %s", flow_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# POST endpoint for creating flow segments
@router.post("/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_new_flow_segment(
    flow_id: str,
    segment: FlowSegment = Body(...),
    filename: Optional[str] = Query(None, description="Source filename for object metadata"),
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new flow segment"""
    try:
        # Get username for logging (segments don't have created_by/updated_by in TAMS spec)
        username = user_session.username if user_session else "system"
        logger.debug("User %s creating segment for flow %s", username, flow_id)
        # Validate segment data
        if not segment.object_id:
            raise HTTPException(status_code=400, detail="object_id is required")
        if not segment.timerange:
            raise HTTPException(status_code=400, detail="timerange is required")
        
        # Create segment using storage service
        success = await storage.create_flow_segment(flow_id, segment)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create segment")
        
        # Emit segment created event
        try:
            vast_db = get_vast_db()
            event_manager = EventManager(vast_db)
            await event_manager.emit_segment_event('flow-segments/created', segment, flow_id=flow_id)
        except Exception as e:
            logger.warning("Failed to emit segment created event: %s", e)
        
        # Update object size from S3 in background (non-blocking)
        if segment.object_id:
            background_tasks.add_task(update_object_size_from_s3, segment.object_id)
        
        # Update object metadata with filename in background (non-blocking)
        if segment.object_id and filename:
            background_tasks.add_task(update_object_metadata_with_filename, segment.object_id, filename)
        
        return segment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create segment for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# DELETE endpoint
@router.delete("/{flow_id}/segments")
async def delete_flow_segments_by_id(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Only delete flow segments that are completely covered by the given timerange"),
    object_id: Optional[str] = Query(None, description="Filter on object identifier"),
    storage: StorageInterface = Depends(get_storage_service),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_session: UserSession = Depends(require_admin)
):
    """Delete segments for a specific flow
    
    For long-running deletions (large timeranges or many segments), this will create
    a deletion request and return 202 Accepted with the request ID. The deletion will
    be processed asynchronously.
    """
    try:
        from ..service.deletion_service import DeletionRequestService
        from ..common.models import TimeRange
        from ..core.dependencies import get_vast_db, get_s3_client
        from ..segments.service import SegmentStorageService
        from ..flows.service import FlowStorageService
        
        vast_db = get_vast_db()
        deletion_service = DeletionRequestService(vast_db)
        
        # If object_id is specified, we need to filter segments first
        if object_id:
            # Get segments to find the ones matching object_id
            segments = await storage.get_flow_segments(flow_id, timerange)
            matching_segments = [s for s in segments if s.object_id == object_id]
            
            if not matching_segments:
                raise HTTPException(status_code=404, detail="No segments found with specified object_id")
            
            # For object_id deletions, check if we should use async deletion
            if len(matching_segments) > 50:  # Threshold for async deletion
                # Create deletion request for async processing
                # Note: We'll need to handle object_id filtering in the deletion service
                # For now, fall back to synchronous deletion for object_id
                deleted_count = 0
                for segment in matching_segments:
                    success = await storage.delete_flow_segments(flow_id, timerange)
                    if success:
                        deleted_count += 1
                return {"message": f"Deleted {deleted_count} segments with object_id {object_id}"}
            else:
                # Small deletion - do synchronously
                deleted_count = 0
                for segment in matching_segments:
                    success = await storage.delete_flow_segments(flow_id, timerange)
                    if success:
                        deleted_count += 1
                return {"message": f"Deleted {deleted_count} segments with object_id {object_id}"}
        else:
            # Timerange-based deletion
            if timerange:
                # Check if this will be a long-running operation
                segments = await storage.get_flow_segments(flow_id, timerange)
                segment_count = len(segments) if segments else 0
                
                # Quantity threshold: if more than 50 segments, use async deletion immediately
                if segment_count > 50:
                    # Create deletion request for async processing
                    try:
                        timerange_obj = TimeRange(value=timerange)
                        deletion_request = await deletion_service.create_deletion_request(
                            flow_id=flow_id,
                            timerange_to_delete=timerange_obj,
                            delete_flow=False,
                            created_by=user_session.username if user_session else "system"
                        )
                        
                        # Start background processing
                        segment_service = SegmentStorageService(vast_db, get_s3_client())
                        flow_service = FlowStorageService(vast_db, get_s3_client())
                        background_tasks.add_task(
                            deletion_service.process_deletion_request,
                            deletion_request.id,
                            segment_service,
                            flow_service
                        )
                        
                        # Return 202 Accepted with Location header
                        return Response(
                            status_code=202,
                            headers={"Location": f"/flow-delete-requests/{deletion_request.id}"},
                            content=f'{{"id": "{deletion_request.id}", "status": "created", "message": "Deletion request created"}}',
                            media_type="application/json"
                        )
                    except Exception as e:
                        logger.error("Failed to create deletion request: %s", e)
                        # Fall back to synchronous deletion
                        pass
                
                # Synchronous deletion for small operations (<= 50 segments)
                # But with 30-second timeout - if it takes too long, switch to async
                try:
                    start_time = time.time()
                    deletion_timeout = 30.0  # 30 seconds
                    
                    # Attempt deletion with timeout
                    try:
                        success = await asyncio.wait_for(
                            storage.delete_flow_segments(flow_id, timerange),
                            timeout=deletion_timeout
                        )
                        
                        elapsed_time = time.time() - start_time
                        
                        if not success:
                            return Response(status_code=204)
                        return {"message": "Segments deleted successfully"}
                    
                    except asyncio.TimeoutError:
                        # Deletion took more than 30 seconds - switch to async
                        elapsed_time = time.time() - start_time
                        logger.info(
                            "Deletion for flow %s exceeded %ds timeout (took %.2fs), switching to async deletion request",
                            flow_id, deletion_timeout, elapsed_time
                        )
                        
                        # Create deletion request for async processing
                        timerange_obj = TimeRange(value=timerange)
                        deletion_request = await deletion_service.create_deletion_request(
                            flow_id=flow_id,
                            timerange_to_delete=timerange_obj,
                            delete_flow=False,
                            created_by=user_session.username if user_session else "system"
                        )
                        
                        # Start background processing
                        segment_service = SegmentStorageService(vast_db, get_s3_client())
                        flow_service = FlowStorageService(vast_db, get_s3_client())
                        background_tasks.add_task(
                            deletion_service.process_deletion_request,
                            deletion_request.id,
                            segment_service,
                            flow_service
                        )
                        
                        # Return 202 Accepted with Location header
                        return Response(
                            status_code=202,
                            headers={"Location": f"/flow-delete-requests/{deletion_request.id}"},
                            content=f'{{"id": "{deletion_request.id}", "status": "created", "message": "Deletion request created after timeout"}}',
                            media_type="application/json"
                        )
                
                except Exception as e:
                    logger.error("Failed to delete segments for flow %s: %s", flow_id, e)
                    if "not found" in str(e).lower() or "no segments" in str(e).lower():
                        raise HTTPException(status_code=404, detail="No segments found to delete")
                    raise HTTPException(status_code=500, detail="Internal server error")
            else:
                # Delete all segments - check segment count first
                segments = await storage.get_flow_segments(flow_id)
                segment_count = len(segments) if segments else 0
                
                # Quantity threshold: if more than 50 segments, use async deletion immediately
                if segment_count > 50:
                    # Create deletion request for async processing
                    try:
                        # For "all segments", we'll use a very large timerange
                        from ..common.models import TimeRange
                        timerange_obj = TimeRange(value="0:0_999999:0")  # Large timerange
                        deletion_request = await deletion_service.create_deletion_request(
                            flow_id=flow_id,
                            timerange_to_delete=timerange_obj,
                            delete_flow=False,
                            created_by=user_session.username if user_session else "system"
                        )
                        
                        # Start background processing
                        segment_service = SegmentStorageService(vast_db, get_s3_client())
                        flow_service = FlowStorageService(vast_db, get_s3_client())
                        background_tasks.add_task(
                            deletion_service.process_deletion_request,
                            deletion_request.id,
                            segment_service,
                            flow_service
                        )
                        
                        # Return 202 Accepted
                        return Response(
                            status_code=202,
                            headers={"Location": f"/flow-delete-requests/{deletion_request.id}"},
                            content=f'{{"id": "{deletion_request.id}", "status": "created", "message": "Deletion request created"}}',
                            media_type="application/json"
                        )
                    except Exception as e:
                        logger.error("Failed to create deletion request: %s", e)
                        # Fall back to synchronous deletion
                        pass
                
                # Synchronous deletion for small operations (<= 50 segments)
                # But with 30-second timeout - if it takes too long, switch to async
                try:
                    start_time = time.time()
                    deletion_timeout = 30.0  # 30 seconds
                    
                    # Attempt deletion with timeout
                    try:
                        success = await asyncio.wait_for(
                            storage.delete_flow_segments(flow_id, timerange),
                            timeout=deletion_timeout
                        )
                        
                        if not success:
                            return Response(status_code=204)
                        return {"message": "Segments deleted successfully"}
                    
                    except asyncio.TimeoutError:
                        # Deletion took more than 30 seconds - switch to async
                        elapsed_time = time.time() - start_time
                        logger.info(
                            "Deletion for flow %s exceeded %ds timeout (took %.2fs), switching to async deletion request",
                            flow_id, deletion_timeout, elapsed_time
                        )
                        
                        # Create deletion request for async processing
                        from ..common.models import TimeRange
                        timerange_obj = TimeRange(value="0:0_999999:0")  # Large timerange
                        deletion_request = await deletion_service.create_deletion_request(
                            flow_id=flow_id,
                            timerange_to_delete=timerange_obj,
                            delete_flow=False,
                            created_by=user_session.username if user_session else "system"
                        )
                        
                        # Start background processing
                        segment_service = SegmentStorageService(vast_db, get_s3_client())
                        flow_service = FlowStorageService(vast_db, get_s3_client())
                        background_tasks.add_task(
                            deletion_service.process_deletion_request,
                            deletion_request.id,
                            segment_service,
                            flow_service
                        )
                        
                        # Return 202 Accepted
                        return Response(
                            status_code=202,
                            headers={"Location": f"/flow-delete-requests/{deletion_request.id}"},
                            content=f'{{"id": "{deletion_request.id}", "status": "created", "message": "Deletion request created after timeout"}}',
                            media_type="application/json"
                        )
                
                except Exception as e:
                    logger.error("Failed to delete segments for flow %s: %s", flow_id, e)
                    raise HTTPException(status_code=500, detail="Internal server error")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete segments for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# Storage allocation endpoint
@router.post("/{flow_id}/storage", response_model=FlowStorage, status_code=201)
async def create_flow_storage_by_id(
    flow_id: str,
    request: FlowStoragePost,
    storage: StorageInterface = Depends(get_storage_service)
):
    """Allocate storage locations for writing media objects"""
    try:
        # Use storage service to allocate storage
        flow_storage = await storage.allocate_flow_storage(flow_id, request)
        return flow_storage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to allocate storage for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

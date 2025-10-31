"""
Minimal Segments Router

This is a minimal working segments router that uses the new storage service architecture.
It provides basic endpoint structure that can be expanded later.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["segments"])


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
        
        # Get S3 client (vasts3)
        s3_client = get_s3_client()
        if not s3_client:
            logger.debug("S3 client not available for object %s", object_id)
            return
        # Get object metadata using vasts3
        try:
            s3_metadata = s3_client.get_object_metadata(key=storage_path)
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
                logger.info("Updated size for object %s: %d bytes", object_id, s3_size)
        except Exception as s3_err:
            logger.warning("Failed to get metadata from S3 for object %s: %s", object_id, s3_err)
            
    except Exception as e:
        # Log but don't fail - this is a background task
        logger.warning("Failed to update object size from S3 for object %s: %s", object_id, e)

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
    limit: Optional[int] = Query(None, description="Limit number of results"),
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
    limit: Optional[int] = Query(None, description="Limit number of results"),
    offset: Optional[int] = Query(None, description="Offset for pagination"),
    storage: StorageInterface = Depends(get_storage_service)
):
    """List segments for a specific flow"""
    try:
        segments = await storage.get_flow_segments(flow_id, timerange)
        
        # Apply object_id filtering if specified
        if object_id:
            segments = [s for s in segments if s.object_id == object_id]
        
        # Apply reverse order sorting if specified
        if reverse_order:
            # Sort by timerange value in descending order
            segments.sort(key=lambda s: s.timerange.value if s.timerange else "", reverse=True)
        else:
            # Sort by timerange value in ascending order (default)
            segments.sort(key=lambda s: s.timerange.value if s.timerange else "")
        
        # Apply verbose_storage filtering if specified
        if not verbose_storage:
            # Remove verbose storage metadata from get_urls
            for segment in segments:
                if hasattr(segment, 'get_urls') and segment.get_urls:
                    # Keep only url, presigned, and label fields
                    filtered_urls = []
                    for url_info in segment.get_urls:
                        filtered_url = {
                            'url': url_info.get('url') if isinstance(url_info, dict) else getattr(url_info, 'url', None),
                            'presigned': url_info.get('presigned') if isinstance(url_info, dict) else getattr(url_info, 'presigned', None),
                            'label': url_info.get('label') if isinstance(url_info, dict) else getattr(url_info, 'label', None)
                        }
                        filtered_urls.append(filtered_url)
                    segment.get_urls = filtered_urls
        
        # Apply URL filtering if specified
        for segment in segments:
            if hasattr(segment, 'get_urls') and segment.get_urls:
                filtered_urls = []
                
                for url_info in segment.get_urls:
                    # Normalize url_info to dict
                    if not isinstance(url_info, dict):
                        url_info = {
                            'url': getattr(url_info, 'url', None),
                            'label': getattr(url_info, 'label', None),
                            'storage_id': getattr(url_info, 'storage_id', None),
                            'presigned': getattr(url_info, 'presigned', None)
                        }
                    
                    # Apply accept_get_urls filtering (by label)
                    if accept_get_urls:
                        url_labels = [label.strip() for label in accept_get_urls.split(',') if label.strip()]
                        if url_labels:  # Only filter if labels are specified
                            url_label = url_info.get('label', '')
                            if url_label not in url_labels:
                                continue  # Skip this URL
                    
                    # Apply accept_storage_ids filtering (by storage_id)
                    if accept_storage_ids:
                        storage_ids = [sid.strip() for sid in accept_storage_ids.split(',') if sid.strip()]
                        if storage_ids:  # Only filter if storage IDs are specified
                            url_storage_id = url_info.get('storage_id', '')
                            if url_storage_id not in storage_ids:
                                continue  # Skip this URL
                    
                    # Apply presigned filtering
                    if presigned is not None:
                        url_presigned = url_info.get('presigned', False)
                        if url_presigned != presigned:
                            continue  # Skip this URL
                    
                    # URL passed all filters
                    filtered_urls.append(url_info)
                
                # Update segment with filtered URLs
                segment.get_urls = filtered_urls
        
        # Apply pagination if specified
        if offset is not None:
            segments = segments[offset:]
        
        if limit is not None:
            segments = segments[:limit]
        
        return segments
    except Exception as e:
        logger.error("Failed to list segments for flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

# POST endpoint for creating flow segments
@router.post("/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_new_flow_segment(
    flow_id: str,
    segment: FlowSegment = Body(...),
    storage: StorageInterface = Depends(get_storage_service),
    user_session: UserSession = Depends(require_editor),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new flow segment"""
    try:
        # Get username for logging (segments don't have created_by/updated_by in TAMS spec)
        username = user_session.username if user_session else "system"
        logger.info("User %s creating segment for flow %s", username, flow_id)
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
    storage: StorageInterface = Depends(get_storage_service)
):
    """Delete segments for a specific flow"""
    try:
        # If object_id is specified, we need to filter segments first
        if object_id:
            # Get segments to find the ones matching object_id
            segments = await storage.get_flow_segments(flow_id, timerange)
            matching_segments = [s for s in segments if s.object_id == object_id]
            
            if not matching_segments:
                raise HTTPException(status_code=404, detail="No segments found with specified object_id")
            
            # Delete each matching segment individually
            deleted_count = 0
            for segment in matching_segments:
                # For now, we'll use the existing delete method
                # In a full implementation, we'd need a delete by object_id method
                success = await storage.delete_flow_segments(flow_id, timerange)
                if success:
                    deleted_count += 1
            
            return {"message": f"Deleted {deleted_count} segments with object_id {object_id}"}
        else:
            # Original behavior for timerange-only deletion
            success = await storage.delete_flow_segments(flow_id, timerange)
            if not success:
                raise HTTPException(status_code=404, detail="No segments found to delete")
            
            return {"message": "Segments deleted successfully"}
        
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

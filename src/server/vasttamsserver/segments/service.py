"""
Segment Storage Service

This module handles all flow segment-related storage operations including
CRUD operations, filtering, and segment management.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import (
    get_tams_timestamp,
    prepare_data_for_pyarrow
)
from .models import FlowSegment
from .get_url_factory import GetUrlFactory
from ..service.storage_models import FlowStorage, FlowStoragePost, MediaObject
from ..common.models import HttpRequest

logger = logging.getLogger(__name__)


def _is_conflict_error(error: Exception) -> bool:
    """Check if an error is a 409 Conflict error from VAST"""
    error_str = str(error)
    # Check for common conflict error indicators
    return (
        "409" in error_str or
        "VastConflictException" in error_str or
        "Conflict" in error_str or
        "TabularWwc" in error_str
    )


class SegmentStorageService:
    """Handles flow segment-related storage operations"""
    
    def __init__(self, vast_db, s3_client, settings):
        self.vast_db = vast_db
        self.s3_client = s3_client
        self.settings = settings
        self._get_url_factory = GetUrlFactory(vast_db, s3_client, settings)
    
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None, skip_get_urls_generation: bool = False) -> List[FlowSegment]:
        """Get flow segments with optional timerange filtering"""
        try:
            # Try cache first (only if no timerange filter)
            # Timerange filtering requires DB calculation, so skip cache in that case
            # Note: We cache segments without get_urls, then generate get_urls on-demand if needed
            use_cache = timerange is None
            
            if use_cache:
                from ..core.dependencies import get_cache_service
                cache_service = get_cache_service()
                cache_key = f"flow_segments:{flow_id}"
                cached = await cache_service.get(cache_key)
                if cached:
                    try:
                        import json
                        # Reconstruct FlowSegment objects from cached data
                        segments_data = json.loads(cached) if isinstance(cached, str) else cached
                        segments = []
                        for seg_data in segments_data:
                            # get_urls are excluded from cache (set to None) to avoid expired presigned URLs
                            # They will be generated on-demand if skip_get_urls_generation=False
                            if 'get_urls' in seg_data:
                                seg_data['get_urls'] = None
                            # Reconstruct timerange
                            if 'timerange' in seg_data and isinstance(seg_data['timerange'], dict):
                                from ..common.models import TimeRange
                                seg_data['timerange'] = TimeRange(**seg_data['timerange'])
                            segments.append(FlowSegment(**seg_data))
                        logger.debug(f"Cache hit for flow segments: {flow_id} ({len(segments)} segments, get_urls excluded from cache)")
                        # If get_urls are needed, generate them now (even for cached segments)
                        if not skip_get_urls_generation:
                            # Generate get_urls for cached segments that need them
                            # Check both None and empty list cases
                            segments_needing_urls = [
                                segment for segment in segments 
                                if segment.get_urls is None or (isinstance(segment.get_urls, list) and len(segment.get_urls) == 0)
                            ]
                            if segments_needing_urls:
                                logger.debug(f"Generating get_urls for {len(segments_needing_urls)} cached segments (skip_get_urls_generation=False)")
                                valid_segments = [s for s in segments_needing_urls if s.object_id]
                                if valid_segments:
                                    logger.debug(f"Found {len(valid_segments)} segments with object_id out of {len(segments_needing_urls)} needing URLs")
                                    # Use factory's optimized batch processing
                                    object_ids = [segment.object_id for segment in valid_segments]
                                    batch_results = await self._get_url_factory.create_get_urls_batch(
                                        object_ids, 
                                        batch_size=100  # Increased from 10 to 100 for better parallelism
                                    )
                                    
                                    # Map results back to segments
                                    urls_generated = 0
                                    for segment in valid_segments:
                                        get_urls = batch_results.get(segment.object_id)
                                        if get_urls:
                                            segment.get_urls = get_urls
                                            urls_generated += 1
                                    logger.debug(f"Generated get_urls for {urls_generated} out of {len(valid_segments)} segments")
                                else:
                                    logger.warning(f"No segments with object_id found for URL generation (out of {len(segments_needing_urls)} segments)")
                            else:
                                logger.debug(f"All {len(segments)} cached segments already have get_urls")
                        else:
                            logger.debug(f"Skipping get_urls generation for cached segments (skip_get_urls_generation=True)")
                        return segments
                    except Exception as e:
                        logger.debug(f"Failed to deserialize cached segments for flow {flow_id}: {e}")
                        # Fall through to DB query
            
            # Query segments using vaststore
            # Run blocking database query in thread pool to avoid blocking event loop
            # This is especially important in dev mode with single worker
            # Exclude get_urls to avoid loading expired presigned URLs - they will be generated on-demand if needed
            query = self.vast_db.query("segments").select("id, flow_id, object_id, timerange_start, timerange_end, ts_offset, last_duration, sample_offset, sample_count, key_frame_count, created").where(f"flow_id = '{flow_id}'")
            
            result = await asyncio.to_thread(lambda: query.execute())
            
            # Convert to FlowSegment objects
            segments = []
            # VAST returns a dict with 'data' field containing column arrays
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        segment_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                segment_data[column] = value
                        
                        # Reconstruct timerange from separate start/end fields
                        timerange_start = segment_data.pop('timerange_start', None)
                        timerange_end = segment_data.pop('timerange_end', None)
                        
                        # Create timerange object - required field
                        if timerange_start and timerange_end:
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                        elif timerange_start:
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=str(timerange_start))
                        else:
                            # Provide a default timerange if both are missing
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value="0:0")
                        
                        # Parse JSON fields
                        for field in ['ts_offset', 'last_duration', 'get_urls']:
                            if field in segment_data and isinstance(segment_data[field], str):
                                try:
                                    import json
                                    parsed = json.loads(segment_data[field])
                                    if field == 'get_urls' and isinstance(parsed, list):
                                        # Convert list of dicts to GetUrl objects
                                        from .models import GetUrl
                                        segment_data[field] = [GetUrl(**url) if isinstance(url, dict) else url for url in parsed]
                                    else:
                                        segment_data[field] = parsed
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.debug(f"Failed to parse {field}: {e}")
                                    pass
                        
                        segments.append(FlowSegment(**segment_data))
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        segment_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        
                        # Reconstruct timerange from separate start/end fields
                        timerange_start = segment_data.pop('timerange_start', None)
                        timerange_end = segment_data.pop('timerange_end', None)
                        
                        # Create timerange object - required field
                        if timerange_start and timerange_end:
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                        elif timerange_start:
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value=str(timerange_start))
                        else:
                            # Provide a default timerange if both are missing
                            from ..common.models import TimeRange
                            segment_data['timerange'] = TimeRange(value="0:0")
                        
                        # Parse JSON fields (including get_urls into GetUrl models)
                        for field in ['ts_offset', 'last_duration', 'get_urls']:
                            if field in segment_data and isinstance(segment_data[field], str):
                                try:
                                    import json
                                    parsed = json.loads(segment_data[field])
                                    if field == 'get_urls' and isinstance(parsed, list):
                                        from .models import GetUrl
                                        segment_data[field] = [GetUrl(**url) if isinstance(url, dict) else url for url in parsed]
                                    else:
                                        segment_data[field] = parsed
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        segments.append(FlowSegment(**segment_data))
            else:
                # Fallback for direct list results
                for row in result:
                    segment_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    # Reconstruct timerange from separate start/end fields
                    timerange_start = segment_data.pop('timerange_start', None)
                    timerange_end = segment_data.pop('timerange_end', None)
                    
                    # Create timerange object - required field
                    if timerange_start and timerange_end:
                        from ..common.models import TimeRange
                        segment_data['timerange'] = TimeRange(value=f"{timerange_start}_{timerange_end}")
                    elif timerange_start:
                        from ..common.models import TimeRange
                        segment_data['timerange'] = TimeRange(value=str(timerange_start))
                    else:
                        # Provide a default timerange if both are missing
                        from ..common.models import TimeRange
                        segment_data['timerange'] = TimeRange(value="0:0")
                    
                    # Parse JSON fields (including get_urls into GetUrl models)
                    for field in ['ts_offset', 'last_duration', 'get_urls']:
                        if field in segment_data and isinstance(segment_data[field], str):
                            try:
                                import json
                                parsed = json.loads(segment_data[field])
                                if field == 'get_urls' and isinstance(parsed, list):
                                    from .models import GetUrl
                                    segment_data[field] = [GetUrl(**url) if isinstance(url, dict) else url for url in parsed]
                                else:
                                    segment_data[field] = parsed
                            except (json.JSONDecodeError, TypeError):
                                pass
                    segments.append(FlowSegment(**segment_data))
            
            # Filter by timerange if provided
            if timerange:
                try:
                    from ..core.timerange_utils import parse_tams_timerange
                    query_start, query_end = parse_tams_timerange(timerange)
                    
                    # Only filter if we got valid start and end times (not infinity)
                    if query_start is not None and query_end is not None and query_end != float('inf'):
                        filtered_segments = []
                        for segment in segments:
                            # Parse segment timerange
                            if segment.timerange and segment.timerange.value:
                                seg_start, seg_end = parse_tams_timerange(segment.timerange.value)
                                
                                # Check if segment overlaps with query timerange
                                # Overlap: segment_start < query_end AND segment_end > query_start
                                if seg_start is not None and seg_end is not None:
                                    if seg_start < query_end and seg_end > query_start:
                                        filtered_segments.append(segment)
                            
                        segments = filtered_segments
                        logger.debug(f"Filtered {len(segments)} segments matching timerange {timerange} (query: {query_start}s to {query_end}s)")
                except Exception as e:
                    logger.warning(f"Failed to filter segments by timerange {timerange}: {e}")
                    # Continue with unfiltered segments if parsing fails
            
            # Populate get_urls if missing (per TAMS spec - service should auto-populate controlled URLs)
            # Skip if skip_get_urls_generation is True (e.g., when accept_get_urls="" to avoid expensive operations)
            if not skip_get_urls_generation:
                # Collect segments that need get_urls generation
                segments_needing_urls = [
                    segment for segment in segments 
                    if not segment.get_urls or len(segment.get_urls) == 0
                ]
                
                if segments_needing_urls:
                    logger.debug(f"Auto-populating get_urls for {len(segments_needing_urls)} segments")
                    # Generate get_urls in parallel for better performance
                    # Filter out segments without object_id (shouldn't happen per TAMS spec, but be defensive)
                    valid_segments = [s for s in segments_needing_urls if s.object_id]
                    invalid_segments = [s for s in segments_needing_urls if not s.object_id]
                    
                    if invalid_segments:
                        logger.warning(f"Skipping {len(invalid_segments)} segments without object_id (data integrity issue)")
                    
                    if valid_segments:
                        # Use factory's optimized batch processing
                        # Factory now handles:
                        # - Batch database queries (single query for all objects)
                        # - Parallel batch processing (all batches in parallel)
                        # - Storage backend caching
                        object_ids = [segment.object_id for segment in valid_segments]
                        logger.debug(f"Generating get_urls for {len(object_ids)} segments using optimized batch processing")
                        batch_results = await self._get_url_factory.create_get_urls_batch(
                            object_ids, 
                            batch_size=100  # Increased from 20 to 100 for better parallelism
                        )
                        
                        # Map results back to segments
                        for segment in valid_segments:
                            get_urls = batch_results.get(segment.object_id)
                            if get_urls:
                                logger.debug(f"Generated {len(get_urls)} get_urls for object_id: {segment.object_id}")
                                segment.get_urls = get_urls
                            else:
                                logger.warning(f"Failed to generate get_urls for object_id: {segment.object_id} (returned None)")
            
            # Cache the result if appropriate (no timerange filter)
            # IMPORTANT: We exclude get_urls from cache to avoid caching expired presigned URLs
            # get_urls will be generated on-demand when needed
            if use_cache:
                try:
                    from ..core.dependencies import get_cache_service
                    cache_service = get_cache_service()
                    cache_key = f"flow_segments:{flow_id}"
                    # Serialize segments for caching (convert to dict, handling nested objects)
                    # CRITICAL: Exclude get_urls from cache since presigned URLs expire
                    segments_data = []
                    for seg in segments:
                        seg_dict = seg.model_dump()
                        # Convert timerange to dict
                        if 'timerange' in seg_dict and hasattr(seg_dict['timerange'], 'model_dump'):
                            seg_dict['timerange'] = seg_dict['timerange'].model_dump()
                        # Remove get_urls from cached data - they contain presigned URLs that expire
                        # get_urls will be generated on-demand when needed (and only when skip_get_urls_generation=False)
                        seg_dict['get_urls'] = None
                        segments_data.append(seg_dict)
                    
                    import json
                    cache_value = json.dumps(segments_data)
                    # Cache for 5 minutes (300 seconds) - segments don't change often
                    await cache_service.set(cache_key, cache_value, ttl=300)
                    logger.debug(f"Cached flow segments: {flow_id} ({len(segments)} segments, get_urls excluded)")
                except Exception as e:
                    logger.debug(f"Failed to cache segments for flow {flow_id}: {e}")
                    # Don't fail the request if caching fails
            
            return segments
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get flow segments for %s: %s", flow_id, e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def create_flow_segment(self, flow_id: str, segment: FlowSegment) -> bool:
        """Create a new flow segment"""
        try:
            # Validate that the object exists before creating the segment
            # This prevents orphaned segment references that cause get_urls generation failures
            if segment.object_id:
                obj_dict = await self._get_object(segment.object_id)
                if not obj_dict:
                    logger.error(
                        f"Cannot create segment for flow {flow_id}: object {segment.object_id} does not exist. "
                        f"Objects must be created via POST /flows/{{flowId}}/storage before segments can reference them."
                    )
                    # Record metrics
                    try:
                        from ..core.telemetry import metrics
                        metrics.orphaned_segment_references_total.labels(flow_id=flow_id).inc()
                    except Exception:
                        pass  # Don't fail if metrics unavailable
                    raise HTTPException(
                        status_code=404,
                        detail=f"Object {segment.object_id} not found. Objects must be allocated via POST /flows/{{flowId}}/storage before segments can reference them."
                    )
            
            segment_data = segment.model_dump()
            segment_data['flow_id'] = flow_id
            
            # Handle timerange splitting for database storage
            if 'timerange' in segment_data and segment_data['timerange']:
                timerange_obj = segment_data['timerange']
                if isinstance(timerange_obj, dict) and 'value' in timerange_obj:
                    timerange_value = timerange_obj['value']
                    # Split timerange into start and end for database storage
                    if '_' in timerange_value:
                        timerange_start, timerange_end = timerange_value.split('_', 1)
                        segment_data['timerange_start'] = timerange_start
                        segment_data['timerange_end'] = timerange_end
                        logger.debug(f"Split timerange {timerange_value} into start: {timerange_start}, end: {timerange_end}")
                    else:
                        # If no underscore, treat as start only
                        segment_data['timerange_start'] = timerange_value
                        segment_data['timerange_end'] = timerange_value
                        logger.debug(f"Set timerange {timerange_value} as both start and end")
                    
                    # Remove the original timerange field as it's not in the database schema
                    del segment_data['timerange']
                else:
                    # Handle case where timerange is already a string
                    timerange_value = str(timerange_obj)
                    if '_' in timerange_value:
                        timerange_start, timerange_end = timerange_value.split('_', 1)
                        segment_data['timerange_start'] = timerange_start
                        segment_data['timerange_end'] = timerange_end
                    else:
                        segment_data['timerange_start'] = timerange_value
                        segment_data['timerange_end'] = timerange_value
                    del segment_data['timerange']
            
            # Handle other JSON fields that need to be serialized
            for field in ['ts_offset', 'last_duration', 'get_urls']:
                if field in segment_data and segment_data[field] is not None:
                    if isinstance(segment_data[field], (dict, list)):
                        import json
                        segment_data[field] = json.dumps(segment_data[field])
                        logger.debug(f"Serialized {field} to JSON string")
            
            logger.debug("Creating segment with processed data: %s", segment_data)
            self.vast_db.insert_record("segments", segment_data)
            
            # Invalidate segments cache for this flow
            try:
                from ..core.dependencies import get_cache_service
                cache_service = get_cache_service()
                await cache_service.delete(f"flow_segments:{flow_id}")
                logger.debug(f"Invalidated segments cache for flow: {flow_id}")
            except Exception as e:
                logger.debug(f"Failed to invalidate segments cache for flow {flow_id}: {e}")
            
            # Maintain normalized relationship and object reference tracking
            try:
                import json as _json
                import uuid as _uuid
                # 1) Insert into flow_object_references if not already present
                existing = await asyncio.to_thread(
                    lambda: self.vast_db.query("flow_object_references").select("id").where(
                        f"flow_id = '{flow_id}' AND object_id = '{segment_data.get('object_id')}'"
                    ).execute()
                )
                already_exists = False
                if isinstance(existing, dict) and 'data' in existing:
                    data = existing['data']
                    # VAST returns column arrays; check if any rows exist
                    if isinstance(data, dict) and data and any(len(col) > 0 for col in data.values() if isinstance(col, list)):
                        already_exists = True
                    elif isinstance(data, list) and len(data) > 0:
                        already_exists = True
                elif isinstance(existing, list) and len(existing) > 0:
                    already_exists = True
                
                if not already_exists:
                    ref_row = {
                        "id": str(_uuid.uuid4()),
                        "flow_id": flow_id,
                        "object_id": segment_data.get('object_id'),
                        "created": get_tams_timestamp()
                    }
                    ref_row = prepare_data_for_pyarrow(ref_row)
                    self.vast_db.insert_record("flow_object_references", ref_row)
                
                # Note: We no longer update objects.referenced_by_flows as JSON
                # It's computed dynamically from segments/flow_object_references tables using JOINs
                # This is cleaner, avoids JSON parsing complexity, and uses normalized relational data
            except Exception as rel_err:
                logger.warning("Failed to update flow-object references for flow %s, object %s: %s", flow_id, segment_data.get('object_id'), rel_err)
            return True
        except Exception as e:
            logger.error("Failed to create flow segment: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """Delete flow segments"""
        try:
            # If timerange is provided, we need to filter segments first since timerange is not a column
            # The segments table has timerange_start and timerange_end columns
            if timerange:
                # Get segments first, filter by timerange, then delete individually
                segments = await self.get_flow_segments(flow_id, timerange)
                if not segments:
                    logger.debug("No segments found to delete for flow %s with timerange %s", flow_id, timerange)
                    return True  # Idempotent delete - return True if nothing to delete
                
                # Delete each segment individually by flow_id, object_id, and timerange
                # FlowSegment doesn't have an id field, so we delete by identifying fields
                segments_table = self.vast_db.get_qualified_table_name("segments")
                deleted_count = 0
                for segment in segments:
                    # Reconstruct timerange_start and timerange_end from segment timerange
                    timerange_value = segment.timerange.value if segment.timerange else "0:0"
                    if "_" in timerange_value:
                        timerange_start, timerange_end = timerange_value.split("_", 1)
                    else:
                        timerange_start = timerange_value
                        timerange_end = timerange_value
                    
                    delete_sql = f"""
                        DELETE FROM {segments_table} 
                        WHERE flow_id = '{flow_id}' 
                        AND object_id = '{segment.object_id}' 
                        AND timerange_start = '{timerange_start}' 
                        AND timerange_end = '{timerange_end}'
                    """
                    
                    # Retry logic for conflict errors (409) with exponential backoff
                    max_retries = 3
                    base_delay = 0.1  # 100ms base delay
                    success = False
                    
                    for attempt in range(max_retries):
                        try:
                            await asyncio.to_thread(lambda: self.vast_db.execute_sql(delete_sql))
                            deleted_count += 1
                            success = True
                            break
                        except Exception as e:
                            # Check if this is a conflict error that should be retried
                            if _is_conflict_error(e) and attempt < max_retries - 1:
                                # Exponential backoff: 100ms, 200ms, 400ms
                                delay = base_delay * (2 ** attempt)
                                logger.debug(
                                    "Conflict error deleting segment (flow_id=%s, object_id=%s, attempt %d/%d), "
                                    "retrying after %.3fs: %s",
                                    flow_id, segment.object_id, attempt + 1, max_retries, delay, str(e)[:200]
                                )
                                await asyncio.sleep(delay)
                                continue
                            else:
                                # Not a conflict error, or max retries reached
                                if _is_conflict_error(e):
                                    logger.warning(
                                        "Failed to delete segment after %d retries (flow_id=%s, object_id=%s): %s",
                                        max_retries, flow_id, segment.object_id, str(e)[:500]
                                    )
                                else:
                                    logger.warning(
                                        "Failed to delete segment (flow_id=%s, object_id=%s): %s",
                                        flow_id, segment.object_id, str(e)[:500]
                                    )
                                # Continue with other segments
                                break
                    
                    # If deletion failed after retries, check if segment still exists (idempotent delete)
                    if not success:
                        try:
                            # Check if segment still exists - if not, consider it successfully deleted
                            check_sql = f"""
                                SELECT COUNT(*) as count
                                FROM {segments_table}
                                WHERE flow_id = '{flow_id}' 
                                AND object_id = '{segment.object_id}' 
                                AND timerange_start = '{timerange_start}' 
                                AND timerange_end = '{timerange_end}'
                            """
                            result = await asyncio.to_thread(lambda: self.vast_db.execute_sql(check_sql))
                            
                            # Parse result to check count
                            count = 0
                            if isinstance(result, dict) and 'data' in result:
                                data = result['data']
                                if isinstance(data, dict):
                                    count_col = data.get('count', [])
                                    if count_col and len(count_col) > 0:
                                        count = count_col[0] or 0
                                elif isinstance(data, list) and len(data) > 0:
                                    count = data[0].get('count', 0) if isinstance(data[0], dict) else 0
                            elif isinstance(result, list) and len(result) > 0:
                                count = result[0].get('count', 0) if isinstance(result[0], dict) else 0
                            
                            if count == 0:
                                # Segment doesn't exist - consider it successfully deleted (idempotent)
                                logger.debug(
                                    "Segment already deleted (flow_id=%s, object_id=%s) - treating as success",
                                    flow_id, segment.object_id
                                )
                                deleted_count += 1
                        except Exception as check_error:
                            logger.debug(
                                "Failed to check if segment exists (flow_id=%s, object_id=%s): %s",
                                flow_id, segment.object_id, str(check_error)[:200]
                            )
                            # Continue - segment deletion failed but we'll try others
                
                logger.debug("Deleted %d segments for flow %s with timerange %s", deleted_count, flow_id, timerange)
                # Invalidate segments cache for this flow
                try:
                    from ..core.dependencies import get_cache_service
                    cache_service = get_cache_service()
                    await cache_service.delete(f"flow_segments:{flow_id}")
                    logger.debug(f"Invalidated segments cache for flow: {flow_id}")
                except Exception as e:
                    logger.debug(f"Failed to invalidate segments cache for flow {flow_id}: {e}")
                return deleted_count > 0
            else:
                # Delete all segments for the flow (no timerange filter)
                query = self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'")
                await asyncio.to_thread(lambda: query.execute())
                logger.debug("Deleted all segments for flow %s", flow_id)
                # Invalidate segments cache for this flow
                try:
                    from ..core.dependencies import get_cache_service
                    cache_service = get_cache_service()
                    await cache_service.delete(f"flow_segments:{flow_id}")
                    logger.debug(f"Invalidated segments cache for flow: {flow_id}")
                except Exception as e:
                    logger.debug(f"Failed to invalidate segments cache for flow {flow_id}: {e}")
                return True
        except Exception as e:
            logger.error("Failed to delete flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def _derive_content_type_from_flow(self, flow: Any) -> str:
        """
        Derive content-type (container MIME type) from Flow per TAMS 8.0 spec.
        AppNote 0018 requires content-type inheritance from Flow when storage is allocated.
        
        Priority:
        1. flow.container (authoritative source per TAMS spec)
        2. Heuristics based on format/codec
        """
        try:
            # First check flow.container (authoritative source per TAMS spec)
            flow_container = getattr(flow, 'container', None)
            if flow_container and isinstance(flow_container, str) and '/' in flow_container:
                return flow_container
            
            # Fallback to heuristics based on format/codec
            flow_format = getattr(flow, 'format', None)
            flow_codec = getattr(flow, 'codec', None)
            
            # Common TAMS container mappings based on format
            # Default to video/mp2t (MPEG-TS) for video flows as shown in TAMS examples
            if flow_format == "urn:x-nmos:format:video":
                # Video flows: typically MPEG-TS container
                return "video/mp2t"
            elif flow_format == "urn:x-nmos:format:audio":
                # Audio flows: can vary, default to MPEG-TS
                return "video/mp2t"  # Audio can also be in MPEG-TS
            elif flow_format == "urn:x-nmos:format:image":
                # Image flows: derive from codec if available
                if flow_codec:
                    # Codec like "image/jpeg" can serve as container for images
                    return flow_codec
                return "image/jpeg"  # Default for images
            elif flow_format == "urn:x-nmos:format:data":
                return "application/octet-stream"  # Default for data
            else:
                # Fallback: try to use codec if available, otherwise default
                if flow_codec and '/' in flow_codec:
                    return flow_codec
                return "video/mp2t"  # Conservative default per TAMS examples
        except Exception as e:
            logger.warning(f"Failed to derive content-type from flow: {e}")
            return "video/mp2t"  # Safe fallback
    
    async def create_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> Optional[FlowStorage]:
        """Create storage allocation for a flow"""
        try:
            import uuid
            import json
            
            # Get Flow to derive content-type (TAMS 8.0 AppNote 0018 requirement)
            from ..flows.service import FlowStorageService
            flow_service = FlowStorageService(self.vast_db, self.s3_client)
            flow = await flow_service.get_flow(flow_id)
            if not flow:
                raise HTTPException(status_code=404, detail=f"Flow {flow_id} not found")
            
            # Derive content-type from Flow per TAMS 8.0 spec
            content_type = self._derive_content_type_from_flow(flow)
            logger.debug(f"Derived content-type '{content_type}' from flow {flow_id} (format: {getattr(flow, 'format', None)}, codec: {getattr(flow, 'codec', None)})")
            
            # Get default storage backend
            storage_id = None
            if storage_request.storage_id:
                storage_id = storage_request.storage_id
            else:
                # Get default storage backend
                from ..storagebackends.service import StorageBackendService
                backend_service = StorageBackendService(self.vast_db, self.s3_client)
                backends = await backend_service.get_storage_backends()
                default_backend = next((b for b in backends if b.default_storage), None)
                if default_backend:
                    storage_id = default_backend.id
                    logger.debug(f"Using default storage backend: {storage_id}")
                else:
                    logger.warning("No default storage backend found, storage_id will be None")
            
            # Generate object IDs if not provided
            if storage_request.object_ids:
                object_ids = storage_request.object_ids
            else:
                limit = storage_request.limit or self.settings.flow_storage_default_limit
                object_ids = [str(uuid.uuid4()) for _ in range(limit)]
            
            # Validate that object IDs don't already exist
            for object_id in object_ids:
                existing_object = await self._get_object(object_id)
                if existing_object:
                    raise HTTPException(status_code=400, detail=f"Object ID {object_id} already exists")
            
            # Generate storage locations with presigned URLs
            media_objects = []
            for object_id in object_ids:
                # Generate TAMS-compliant storage path
                now = get_tams_timestamp()
                year = str(now.year)
                month = f"{now.month:02d}"
                date = f"{now.day:02d}"
                
                # Use TAMS path format: {tams_storage_path}/{year}/{month}/{date}/{object_id}
                # Normalize paths to avoid double slashes
                tams_path = self.settings.tams_storage_path.strip('/')
                relative_storage_path = f"{tams_path}/{year}/{month}/{date}/{object_id}"
                
                # Look up backend if storage_id is provided
                backend_info = None
                if storage_id:
                    try:
                        from ..storagebackends.service import StorageBackendService
                        backend_service = StorageBackendService(self.vast_db, self.s3_client)
                        backend = await backend_service.get_storage_backend(storage_id)
                        if backend:
                            backend_info = backend.model_dump()
                            # Include root_path in storage_path if backend has one
                            backend_root_path = backend.root_path
                            if backend_root_path:
                                backend_root_path = backend_root_path.strip('/')
                                storage_path = f"{backend_root_path}/{relative_storage_path}"
                            else:
                                storage_path = relative_storage_path
                        else:
                            storage_path = relative_storage_path
                    except Exception as e:
                        logger.warning(f"Failed to load storage backend {storage_id} for root_path: {e}")
                        storage_path = relative_storage_path
                else:
                    storage_path = relative_storage_path
                
                # Generate presigned URL for upload with content-type (TAMS 8.0 requirement)
                # Pass relative_storage_path (without root_path) since _generate_presigned_url
                # will use key_prefix from storage_backend if provided
                presigned_url = await self._generate_presigned_url(
                    key=relative_storage_path,
                    operation="put_object",
                    expiration=self.settings.s3_presigned_url_upload_timeout,
                    storage_backend=backend_info,
                    content_type=content_type
                )
                
                if not presigned_url:
                    raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL for object {object_id}")
                
                # Create MediaObject with content-type in put_url (TAMS 8.0 requirement)
                # Use model_validate with alias key for proper serialization
                put_url_data = {
                    "url": presigned_url,
                    "content-type": content_type,  # Required by TAMS 8.0 spec (using alias)
                    "headers": {}
                }
                media_object = MediaObject(
                    object_id=object_id,
                    put_url=HttpRequest.model_validate(put_url_data),
                    metadata={"storage_path": storage_path}  # Full path including root_path
                )
                
                media_objects.append(media_object)
                
                # Create Object record in database with storage_id, storage_path, and content_type in metadata
                from ..objects.models import Object
                from ..common.models import TimeRange
                object_metadata = {
                    "storage_path": storage_path,  # Full path including root_path
                    "content_type": content_type  # Store for GET URL generation (TAMS 8.0)
                }
                if storage_id:
                    object_metadata["storage_id"] = storage_id
                
                # Object requires timerange - use a default empty timerange for new objects
                # The actual timerange will be set when segments reference this object
                obj = Object(
                    id=object_id,
                    referenced_by_flows=[flow_id],
                    first_referenced_by_flow=flow_id,
                    timerange=TimeRange(value="0:0"),  # Default timerange for new objects
                    metadata=object_metadata,
                    created=now
                )
                await self._create_object(obj)
            
            # Create FlowStorage response
            flow_storage = FlowStorage(
                flow_id=flow_id,
                media_objects=media_objects
            )
            
            return flow_storage
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to create flow storage for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _get_object(self, object_id: str):
        """Get an object by ID"""
        try:
            # Run blocking database query in thread pool to avoid blocking event loop
            # This is especially important in dev mode with single worker
            result = await asyncio.to_thread(
                lambda: self.vast_db.query("objects").select("*").where(f"id = '{object_id}'").execute()
            )
            
            # Handle VAST query result format
            rows = []
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
                    try:
                        obj_data[col] = values[0] if isinstance(values, list) and values else values
                    except Exception:
                        obj_data[col] = None
            elif isinstance(result, list) and result:
                first = result[0]
                obj_data = dict(first) if isinstance(first, dict) else first
            else:
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
            logger.error("Failed to get object %s: %s", object_id, e)
            return None
    
    async def _create_object(self, obj):
        """Create an object"""
        try:
            now = get_tams_timestamp()
            obj.created = now
            
            object_data = obj.model_dump()
            
            # Convert timestamp fields to PyArrow format using centralized function
            from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
            object_data = prepare_data_for_pyarrow(object_data)
            
            self.vast_db.insert_record("objects", object_data)
            return True
        except Exception as e:
            logger.error("Failed to create object: %s", e)
            return False
    
    async def _generate_presigned_url(self, key: str, operation: str, expiration: int = 3600, storage_backend: Optional[Dict[str, Any]] = None, content_type: Optional[str] = None) -> Optional[str]:
        """Generate presigned URL; prefer backend-specific endpoint/credentials if provided.
        
        Args:
            key: S3 object key
            operation: S3 operation (get_object, put_object)
            expiration: URL expiration in seconds
            storage_backend: Optional backend-specific config
            content_type: MIME type for PUT requests (TAMS 8.0 requirement - must match Flow)
        """
        try:
            import inspect
            import asyncio
            http_method = 'GET' if operation.lower() in ('get', 'get_object') else 'PUT'
            # Use provided content_type or fallback (TAMS 8.0 requires content-type for PUT)
            final_content_type = content_type or 'application/octet-stream'
            
            # Only use storage_backend if it has valid credentials (both access_key and secret_key)
            access_key = storage_backend.get('access_key') if storage_backend else None
            secret_key = storage_backend.get('secret_key') if storage_backend else None
            has_valid_credentials = (
                access_key and secret_key and 
                isinstance(access_key, str) and isinstance(secret_key, str) and
                access_key.strip() and secret_key.strip()
            )
            
            if storage_backend and has_valid_credentials:
                from vasts3 import S3Client, S3Config
                
                # Use backend-specific values when available, fallback to settings
                backend_root_path = storage_backend.get('root_path') or getattr(self.settings, 's3_root_path', None)
                key_prefix = backend_root_path.strip('/') if backend_root_path else None
                
                cfg = S3Config(
                    endpoint_url=storage_backend.get('endpoint_url'),
                    bucket_name=storage_backend.get('bucket_name') or self.settings.s3_bucket_name,
                    access_key=access_key,
                    secret_key=secret_key,
                    region=storage_backend.get('region') or self.settings.s3_region,
                    use_ssl=storage_backend.get('use_ssl') if storage_backend.get('use_ssl') is not None else self.settings.s3_use_ssl,
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
                    # Note: response_content_type and response_content_disposition are not included
                    # because VAST S3 backend does not support these parameters in presigned URLs
                }
                # Remove None values
                candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
                kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
                # Run synchronous generate_presigned_url in thread pool to avoid blocking
                return await asyncio.to_thread(tmp_client.generate_presigned_url, **kwargs)
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
                # Note: response_content_type and response_content_disposition are not included
                # because VAST S3 backend does not support these parameters in presigned URLs
            }
            # Remove None values
            candidate_kwargs = {k: v for k, v in candidate_kwargs.items() if v is not None}
            kwargs = {k: v for k, v in candidate_kwargs.items() if k in supported}
            # Run synchronous generate_presigned_url in thread pool to avoid blocking
            return await asyncio.to_thread(self.s3_client.generate_presigned_url, **kwargs)
        except Exception as e:
            logger.error("Failed to generate presigned URL: %s", e)
            return None
    
    
    async def get_segments_with_flow_and_object_details(self, flow_id: str) -> List[Dict[str, Any]]:
        """Get segments with flow and object details using join query"""
        try:
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            objects_table = self.vast_db.get_qualified_table_name("objects")
            
            sql = f"""
                SELECT 
                    seg.id,
                    seg.flow_id,
                    seg.object_id,
                    seg.timerange_start,
                    seg.timerange_end,
                    seg.ts_offset,
                    seg.last_duration,
                    seg.sample_offset,
                    seg.sample_count,
                    seg.get_urls,
                    seg.key_frame_count,
                    seg.created,
                    f.label as flow_label,
                    f.format as flow_format,
                    f.description as flow_description,
                    o.size as object_size,
                    o.first_referenced_by_flow
                FROM {segments_table} seg
                JOIN {flows_table} f ON seg.flow_id = f.id
                JOIN {objects_table} o ON seg.object_id = o.id
                WHERE seg.flow_id = '{flow_id}'
                ORDER BY seg.timerange_start
            """
            
            result = await asyncio.to_thread(lambda: self.vast_db.execute_sql(sql))
            if result and 'data' in result:
                segments = []
                for row in result['data']:
                    segments.append({
                        "id": row[0],
                        "flow_id": row[1],
                        "object_id": row[2],
                        "timerange_start": row[3],
                        "timerange_end": row[4],
                        "ts_offset": row[5],
                        "last_duration": row[6],
                        "sample_offset": row[7],
                        "sample_count": row[8],
                        "get_urls": row[9],
                        "key_frame_count": row[10],
                        "created": row[11],
                        "flow": {
                            "id": row[1],
                            "label": row[12],
                            "format": row[13],
                            "description": row[14]
                        },
                        "object": {
                            "id": row[2],
                            "size": row[15],
                            "first_referenced_by_flow": row[16]
                        }
                    })
                return segments
            return []
        except Exception as e:
            logger.error("Failed to get segments with flow and object details for %s: %s", flow_id, e)
            return []
    
    async def get_segment_analytics(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get segment analytics using join queries"""
        try:
            segments_table = self.vast_db.get_qualified_table_name("segments")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            objects_table = self.vast_db.get_qualified_table_name("objects")
            
            where_clause = f"WHERE seg.flow_id = '{flow_id}'" if flow_id else ""
            
            sql = f"""
                SELECT 
                    COUNT(seg.id) as total_segments,
                    COALESCE(SUM(seg.sample_count), 0) as total_samples,
                    COALESCE(SUM(o.size), 0) as total_size_bytes,
                    COUNT(DISTINCT seg.flow_id) as flow_count,
                    COUNT(DISTINCT seg.object_id) as object_count,
                    AVG(seg.sample_count) as avg_samples_per_segment,
                    MIN(seg.timerange_start) as earliest_timerange,
                    MAX(seg.timerange_end) as latest_timerange
                FROM {segments_table} seg
                JOIN {flows_table} f ON seg.flow_id = f.id
                JOIN {objects_table} o ON seg.object_id = o.id
                {where_clause}
            """
            
            result = await asyncio.to_thread(lambda: self.vast_db.execute_sql(sql))
            if result and 'data' in result and len(result['data']) > 0:
                row = result['data'][0]
                return {
                    "total_segments": row[0] if row[0] is not None else 0,
                    "total_samples": row[1] if row[1] is not None else 0,
                    "total_size_bytes": row[2] if row[2] is not None else 0,
                    "flow_count": row[3] if row[3] is not None else 0,
                    "object_count": row[4] if row[4] is not None else 0,
                    "avg_samples_per_segment": row[5] if row[5] is not None else 0,
                    "earliest_timerange": row[6],
                    "latest_timerange": row[7],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "total_segments": 0,
                    "total_samples": 0,
                    "total_size_bytes": 0,
                    "flow_count": 0,
                    "object_count": 0,
                    "avg_samples_per_segment": 0,
                    "earliest_timerange": None,
                    "latest_timerange": None,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error("Failed to get segment analytics: %s", e)
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

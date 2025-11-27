"""
Flow Storage Service

This module handles all flow-related storage operations including
CRUD operations, filtering, and flow management.
"""

import logging
import time
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import (
    is_timestamp_field,
    get_tams_timestamp, 
    get_timeline_synchronizer,
    prepare_data_for_pyarrow,
    prepare_data_for_sql
)
from .models import Flow, VideoFlow, AudioFlow, ImageFlow, DataFlow, MultiFlow
from .bitrate_calculator import BitRateCalculator
from ..common.filters import FlowFilters, FlowDetailFilters
from ..sources.models import Source
from ..core.telemetry import telemetry_manager

logger = logging.getLogger(__name__)


def _get_flow_class(format_str: str):
    """Get the appropriate flow class based on format"""
    if format_str == "urn:x-nmos:format:video":
        return VideoFlow
    elif format_str == "urn:x-nmos:format:audio":
        return AudioFlow
    elif format_str == "urn:x-nmos:format:image":
        return ImageFlow
    elif format_str == "urn:x-nmos:format:data":
        return DataFlow
    elif format_str == "urn:x-nmos:format:multi":
        return MultiFlow
    else:
        # Default to VideoFlow for unknown formats
        return VideoFlow


class FlowStorageService:
    """Handles flow-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
        from ..common.tags.service import TagStorageService
        self.tag_service = TagStorageService(vast_db, s3_client)
    
    async def _fetch_and_add_tags(self, flow_data: dict, flow_id: str):
        """Helper method to fetch tags from tags table and add to flow_data"""
        try:
            tags = await self.tag_service.get_entity_tags("flow", flow_id)
            if tags:
                # Tags object is already a Tags instance, use it directly
                logger.debug(f"Fetched tags for flow {flow_id}: {tags.root if hasattr(tags, 'root') else tags}")
                flow_data['tags'] = tags
            else:
                logger.debug(f"No tags found for flow {flow_id}")
                flow_data['tags'] = None
        except Exception as e:
            logger.warning(f"Failed to fetch tags for flow {flow_id}: {e}", exc_info=True)
            flow_data['tags'] = None
    
    def _ensure_required_flow_fields(self, flow_data: Dict[str, Any], flow_class) -> Dict[str, Any]:
        """
        Ensure required fields are present in flow_data before creating flow object.
        Provides defaults for missing required fields to handle incomplete database records.
        """
        # Ensure codec is present for flows that require it
        if flow_class in [VideoFlow, AudioFlow, ImageFlow, DataFlow]:
            if 'codec' not in flow_data or flow_data.get('codec') is None:
                # Provide default codec based on flow type
                if flow_class == VideoFlow:
                    flow_data['codec'] = 'video/mp4'
                elif flow_class == AudioFlow:
                    flow_data['codec'] = 'audio/mp4'
                elif flow_class == ImageFlow:
                    flow_data['codec'] = 'image/jpeg'
                elif flow_class == DataFlow:
                    flow_data['codec'] = 'application/octet-stream'
        
        # Ensure essence_parameters is present and complete
        if flow_class == VideoFlow:
            if 'essence_parameters' not in flow_data or not flow_data.get('essence_parameters'):
                flow_data['essence_parameters'] = {}
            ep = flow_data['essence_parameters']
            if not isinstance(ep, dict):
                ep = {}
                flow_data['essence_parameters'] = ep
            # Ensure required video essence parameters
            if 'frame_width' not in ep or ep.get('frame_width') is None:
                ep['frame_width'] = 1920  # Default HD width
            if 'frame_height' not in ep or ep.get('frame_height') is None:
                ep['frame_height'] = 1080  # Default HD height
            if 'vfr' not in ep:
                ep['vfr'] = False
            if not ep.get('vfr') and 'frame_rate' not in ep:
                # Default 25fps - SegmentDuration requires numerator and denominator
                ep['frame_rate'] = {'numerator': 25, 'denominator': 1}
        
        elif flow_class == AudioFlow:
            if 'essence_parameters' not in flow_data or not flow_data.get('essence_parameters'):
                flow_data['essence_parameters'] = {}
            ep = flow_data['essence_parameters']
            if not isinstance(ep, dict):
                ep = {}
                flow_data['essence_parameters'] = ep
            # Ensure required audio essence parameters
            if 'sample_rate' not in ep or ep.get('sample_rate') is None:
                ep['sample_rate'] = 48000  # Default 48kHz
            if 'channels' not in ep or ep.get('channels') is None:
                ep['channels'] = 2  # Default stereo
        
        elif flow_class == ImageFlow:
            if 'essence_parameters' not in flow_data or not flow_data.get('essence_parameters'):
                flow_data['essence_parameters'] = {}
            ep = flow_data['essence_parameters']
            if not isinstance(ep, dict):
                ep = {}
                flow_data['essence_parameters'] = ep
            # Ensure required image essence parameters
            if 'frame_width' not in ep or ep.get('frame_width') is None:
                ep['frame_width'] = 1920
            if 'frame_height' not in ep or ep.get('frame_height') is None:
                ep['frame_height'] = 1080
        
        elif flow_class == DataFlow:
            if 'essence_parameters' not in flow_data or not flow_data.get('essence_parameters'):
                flow_data['essence_parameters'] = {}
            ep = flow_data['essence_parameters']
            if not isinstance(ep, dict):
                ep = {}
                flow_data['essence_parameters'] = ep
        
        return flow_data
    
    async def get_flows(self, filters: FlowFilters) -> List[Flow]:
        """Get flows with filtering (TAMS 8.0 with tag filtering)"""
        total_start = time.time()
        query_start = time.time()
        json_parse_start = 0
        json_parse_duration = 0
        
        # Try cache first (only for simple queries without complex filters)
        from ..core.dependencies import get_cache_service
        cache_service = get_cache_service()
        
        # Check if filters are being used
        has_filters = bool(
            filters.source_id or filters.label or filters.format or filters.codec or
            filters.frame_width or filters.frame_height or filters.tag_filters or
            filters.tag_exists_filters
        )
        
        # Only cache simple queries (no filters or just source_id filter)
        # Complex filters (tag filters, frame dimensions, etc.) are not cached
        use_cache = not has_filters or (filters.source_id and not (
            filters.label or filters.format or filters.codec or
            filters.frame_width or filters.frame_height or filters.tag_filters or
            filters.tag_exists_filters
        ))
        
        if use_cache:
            # Build cache key based on filters
            if filters.source_id:
                cache_key = f"flows:source:{filters.source_id}"
            else:
                cache_key = "flows:list:all"
            
            cached = await cache_service.get(cache_key)
            if cached:
                try:
                    # Reconstruct Flow objects from cached data
                    # Note: Tags are not cached, fetch them fresh for each flow
                    flows = []
                    for flow_data in cached:
                        flow_id = flow_data.get('id')
                        if flow_id:
                            await self._fetch_and_add_tags(flow_data, flow_id)
                        flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                        flow_data = self._ensure_required_flow_fields(flow_data, flow_class)
                        flows.append(flow_class(**flow_data))
                    logger.info(f"Cache hit: {cache_key} ({len(flows)} flows)")
                    return flows
                except Exception as e:
                    logger.debug(f"Failed to deserialize cached flows for {cache_key}: {e}")
                    # Fall through to DB query
        
        try:
            
            # Build query using vaststore
            query = self.vast_db.query("flows").select("*")
            
            # Add standard filters
            if filters.source_id:
                query = query.where(f"source_id = '{filters.source_id}'")
            if filters.label:
                query = query.where(f"label = '{filters.label}'")
            if filters.format:
                query = query.where(f"format = '{filters.format}'")
            if filters.codec:
                query = query.where(f"codec = '{filters.codec}'")
            # Filter by essence_parameters (frame_width, frame_height are in essence_parameters JSON)
            # Cast JSON_EXTRACT to INTEGER for comparison
            if filters.frame_width:
                query = query.where(f"CAST(JSON_EXTRACT(essence_parameters, '$.frame_width') AS INTEGER) = {filters.frame_width}")
            if filters.frame_height:
                query = query.where(f"CAST(JSON_EXTRACT(essence_parameters, '$.frame_height') AS INTEGER) = {filters.frame_height}")
            
            # TAMS 8.0: Add tag filters if present
            if filters.tag_filters:
                for tag_name, tag_values in filters.tag_filters.items():
                    # tag_values can be string or list
                    if isinstance(tag_values, list):
                        # "OR" query: tag value matches at least one in the list
                        conditions = []
                        for val in tag_values:
                            conditions.append(f"JSON_CONTAINS(tags, '\"{val}\"', '$.\"{tag_name}\"') OR JSON_CONTAINS(tags, '[\"{val}\"]', '$.\"{tag_name}\"')")
                        tag_filter = " OR ".join(conditions)
                        query = query.where(f"({tag_filter})")
                    else:
                        # Single string value
                        query = query.where(f"(JSON_EXTRACT(tags, '$.\"{tag_name}\"') = '\"{tag_values}\"' OR JSON_CONTAINS(JSON_EXTRACT(tags, '$.\"{tag_name}\"'), '\"{tag_values}\"'))")
            
            # TAMS 8.0: Add tag_exists filters if present
            if filters.tag_exists_filters:
                for tag_name, exists in filters.tag_exists_filters.items():
                    if exists:
                        query = query.where(f"JSON_EXTRACT(tags, '$.\"{tag_name}\"') IS NOT NULL")
                    else:
                        query = query.where(f"JSON_EXTRACT(tags, '$.\"{tag_name}\"') IS NULL")
            
            # Add limit
            if filters.limit:
                query = query.limit(filters.limit)
            
            result = query.execute()
            query_duration = time.time() - query_start
            json_parse_start = time.time()
            
            # Convert to Flow objects
            flows = []
            # VAST returns a dict with 'data' field containing column arrays
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        flow_data = {}
                        for column, values in data.items():
                            if column != '$row_id':  # Skip internal row IDs
                                value = values[i] if i < len(values) else None
                                # Parse JSON fields (skip flow_collection - it's computed on-demand in get_flow() only)
                                if column in ['essence_parameters', 'tags'] and isinstance(value, str):
                                    try:
                                        import json
                                        parsed = json.loads(value)
                                        # Handle empty JSON strings like '{}' or '[]'
                                        if parsed == {} or parsed == []:
                                            flow_data[column] = None if column == 'tags' else parsed
                                        else:
                                            flow_data[column] = parsed
                                    except (json.JSONDecodeError, TypeError) as e:
                                        # For essence_parameters, invalid JSON should cause validation error
                                        if column == 'essence_parameters':
                                            raise HTTPException(
                                                status_code=500, 
                                                detail=f"Invalid JSON in essence_parameters for flow {flow_data.get('id', 'unknown')}: {str(e)}"
                                            )
                                        # For tags, set to None on parse error
                                        if column == 'tags':
                                            flow_data[column] = None
                                else:
                                    flow_data[column] = value
                        
                        # flow_collection is computed on-demand in get_flow() only
                        # For list operations, set it to None to avoid expensive JSON parsing
                        flow_data['flow_collection'] = None
                        
                        # Fetch tags for this flow
                        flow_id = flow_data.get('id')
                        if flow_id:
                            await self._fetch_and_add_tags(flow_data, flow_id)
                        
                        # Get the appropriate flow class based on format
                        # Safety check: ensure flow_data is a dict
                        if not isinstance(flow_data, dict):
                            logger.warning(f"flow_data is not a dict in column array branch: {type(flow_data)}, skipping")
                            continue
                        flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                        # Ensure required fields are present before creating flow object
                        flow_data = self._ensure_required_flow_fields(flow_data, flow_class)
                        flows.append(flow_class(**flow_data))
                elif isinstance(data, list):
                    # If data is a list, iterate directly
                    for row in data:
                        # Ensure flow_data is a dictionary
                        if isinstance(row, dict):
                            flow_data = row.copy()
                        elif hasattr(row, '__iter__') and not isinstance(row, str):
                            flow_data = dict(row)
                        else:
                            # Skip non-dict rows (including strings)
                            logger.debug(f"Skipping non-dict row in get_flows list branch: {type(row)}")
                            continue
                        
                        # Additional safety check: ensure flow_data is still a dict
                        if not isinstance(flow_data, dict):
                            logger.warning(f"flow_data is not a dict after conversion in list branch: {type(flow_data)}, skipping")
                            continue
                        
                        # Parse JSON fields (skip flow_collection - it's computed on-demand in get_flow() only)
                        for field in ['essence_parameters', 'tags']:
                            if field in flow_data and isinstance(flow_data[field], str):
                                try:
                                    import json
                                    parsed = json.loads(flow_data[field])
                                    # Handle empty JSON strings like '{}' or '[]'
                                    if parsed == {} or parsed == []:
                                        flow_data[field] = None if field == 'tags' else parsed
                                    else:
                                        flow_data[field] = parsed
                                except (json.JSONDecodeError, TypeError) as e:
                                    # For essence_parameters, invalid JSON should cause validation error
                                    if field == 'essence_parameters':
                                        raise HTTPException(
                                            status_code=500, 
                                            detail=f"Invalid JSON in essence_parameters for flow {flow_data.get('id', 'unknown')}: {str(e)}"
                                        )
                                    # For tags, set to None on parse error
                                    if field == 'tags':
                                        flow_data[field] = None
                        
                        # flow_collection is computed on-demand in get_flow() only
                        # For list operations, set it to None to avoid expensive JSON parsing
                        flow_data['flow_collection'] = None
                        
                        # Fetch tags for this flow
                        flow_id = flow_data.get('id')
                        if flow_id:
                            await self._fetch_and_add_tags(flow_data, flow_id)
                        
                        # Get the appropriate flow class based on format
                        # Additional safety check before calling .get()
                        if not isinstance(flow_data, dict):
                            logger.error(f"flow_data is not a dict before _get_flow_class in list branch: {type(flow_data)}")
                            continue
                        flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                        # Ensure required fields are present before creating flow object
                        flow_data = self._ensure_required_flow_fields(flow_data, flow_class)
                        flows.append(flow_class(**flow_data))
            else:
                # Fallback for direct list results
                for row in result:
                    # Ensure flow_data is a dictionary
                    if isinstance(row, dict):
                        flow_data = row.copy()
                    elif hasattr(row, '__iter__') and not isinstance(row, str):
                        flow_data = dict(row)
                    else:
                        # Skip non-dict rows (including strings)
                        logger.debug(f"Skipping non-dict row in get_flows: {type(row)}")
                        continue
                    
                    # Additional safety check: ensure flow_data is still a dict
                    if not isinstance(flow_data, dict):
                        logger.warning(f"flow_data is not a dict after conversion: {type(flow_data)}, skipping")
                        continue
                    
                    # Parse JSON fields (skip flow_collection - it's computed on-demand in get_flow() only)
                    for field in ['essence_parameters', 'tags']:
                        if field in flow_data and isinstance(flow_data[field], str):
                            try:
                                import json
                                parsed = json.loads(flow_data[field])
                                # Handle empty JSON strings like '{}' or '[]'
                                if parsed == {} or parsed == []:
                                    flow_data[field] = None if field == 'tags' else parsed
                                else:
                                    flow_data[field] = parsed
                            except (json.JSONDecodeError, TypeError):
                                # If parsing fails, set to None for tags, keep as-is for essence_parameters
                                if field == 'tags':
                                    flow_data[field] = None
                        
                    # flow_collection is computed on-demand in get_flow() only
                    # For list operations, set it to None to avoid expensive JSON parsing
                    flow_data['flow_collection'] = None
                    
                    # Fetch tags for this flow
                    flow_id = flow_data.get('id')
                    if flow_id:
                        await self._fetch_and_add_tags(flow_data, flow_id)
                    
                    # Get the appropriate flow class based on format
                    # Additional safety check before calling .get()
                    if not isinstance(flow_data, dict):
                        logger.error(f"flow_data is not a dict before _get_flow_class: {type(flow_data)}")
                        continue
                    flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
                    # Ensure required fields are present before creating flow object
                    flow_data = self._ensure_required_flow_fields(flow_data, flow_class)
                    flows.append(flow_class(**flow_data))
            
            json_parse_duration = time.time() - json_parse_start
            total_duration = time.time() - total_start
            
            # Record telemetry metrics
            telemetry_manager.record_list_performance(
                entity_type="flows",
                query_duration=query_duration,
                json_parse_duration=json_parse_duration,
                total_duration=total_duration,
                record_count=len(flows),
                has_filters=has_filters
            )
            
            # Cache the result (only for simple queries)
            if use_cache:
                try:
                    # Convert flows to dict for caching
                    flows_dict = [flow.model_dump() for flow in flows]
                    await cache_service.set(cache_key, flows_dict, ttl=300)  # 5 minutes TTL
                    logger.info(f"Cache set: {cache_key} ({len(flows)} flows)")
                except Exception as e:
                    logger.debug(f"Failed to cache flows for {cache_key}: {e}")
            
            return flows
        except Exception as e:
            import traceback
            total_duration = time.time() - total_start if 'total_start' in locals() else 0
            logger.error("Failed to get flows (duration=%.3fs): %s\n%s", total_duration, e, traceback.format_exc())
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_flow(self, flow_id: str, filters: Optional[FlowDetailFilters] = None) -> Optional[Flow]:
        """Get a specific flow by ID with optional timerange handling per TAMS 8.0 spec"""
        # Try cache first (if no filters that require DB calculation)
        from ..core.dependencies import get_cache_service
        cache_service = get_cache_service()
        
        # Only use cache if no complex filters that require DB calculation
        use_cache = filters is None or (not filters.include_timerange and not filters.timerange)
        
        if use_cache:
            cache_key = f"flow:{flow_id}"
            cached = await cache_service.get(cache_key)
            if cached:
                try:
                    # Always fetch tags even for cached flows (tags are dynamic)
                    await self._fetch_and_add_tags(cached, flow_id)
                    # Reconstruct Flow object from cached data with updated tags
                    from ..flows.models import Flow
                    # Determine flow class from format
                    format_urn = cached.get('format', '')
                    if 'video' in format_urn.lower():
                        from ..flows.models import VideoFlow
                        return VideoFlow(**cached)
                    elif 'audio' in format_urn.lower():
                        from ..flows.models import AudioFlow
                        return AudioFlow(**cached)
                    elif 'image' in format_urn.lower():
                        from ..flows.models import ImageFlow
                        return ImageFlow(**cached)
                    elif 'data' in format_urn.lower():
                        from ..flows.models import DataFlow
                        return DataFlow(**cached)
                    else:
                        return Flow(**cached)
                except Exception as e:
                    logger.debug(f"Failed to deserialize cached flow {flow_id}: {e}")
                    # Fall through to DB query
        
        try:
            result = self.vast_db.query("flows").select("*").where(f"id = '{flow_id}'").execute()
            
            # Handle VAST query result format
            flow_data = None
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        return None
                    
                    # Get the first row
                    flow_data = {}
                    for column, values in data.items():
                        if column != '$row_id':  # Skip internal row IDs
                            value = values[0] if len(values) > 0 else None
                            # Parse JSON fields
                            if column in ['essence_parameters', 'tags', 'flow_collection'] and isinstance(value, str):
                                try:
                                    import json
                                    parsed = json.loads(value)
                                    # Handle empty JSON strings like '{}' or '[]'
                                    if parsed == {} or parsed == []:
                                        flow_data[column] = None if column == 'tags' else parsed
                                    else:
                                        flow_data[column] = parsed
                                except (json.JSONDecodeError, TypeError):
                                    # If parsing fails, set to None for tags, keep as-is for essence_parameters and flow_collection
                                    if column == 'tags':
                                        flow_data[column] = None
                                    else:
                                        flow_data[column] = value
                            else:
                                flow_data[column] = value
                elif isinstance(data, list):
                    if not data:
                        return None
                    flow_data = dict(data[0]) if hasattr(data[0], '__iter__') and not isinstance(data[0], str) else data[0]
                    # Parse JSON fields
                    for field in ['essence_parameters', 'tags', 'flow_collection']:
                        if field in flow_data and isinstance(flow_data[field], str):
                            try:
                                import json
                                parsed = json.loads(flow_data[field])
                                # Handle empty JSON strings like '{}' or '[]'
                                if parsed == {} or parsed == []:
                                    flow_data[field] = None if field == 'tags' else parsed
                                else:
                                    flow_data[field] = parsed
                            except (json.JSONDecodeError, TypeError):
                                # If parsing fails, set to None for tags, keep as-is for essence_parameters and flow_collection
                                if field == 'tags':
                                    flow_data[field] = None
                                pass
            else:
                if not result or len(result) == 0:
                    return None
                flow_data = dict(result[0]) if hasattr(result[0], '__iter__') and not isinstance(result[0], str) else result[0]
                # Parse JSON fields
                for field in ['essence_parameters', 'tags', 'flow_collection']:
                    if field in flow_data and isinstance(flow_data[field], str):
                        try:
                            import json
                            parsed = json.loads(flow_data[field])
                            # Handle empty JSON strings like '{}' or '[]'
                            if parsed == {} or parsed == []:
                                flow_data[field] = None if field == 'tags' else parsed
                            else:
                                flow_data[field] = parsed
                        except (json.JSONDecodeError, TypeError):
                            # If parsing fails, set to None for tags, keep as-is for essence_parameters and flow_collection
                            if field == 'tags':
                                flow_data[field] = None
                            pass
            
            if not flow_data:
                return None
            
            # Handle timerange calculation and filtering per TAMS 8.0 spec
            if filters:
                calculated_timerange = None
                
                # Calculate Flow timerange from segments if include_timerange=true OR timerange filter is provided
                # Per TAMS 8.0 spec: timerange "limits the returned available Segment timerange"
                # So we need to calculate it first if timerange filter is provided
                if filters.include_timerange or filters.timerange:
                    calculated_timerange = await self._calculate_flow_timerange_from_segments(flow_id)
                    if calculated_timerange:
                        from ..common.models import TimeRange
                        flow_data['timerange'] = TimeRange(value=calculated_timerange)
                
                # Apply timerange limiting if timerange filter is provided
                if filters.timerange:
                    if calculated_timerange:
                        # Limit the calculated timerange to the requested range
                        limited_timerange = self._limit_timerange(calculated_timerange, filters.timerange)
                        if limited_timerange:
                            from ..common.models import TimeRange
                            flow_data['timerange'] = TimeRange(value=limited_timerange)
                        else:
                            # No overlap - remove timerange (flow has no content in requested range)
                            flow_data.pop('timerange', None)
                    else:
                        # No segments found - timerange should be None/absent
                        flow_data.pop('timerange', None)
                elif filters.include_timerange and not calculated_timerange:
                    # include_timerange=true but no segments found - timerange should be None/absent
                    flow_data.pop('timerange', None)
            
            # Convert flow_collection from list to FlowCollection object if present
            if 'flow_collection' in flow_data and flow_data['flow_collection'] is not None:
                from ..common.models import FlowCollection
                import json
                # If it's still a string, parse it first
                if isinstance(flow_data['flow_collection'], str):
                    try:
                        flow_data['flow_collection'] = json.loads(flow_data['flow_collection'])
                    except (json.JSONDecodeError, TypeError):
                        flow_data['flow_collection'] = None
                # Filter out non-existent flows from flow_collection
                if isinstance(flow_data['flow_collection'], list):
                    valid_items = []
                    for item in flow_data['flow_collection']:
                        if isinstance(item, dict) and 'id' in item:
                            referenced_flow_id = item.get('id')
                            # Check if the referenced flow exists
                            try:
                                referenced_flow = await self.get_flow(referenced_flow_id)
                                if referenced_flow:
                                    valid_items.append(item)
                                else:
                                    logger.debug(f"Flow {flow_data.get('id', 'unknown')}'s flow_collection references non-existent flow {referenced_flow_id}, filtering out")
                            except Exception:
                                # If we can't check, filter it out to be safe
                                logger.debug(f"Could not verify flow {referenced_flow_id} in flow_collection, filtering out")
                        else:
                            # Invalid item format, skip it
                            logger.debug(f"Invalid flow_collection item format: {item}")
                    # Update flow_collection with filtered items (or None if empty)
                    if valid_items:
                        flow_data['flow_collection'] = FlowCollection(valid_items)
                    else:
                        flow_data['flow_collection'] = None
                elif flow_data['flow_collection'] is not None:
                    # If it's not a list and not None, set to None (invalid format)
                    flow_data['flow_collection'] = None
            
            # Fetch tags from tags table and include in response
            await self._fetch_and_add_tags(flow_data, flow_id)
            
            # Get the appropriate flow class based on format
            flow_class = _get_flow_class(flow_data.get('format', 'urn:x-nmos:format:video'))
            # Ensure required fields are present before creating flow object
            flow_data = self._ensure_required_flow_fields(flow_data, flow_class)
            flow = flow_class(**flow_data)
            
            # Store in cache (only if we didn't use cache and no complex filters)
            if use_cache:
                cache_key = f"flow:{flow_id}"
                try:
                    # Convert flow to dict for caching
                    flow_dict = flow.model_dump() if hasattr(flow, 'model_dump') else flow.dict() if hasattr(flow, 'dict') else flow._data if hasattr(flow, '_data') else None
                    if flow_dict:
                        await cache_service.set(cache_key, flow_dict)
                except Exception as e:
                    logger.debug(f"Failed to cache flow {flow_id}: {e}")
            
            return flow
        except Exception as e:
            logger.error("Failed to get flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _calculate_flow_timerange_from_segments(self, flow_id: str) -> Optional[str]:
        """
        Calculate Flow timerange from its segments per TAMS 8.0 spec.
        
        The Flow timerange is the union of all segment timeranges:
        - Start: earliest segment timerange start
        - End: latest segment timerange end
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            Timerange string in TAMS format, or None if no segments found
        """
        try:
            from ..segments.service import SegmentStorageService
            from ..core.config import get_settings
            from ..core.timerange_utils import parse_tams_timerange
            
            segment_service = SegmentStorageService(self.vast_db, self.s3_client, get_settings())
            segments = await segment_service.get_flow_segments(flow_id)
            
            if not segments:
                logger.debug(f"No segments found for flow {flow_id}, cannot calculate timerange")
                return None
            
            # Find earliest start and latest end from all segments
            earliest_start = None
            latest_end = None
            
            for segment in segments:
                if segment.timerange and segment.timerange.value:
                    try:
                        seg_start, seg_end = parse_tams_timerange(segment.timerange.value)
                        if seg_start is not None:
                            if earliest_start is None or seg_start < earliest_start:
                                earliest_start = seg_start
                        if seg_end is not None and seg_end != float('inf'):
                            if latest_end is None or seg_end > latest_end:
                                latest_end = seg_end
                    except Exception as e:
                        logger.debug(f"Failed to parse segment timerange {segment.timerange.value}: {e}")
                        continue
            
            if earliest_start is None or latest_end is None:
                logger.debug(f"Could not determine timerange bounds for flow {flow_id}")
                return None
            
            # Format as TAMS timerange: [start_end)
            # Convert seconds to TAMS format (seconds:nanoseconds)
            start_sec = int(earliest_start)
            start_nano = int((earliest_start - start_sec) * 1e9)
            end_sec = int(latest_end)
            end_nano = int((latest_end - end_sec) * 1e9)
            
            timerange_str = f"[{start_sec}:{start_nano}_{end_sec}:{end_nano})"
            logger.debug(f"Calculated timerange for flow {flow_id}: {timerange_str}")
            return timerange_str
            
        except Exception as e:
            logger.warning(f"Failed to calculate timerange for flow {flow_id}: {e}")
            return None
    
    def _limit_timerange(self, flow_timerange: str, limit_timerange: str) -> Optional[str]:
        """
        Limit/constrain a Flow timerange to the specified timerange per TAMS 8.0 spec.
        
        Args:
            flow_timerange: Current Flow timerange
            limit_timerange: Timerange to limit to
            
        Returns:
            Limited timerange string, or None if no overlap
        """
        try:
            from ..core.timerange_utils import parse_tams_timerange, timeranges_overlap
            
            # Check if timeranges overlap
            if not timeranges_overlap(flow_timerange, limit_timerange):
                logger.debug(f"Flow timerange {flow_timerange} does not overlap with limit {limit_timerange}")
                return None
            
            # Parse both timeranges
            flow_start, flow_end = parse_tams_timerange(flow_timerange)
            limit_start, limit_end = parse_tams_timerange(limit_timerange)
            
            # Calculate intersection
            # Start is the maximum of the two starts
            # End is the minimum of the two ends
            limited_start = max(flow_start, limit_start) if limit_start is not None else flow_start
            limited_end = min(flow_end, limit_end) if limit_end != float('inf') else flow_end
            
            if limited_start >= limited_end:
                return None
            
            # Format as TAMS timerange
            start_sec = int(limited_start)
            start_nano = int((limited_start - start_sec) * 1e9)
            end_sec = int(limited_end)
            end_nano = int((limited_end - end_sec) * 1e9)
            
            limited_timerange_str = f"[{start_sec}:{start_nano}_{end_sec}:{end_nano})"
            logger.debug(f"Limited timerange from {flow_timerange} to {limited_timerange_str}")
            return limited_timerange_str
            
        except Exception as e:
            logger.warning(f"Failed to limit timerange: {e}")
            return None
    
    async def _calculate_and_update_bit_rates(self, flow_id: str) -> None:
        """
        Calculate and update bit rates for a flow from its segments
        
        Args:
            flow_id: Flow identifier
        """
        try:
            # Get flow to check if bit rates need calculation
            flow = await self.get_flow(flow_id, filters=None)
            if not flow:
                return
            
            # Check if bit rates are already set
            if flow.avg_bit_rate and flow.max_bit_rate:
                logger.debug(f"Bit rates already set for flow {flow_id}")
                return
            
            # Get flow segments
            from ..segments.service import SegmentStorageService
            from ..core.config import get_settings
            segment_service = SegmentStorageService(self.vast_db, self.s3_client, get_settings())
            
            segments = await segment_service.get_flow_segments(flow_id)
            
            if not segments:
                logger.debug(f"No segments found for flow {flow_id}, skipping bit rate calculation")
                return
            
            # Calculate bit rates
            calculator = BitRateCalculator()
            
            # Get target segment duration from flow
            target_duration = 1.0  # Default 1 second
            if flow.segment_duration:
                target_duration = flow.segment_duration.numerator / flow.segment_duration.denominator
            
            # Calculate bit rates
            avg_bit_rate = await calculator.calculate_avg_bit_rate(segments)
            max_bit_rate = await calculator.calculate_max_bit_rate(segments, target_duration)
            
            # Update flow with calculated bit rates
            if avg_bit_rate or max_bit_rate:
                from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
                update_data = {}
                
                if avg_bit_rate:
                    update_data['avg_bit_rate'] = avg_bit_rate
                if max_bit_rate:
                    update_data['max_bit_rate'] = max_bit_rate
                
                if update_data:
                    # Prepare and update
                    prepared_data = prepare_data_for_pyarrow(update_data)
                    self.vast_db.insert_record("flows", prepared_data)  # Will use UPSERT logic
                    logger.debug("Updated bit rates for flow %s: avg=%s, max=%s", flow_id, avg_bit_rate, max_bit_rate)
        
        except Exception as e:
            logger.warning(f"Failed to calculate bit rates for flow {flow_id}: {e}")
    
    async def create_flow(self, flow: Flow) -> bool:
        """Create a new flow (TAMS 8.0 with VFR validation)"""
        try:
            # TAMS 8.0: Validate VFR/frame_rate mutex for video flows
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                vfr = flow.essence_parameters.vfr or False
                frame_rate = flow.essence_parameters.frame_rate
                
                # Validate per ADR-0041
                if vfr and frame_rate is not None:
                    raise ValueError("If vfr=True, frame_rate MUST NOT be set")
                if not vfr and frame_rate is None:
                    raise ValueError("If vfr=False or omitted, frame_rate MUST be set")
            
            now = get_tams_timestamp()
            flow.created = now
            flow.metadata_updated = now
            flow.segments_updated = now
            
            # Check if source exists, create it automatically if it doesn't
            await self._ensure_source_exists(flow)
            
            flow_data = flow.model_dump()
            
            # TAMS 8.0: Extract and store VFR field separately
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                flow_data['vfr'] = flow.essence_parameters.vfr
            
            # Convert timestamp fields to PyArrow format using centralized function
            flow_data = prepare_data_for_pyarrow(flow_data)
            
            logger.debug("Creating flow with data: %s", flow_data)
            result = self.vast_db.insert_record("flows", flow_data)
            logger.debug("Flow creation result: %s", result)
            logger.debug("Flow created successfully with ID: %s", flow.id)
            
            # Auto-calculate bit rates if not provided
            if not flow.avg_bit_rate or not flow.max_bit_rate:
                try:
                    await self._calculate_and_update_bit_rates(flow.id)
                except Exception as e:
                    logger.warning("Failed to auto-calculate bit rates: %s", e)
            
            # Invalidate list caches for this flow's source (new flow created)
            from ..core.dependencies import get_cache_service
            cache_service = get_cache_service()
            await cache_service.delete("flows:list:all")
            if flow.source_id:
                await cache_service.clear_pattern(f"flows:source:{flow.source_id}*")
            
            return True
        except ValueError as ve:
            logger.error("VFR validation error creating flow: %s", ve)
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error("Failed to create flow: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """Update an existing flow using update-before-upsert approach (TAMS 8.0 with VFR validation)"""
        try:
            # TAMS 8.0: Validate VFR/frame_rate mutex for video flows
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                vfr = flow.essence_parameters.vfr or False
                frame_rate = flow.essence_parameters.frame_rate
                
                # Validate per ADR-0041
                if vfr and frame_rate is not None:
                    raise ValueError("If vfr=True, frame_rate MUST NOT be set")
                if not vfr and frame_rate is None:
                    raise ValueError("If vfr=False or omitted, frame_rate MUST be set")
            
            flow.metadata_updated = get_tams_timestamp()
            
            # Extract tags separately for handling in tags table
            tags_data = None
            if hasattr(flow, 'tags') and flow.tags is not None:
                tags_data = flow.tags
            
            # Only update mutable fields, exclude read-only fields and tags
            flow_data = flow.model_dump(exclude={'id', 'created', 'created_by', 'collected_by', 'tags'})
            
            # TAMS 8.0: Extract and store VFR field separately
            if isinstance(flow, VideoFlow) and flow.essence_parameters:
                flow_data['vfr'] = flow.essence_parameters.vfr
            
            # Convert timestamp fields to SQL format using centralized function
            flow_data = prepare_data_for_sql(flow_data)

            # Convert essence_parameters to JSON string for database compatibility
            if 'essence_parameters' in flow_data and flow_data['essence_parameters'] is not None:
                import json
                if hasattr(flow_data['essence_parameters'], 'model_dump'):
                    flow_data['essence_parameters'] = json.dumps(flow_data['essence_parameters'].model_dump())
                elif isinstance(flow_data['essence_parameters'], dict):
                    flow_data['essence_parameters'] = json.dumps(flow_data['essence_parameters'])

            # Convert flow_collection to JSON string for database compatibility
            if 'flow_collection' in flow_data and flow_data['flow_collection'] is not None:
                import json
                if hasattr(flow_data['flow_collection'], 'root'):
                    flow_data['flow_collection'] = json.dumps(flow_data['flow_collection'].root)
                elif isinstance(flow_data['flow_collection'], list):
                    flow_data['flow_collection'] = json.dumps(flow_data['flow_collection'])

            # Filter out None values to avoid "unknown" type errors
            flow_data = {k: v for k, v in flow_data.items() if v is not None}
            
            # Try UPDATE first
            try:
                if flow_data:
                    # Build SQL update statement directly
                    set_clauses = []
                    for column, value in flow_data.items():
                        # Check if this is a timestamp field that should be CAST
                        if is_timestamp_field(column) and isinstance(value, str) and value.startswith('CAST('):
                            # Handle timestamp fields that are already CAST expressions - don't quote them
                            set_clauses.append(f"{column} = {value}")
                        else:
                            # Handle regular fields
                            if isinstance(value, str):
                                escaped_value = value.replace("'", "''")
                                set_clauses.append(f"{column} = '{escaped_value}'")
                            elif value is None:
                                set_clauses.append(f"{column} = NULL")
                            else:
                                set_clauses.append(f"{column} = {value}")
                    
                    if set_clauses:
                        flows_table = self.vast_db.get_qualified_table_name("flows")
                        sql = f"UPDATE {flows_table} SET {', '.join(set_clauses)} WHERE id = '{flow_id}'"
                        logger.debug("Updating flow %s with SQL: %s", flow_id, sql)
                        self.vast_db.execute_sql(sql)
                        logger.debug("Successfully updated flow %s", flow_id)
                else:
                    logger.warning("No fields to update for flow %s", flow_id)
                
                # Handle tags separately using tag service
                if tags_data is not None:
                    await self.tag_service.update_flow_tags(flow_id, tags_data)
                
                # Invalidate cache
                from ..core.dependencies import get_cache_service
                cache_service = get_cache_service()
                await cache_service.delete(f"flow:{flow_id}")
                # Invalidate all flows list cache
                await cache_service.delete("flows:list:all")
                # Also invalidate list caches for this flow's source
                if flow.source_id:
                    await cache_service.clear_pattern(f"flows:source:{flow.source_id}*")
                
                return True
                
            except Exception as update_error:
                logger.warning("UPDATE failed for flow %s, trying upsert approach: %s", flow_id, update_error)
                
                # If UPDATE fails, try DELETE + INSERT (upsert)
                try:
                    # Delete existing flow
                    flows_table = self.vast_db.get_qualified_table_name("flows")
                    delete_sql = f"DELETE FROM {flows_table} WHERE id = '{flow_id}'"
                    self.vast_db.execute_sql(delete_sql)
                    logger.debug("Deleted existing flow %s for upsert", flow_id)
                    
                    # Insert new flow data
                    flow_data['id'] = flow_id
                    flow_data['created'] = get_tams_timestamp()
                    
                    # Convert timestamp fields to PyArrow format for insertion
                    flow_data = prepare_data_for_pyarrow(flow_data)
                    
                    logger.debug("Inserting flow %s with data: %s", flow_id, flow_data)
                    self.vast_db.insert_record("flows", flow_data)
                    logger.debug("Successfully inserted flow %s via upsert", flow_id)
                    
                    # Handle tags separately using tag service
                    if tags_data is not None:
                        await self.tag_service.update_flow_tags(flow_id, tags_data)
                    
                    # Invalidate cache
                    from ..core.dependencies import get_cache_service
                    cache_service = get_cache_service()
                    await cache_service.delete(f"flow:{flow_id}")
                    await cache_service.delete("flows:list:all")
                    # Also invalidate list caches for this flow's source
                    if flow.source_id:
                        await cache_service.clear_pattern(f"flows:source:{flow.source_id}*")
                    
                    return True
                    
                except Exception as upsert_error:
                    logger.error("Both UPDATE and upsert failed for flow %s: %s", flow_id, upsert_error)
                    raise upsert_error
                    
        except ValueError as ve:
            logger.error("VFR validation error updating flow: %s", ve)
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error("Failed to update flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_description(self, flow_id: str, description: str) -> bool:
        """Update flow description only"""
        try:
            escaped_description = description.replace("'", "''")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET description = '{escaped_description}' WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            # Invalidate cache
            from ..core.dependencies import get_cache_service
            cache_service = get_cache_service()
            await cache_service.delete(f"flow:{flow_id}")
            return True
        except Exception as e:
            logger.error("Failed to update flow description %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_description(self, flow_id: str) -> bool:
        """Delete flow description only"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET description = NULL WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            return True
        except Exception as e:
            logger.error("Failed to delete flow description %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_label(self, flow_id: str, label: str) -> bool:
        """Update flow label only"""
        try:
            escaped_label = label.replace("'", "''")
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET label = '{escaped_label}' WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            # Invalidate cache
            from ..core.dependencies import get_cache_service
            cache_service = get_cache_service()
            await cache_service.delete(f"flow:{flow_id}")
            return True
        except Exception as e:
            logger.error("Failed to update flow label %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_label(self, flow_id: str) -> bool:
        """Delete flow label only"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET label = NULL WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            return True
        except Exception as e:
            logger.error("Failed to delete flow label %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_read_only(self, flow_id: str, read_only: bool) -> bool:
        """Update flow read_only status only"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sql = f"UPDATE {flows_table} SET read_only = {str(read_only).lower()} WHERE id = '{flow_id}'"
            self.vast_db.execute_sql(sql)
            # Invalidate cache
            from ..core.dependencies import get_cache_service
            cache_service = get_cache_service()
            await cache_service.delete(f"flow:{flow_id}")
            return True
        except Exception as e:
            logger.error("Failed to update flow read_only %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow(self, flow_id: str, cascade: bool = True, object_service=None) -> bool:
        """Delete a flow
        
        Args:
            flow_id: Flow ID to delete
            cascade: If True, delete segments first and clean up multi-flow references.
                     If False, prevent deletion if flow is referenced in multi-flows.
            object_service: Optional ObjectStorageService for cleanup of unreferenced objects
        """
        try:
            # Check if flow is referenced in any multi-flow's flow_collection
            referencing_multi_flows = await self._get_multi_flows_referencing_flow(flow_id)
            
            if referencing_multi_flows:
                if not cascade:
                    # Prevent deletion if cascade=false and flow is referenced
                    raise ValueError(
                        f"Cannot delete flow {flow_id}: it is referenced in {len(referencing_multi_flows)} multi-flow(s). "
                        f"Use cascade=true to automatically remove references, or manually update the multi-flow(s) first."
                    )
                else:
                    # Remove flow from all multi-flows' flow_collection
                    updated_count = await self._remove_flow_from_multi_flows(flow_id)
                    if updated_count > 0:
                        logger.info(f"Removed flow {flow_id} from {updated_count} multi-flow(s) before deletion")
            
            # Delete flow segments first if cascade is True
            if cascade:
                await self._delete_flow_segments(flow_id)
                
                # After deleting segments, cleanup unreferenced objects (TAMS 8.0 spec requirement)
                if object_service:
                    try:
                        unreferenced = await object_service.get_unreferenced_objects()
                        if unreferenced:
                            deleted_count = await object_service.delete_unreferenced_objects(unreferenced)
                            logger.debug("Cleaned up %d unreferenced objects after flow deletion", deleted_count)
                    except Exception as e:
                        logger.warning("Failed to cleanup unreferenced objects after flow deletion: %s", e)
                        # Don't fail the deletion if cleanup fails
            
            # Get source_id before deletion for cache invalidation
            source_id = None
            try:
                flow = await self.get_flow(flow_id)
                if flow and flow.source_id:
                    source_id = flow.source_id
            except Exception:
                # If we can't get the flow, just invalidate the flow cache
                pass
            
            # Delete flow (async to avoid blocking)
            query = self.vast_db.query("flows").delete().where(f"id = '{flow_id}'")
            await asyncio.to_thread(lambda: query.execute())
            
            # Invalidate cache
            from ..core.dependencies import get_cache_service
            cache_service = get_cache_service()
            await cache_service.delete(f"flow:{flow_id}")
            await cache_service.delete("flows:list:all")
            if source_id:
                await cache_service.clear_pattern(f"flows:source:{source_id}*")
            
            return True
        except ValueError:
            # Re-raise ValueError (dependency violations)
            raise
        except Exception as e:
            logger.error("Failed to delete flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_flow_read_only(self, flow_id: str) -> bool:
        """Check if a flow is read-only"""
        try:
            result = self.vast_db.query("flows").select("read_only").where(f"id = '{flow_id}'").execute()
            
            # Handle VAST query result format
            read_only_value = False
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Columnar format - get first value from read_only column
                    read_only_col = data.get('read_only', [])
                    if read_only_col and len(read_only_col) > 0:
                        read_only_value = read_only_col[0] if read_only_col[0] is not None else False
                elif isinstance(data, list) and data:
                    # Row-oriented format
                    if len(data) > 0:
                        read_only_value = data[0].get('read_only', False) if isinstance(data[0], dict) else False
            elif isinstance(result, list) and result:
                # Direct list of rows
                if len(result) > 0:
                    read_only_value = result[0].get('read_only', False) if isinstance(result[0], dict) else False
            elif isinstance(result, (int, float)):
                # Query might return a count or 0
                return False
            else:
                # No result or unexpected format
                return False
            
            return bool(read_only_value)
        except Exception as e:
            logger.error("Failed to check flow read-only status for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _delete_flow_segments(self, flow_id: str) -> bool:
        """Delete flow segments for a flow"""
        try:
            # Use async to avoid blocking the event loop
            query = self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'")
            await asyncio.to_thread(lambda: query.execute())
            return True
        except Exception as e:
            logger.error("Failed to delete flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _get_multi_flows_referencing_flow(self, flow_id: str) -> List[str]:
        """
        Find all multi-flows that reference the given flow in their flow_collection.
        
        Args:
            flow_id: Flow ID to check for references
            
        Returns:
            List of multi-flow IDs that reference this flow
        """
        try:
            import json
            flows_table = self.vast_db.get_qualified_table_name("flows")
            
            # Query all flows with format=multi that have a flow_collection
            sql = f"""
                SELECT id, flow_collection 
                FROM {flows_table} 
                WHERE format = 'urn:x-nmos:format:multi' 
                AND flow_collection IS NOT NULL
            """
            result = self.vast_db.execute_sql(sql)
            
            referencing_flows = []
            
            # Handle VAST query result format
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    ids = data.get('id', [])
                    collections = data.get('flow_collection', [])
                    
                    for i in range(num_rows):
                        flow_id_value = ids[i] if i < len(ids) else None
                        collection_str = collections[i] if i < len(collections) else None
                        
                        if flow_id_value and collection_str:
                            try:
                                collection = json.loads(collection_str)
                                if isinstance(collection, list):
                                    # Check if any item in collection references the flow_id
                                    for item in collection:
                                        if isinstance(item, dict) and item.get('id') == flow_id:
                                            referencing_flows.append(flow_id_value)
                                            break
                            except (json.JSONDecodeError, TypeError):
                                # Skip invalid JSON
                                continue
                elif isinstance(data, list):
                    for row in data:
                        if isinstance(row, dict):
                            flow_id_value = row.get('id')
                            collection_str = row.get('flow_collection')
                            
                            if flow_id_value and collection_str:
                                try:
                                    collection = json.loads(collection_str)
                                    if isinstance(collection, list):
                                        for item in collection:
                                            if isinstance(item, dict) and item.get('id') == flow_id:
                                                referencing_flows.append(flow_id_value)
                                                break
                                except (json.JSONDecodeError, TypeError):
                                    continue
            elif isinstance(result, list):
                for row in result:
                    if isinstance(row, dict):
                        flow_id_value = row.get('id')
                        collection_str = row.get('flow_collection')
                        
                        if flow_id_value and collection_str:
                            try:
                                collection = json.loads(collection_str)
                                if isinstance(collection, list):
                                    for item in collection:
                                        if isinstance(item, dict) and item.get('id') == flow_id:
                                            referencing_flows.append(flow_id_value)
                                            break
                            except (json.JSONDecodeError, TypeError):
                                continue
            
            return referencing_flows
        except Exception as e:
            logger.error("Failed to get multi-flows referencing flow %s: %s", flow_id, e)
            # Don't fail the operation if this check fails
            return []
    
    async def _remove_flow_from_multi_flows(self, flow_id: str) -> int:
        """
        Remove the given flow from all multi-flows' flow_collection.
        
        Args:
            flow_id: Flow ID to remove from collections
            
        Returns:
            Number of multi-flows updated
        """
        try:
            import json
            flows_table = self.vast_db.get_qualified_table_name("flows")
            
            # Get all multi-flows that reference this flow
            multi_flow_ids = await self._get_multi_flows_referencing_flow(flow_id)
            
            if not multi_flow_ids:
                return 0
            
            updated_count = 0
            
            for multi_flow_id in multi_flow_ids:
                try:
                    # Get the current flow_collection
                    sql = f"SELECT flow_collection FROM {flows_table} WHERE id = '{multi_flow_id}'"
                    result = self.vast_db.execute_sql(sql)
                    
                    collection_str = None
                    if isinstance(result, dict) and 'data' in result:
                        data = result['data']
                        if isinstance(data, dict) and data:
                            collections = data.get('flow_collection', [])
                            if collections and len(collections) > 0:
                                collection_str = collections[0]
                        elif isinstance(data, list) and len(data) > 0:
                            collection_str = data[0].get('flow_collection')
                    elif isinstance(result, list) and len(result) > 0:
                        collection_str = result[0].get('flow_collection')
                    
                    if not collection_str:
                        continue
                    
                    # Parse and remove the flow_id
                    collection = json.loads(collection_str)
                    if isinstance(collection, list):
                        # Remove items with matching id
                        original_length = len(collection)
                        collection = [item for item in collection if not (isinstance(item, dict) and item.get('id') == flow_id)]
                        
                        if len(collection) < original_length:
                            # Update the flow_collection
                            updated_collection_json = json.dumps(collection)
                            escaped_json = updated_collection_json.replace("'", "''")
                            
                            update_sql = f"UPDATE {flows_table} SET flow_collection = '{escaped_json}' WHERE id = '{multi_flow_id}'"
                            self.vast_db.execute_sql(update_sql)
                            
                            # Invalidate cache for this multi-flow
                            from ..core.dependencies import get_cache_service
                            cache_service = get_cache_service()
                            await cache_service.delete(f"flow:{multi_flow_id}")
                            
                            updated_count += 1
                            logger.debug(f"Removed flow {flow_id} from multi-flow {multi_flow_id}'s flow_collection")
                except Exception as e:
                    logger.warning(f"Failed to update multi-flow {multi_flow_id} when removing flow {flow_id}: {e}")
                    # Continue with other multi-flows
                    continue
            
            if updated_count > 0:
                logger.info(f"Removed flow {flow_id} from {updated_count} multi-flow(s)' flow_collection")
            
            return updated_count
        except Exception as e:
            logger.error("Failed to remove flow %s from multi-flows: %s", flow_id, e)
            # Don't fail the deletion if cleanup fails
            return 0
    
    async def get_flow_with_source_details(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get flow details with source information using join query"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sources_table = self.vast_db.get_qualified_table_name("sources")
            
            sql = f"""
                SELECT 
                    f.id,
                    f.source_id,
                    f.format,
                    f.label,
                    f.description,
                    f.read_only,
                    f.created,
                    f.updated,
                    f.tags,
                    s.label as source_label,
                    s.format as source_format,
                    s.description as source_description
                FROM {flows_table} f
                JOIN {sources_table} s ON f.source_id = s.id
                WHERE f.id = '{flow_id}'
            """
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result and len(result['data']) > 0:
                row = result['data'][0]
                return {
                    "id": row[0],
                    "source_id": row[1],
                    "format": row[2],
                    "label": row[3],
                    "description": row[4],
                    "read_only": row[5],
                    "created": row[6],
                    "updated": row[7],
                    "tags": row[8],
                    "source": {
                        "id": row[1],
                        "label": row[9],
                        "format": row[10],
                        "description": row[11]
                    }
                }
            return None
        except Exception as e:
            logger.error("Failed to get flow with source details for %s: %s", flow_id, e)
            return None
    
    async def get_flows_with_source_details(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get flows with source information using join query"""
        try:
            flows_table = self.vast_db.get_qualified_table_name("flows")
            sources_table = self.vast_db.get_qualified_table_name("sources")
            
            sql = f"""
                SELECT 
                    f.id,
                    f.source_id,
                    f.format,
                    f.label,
                    f.description,
                    f.read_only,
                    f.created,
                    f.updated,
                    f.tags,
                    s.label as source_label,
                    s.format as source_format,
                    s.description as source_description
                FROM {flows_table} f
                JOIN {sources_table} s ON f.source_id = s.id
            """
            
            # Add filters if provided
            where_conditions = []
            if filters:
                if filters.get("source_id"):
                    where_conditions.append(f"f.source_id = '{filters['source_id']}'")
                if filters.get("label"):
                    where_conditions.append(f"f.label = '{filters['label']}'")
                if filters.get("format"):
                    where_conditions.append(f"f.format = '{filters['format']}'")
                if filters.get("source_format"):
                    where_conditions.append(f"s.format = '{filters['source_format']}'")
            
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
            
            sql += " ORDER BY f.created DESC"
            
            result = self.vast_db.execute_sql(sql)
            if result and 'data' in result:
                flows = []
                for row in result['data']:
                    flows.append({
                        "id": row[0],
                        "source_id": row[1],
                        "format": row[2],
                        "label": row[3],
                        "description": row[4],
                        "read_only": row[5],
                        "created": row[6],
                        "updated": row[7],
                        "tags": row[8],
                        "source": {
                            "id": row[1],
                            "label": row[9],
                            "format": row[10],
                            "description": row[11]
                        }
                    })
                return flows
            return []
        except Exception as e:
            logger.error("Failed to get flows with source details: %s", e)
            return []
    
    async def _ensure_source_exists(self, flow: Flow) -> None:
        """Ensure source exists, create it automatically if it doesn't"""
        try:
            # Check if source exists
            source_query = self.vast_db.query("sources").select("*").where(f"id = '{flow.source_id}'")
            result = source_query.execute()
            
            if not result or not result.get('data') or len(result['data']) == 0:
                # Source doesn't exist, create it automatically
                logger.debug("Source %s doesn't exist, creating it automatically", flow.source_id)
                
                # Create source with metadata from flow
                source = Source(
                    id=flow.source_id,
                    format=flow.format,
                    label=flow.label,
                    description=flow.description,
                    created_by=flow.created_by,
                    updated_by=flow.updated_by,
                    tags=flow.tags  # Replicate tags from flow to source
                )
                
                # Insert source into database
                source_data = source.model_dump(exclude={'source_collection', 'collected_by'})
                source_data['created'] = get_tams_timestamp()
                source_data['updated'] = get_tams_timestamp()
                
                self.vast_db.insert_record("sources", source_data)
                logger.debug("Successfully created source %s with metadata from flow", flow.source_id)
            else:
                logger.debug("Source %s already exists", flow.source_id)
                
        except Exception as e:
            logger.error("Failed to ensure source exists for flow %s: %s", flow.id, e)
            raise HTTPException(status_code=500, detail="Failed to create source automatically")

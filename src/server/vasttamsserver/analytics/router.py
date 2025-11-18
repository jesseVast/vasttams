"""
TAMS Analytics Router

This module provides API endpoints for analytics data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import logging
import json

from .models import AnalyticsSummary, SourceAnalytics, FlowAnalytics
from .service import AnalyticsService
from ..auth.rbac import require_viewer
from ..auth.middleware import UserSession
from ..core.dependencies import get_vast_db, get_cache_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tams/v8.0/analytics", tags=["analytics"])

# Cache keys for analytics endpoints
ANALYTICS_SUMMARY_CACHE_KEY = "analytics:summary"
ANALYTICS_SOURCES_CACHE_KEY = "analytics:sources"
ANALYTICS_FLOWS_CACHE_KEY = "analytics:flows"
ANALYTICS_CACHE_TTL = 300  # 5 minutes


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    refresh: bool = Query(False, description="Force refresh, bypass cache"),
    user_session: UserSession = Depends(require_viewer),
    vast_db = Depends(get_vast_db),
):
    """
    Get comprehensive analytics summary.
    
    Returns summary statistics including:
    - Counts of sources, flows, segments, objects
    - Storage statistics (total size, averages, min/max)
    - Format breakdown (video, audio, image, data, multi flows)
    - Time-based statistics (creation timestamps)
    
    Args:
        refresh: If True, bypass cache and force refresh (default: False)
    """
    cache_service = get_cache_service()
    
    # Check cache unless refresh is requested
    if not refresh:
        cached_summary = await cache_service.get(ANALYTICS_SUMMARY_CACHE_KEY)
        if cached_summary:
            logger.debug("Returning cached analytics summary")
            return AnalyticsSummary(**cached_summary)
    
    try:
        analytics_service = AnalyticsService(vast_db)
        summary = await analytics_service.get_summary()
        
        # Cache the result
        await cache_service.set(ANALYTICS_SUMMARY_CACHE_KEY, summary.model_dump(), ttl=ANALYTICS_CACHE_TTL)
        
        return summary
    except Exception as e:
        logger.error("Failed to get analytics summary: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics summary")


@router.get("/sources", response_model=List[SourceAnalytics])
async def get_source_analytics(
    refresh: bool = Query(False, description="Force refresh, bypass cache"),
    user_session: UserSession = Depends(require_viewer),
    vast_db = Depends(get_vast_db),
):
    """
    Get analytics per source.
    
    Returns analytics for each source including:
    - Flow count
    - Segment count
    - Total storage size
    - Creation time
    
    Args:
        refresh: If True, bypass cache and force refresh (default: False)
    """
    cache_service = get_cache_service()
    
    # Check cache unless refresh is requested
    if not refresh:
        cached_analytics = await cache_service.get(ANALYTICS_SOURCES_CACHE_KEY)
        if cached_analytics:
            logger.debug("Returning cached source analytics")
            # Deserialize from cached JSON
            if isinstance(cached_analytics, str):
                cached_data = json.loads(cached_analytics)
            else:
                cached_data = cached_analytics
            return [SourceAnalytics(**item) for item in cached_data]
    
    try:
        analytics_service = AnalyticsService(vast_db)
        analytics = await analytics_service.get_source_analytics()
        
        # Cache the result - use mode='json' to serialize datetime objects to ISO strings
        analytics_dict = [item.model_dump(mode='json') for item in analytics]
        await cache_service.set(ANALYTICS_SOURCES_CACHE_KEY, json.dumps(analytics_dict), ttl=ANALYTICS_CACHE_TTL)
        
        return analytics
    except Exception as e:
        logger.error("Failed to get source analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve source analytics")


@router.get("/flows", response_model=List[FlowAnalytics])
async def get_flow_analytics(
    refresh: bool = Query(False, description="Force refresh, bypass cache"),
    user_session: UserSession = Depends(require_viewer),
    vast_db = Depends(get_vast_db),
):
    """
    Get analytics per flow.
    
    Returns analytics for each flow including:
    - Segment count
    - Total storage size
    - Format
    - Source ID
    - Creation time
    
    Args:
        refresh: If True, bypass cache and force refresh (default: False)
    """
    cache_service = get_cache_service()
    
    # Check cache unless refresh is requested
    if not refresh:
        cached_analytics = await cache_service.get(ANALYTICS_FLOWS_CACHE_KEY)
        if cached_analytics:
            logger.debug("Returning cached flow analytics")
            # Deserialize from cached JSON
            if isinstance(cached_analytics, str):
                cached_data = json.loads(cached_analytics)
            else:
                cached_data = cached_analytics
            return [FlowAnalytics(**item) for item in cached_data]
    
    try:
        analytics_service = AnalyticsService(vast_db)
        analytics = await analytics_service.get_flow_analytics()
        
        # Cache the result - use mode='json' to serialize datetime objects to ISO strings
        analytics_dict = [item.model_dump(mode='json') for item in analytics]
        await cache_service.set(ANALYTICS_FLOWS_CACHE_KEY, json.dumps(analytics_dict), ttl=ANALYTICS_CACHE_TTL)
        
        return analytics
    except Exception as e:
        logger.error("Failed to get flow analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve flow analytics")


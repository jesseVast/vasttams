"""
TAMS Analytics Router

This module provides API endpoints for analytics data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import logging

from .models import AnalyticsSummary, SourceAnalytics, FlowAnalytics
from .service import AnalyticsService
from ..auth.rbac import require_viewer
from ..auth.middleware import UserSession
from ..core.dependencies import get_vast_db, get_cache_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tams/v8.0/analytics", tags=["analytics"])

# Cache key for analytics summary
ANALYTICS_SUMMARY_CACHE_KEY = "analytics:summary"
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
    """
    try:
        analytics_service = AnalyticsService(vast_db)
        analytics = await analytics_service.get_source_analytics()
        return analytics
    except Exception as e:
        logger.error("Failed to get source analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve source analytics")


@router.get("/flows", response_model=List[FlowAnalytics])
async def get_flow_analytics(
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
    """
    try:
        analytics_service = AnalyticsService(vast_db)
        analytics = await analytics_service.get_flow_analytics()
        return analytics
    except Exception as e:
        logger.error("Failed to get flow analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve flow analytics")


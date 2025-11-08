"""
TAMS Analytics Router

This module provides API endpoints for analytics data.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import logging

from .models import AnalyticsSummary, SourceAnalytics, FlowAnalytics
from .service import AnalyticsService
from ..auth.rbac import require_viewer
from ..auth.middleware import UserSession
from ..core.dependencies import get_vast_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
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
    """
    try:
        analytics_service = AnalyticsService(vast_db)
        summary = await analytics_service.get_summary()
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


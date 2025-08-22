"""
Analytics API router for TAMS
"""
from fastapi import APIRouter, Depends, HTTPException
from ..core.dependencies import get_vast_store
from ..storage.vast_store import VASTStore
from ..core.telemetry import telemetry_manager, trace_operation, monitor_operation
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/flow-usage")
@trace_operation("flow_usage_analytics")
@monitor_operation("analytics", "flow")
async def get_flow_usage_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow usage analytics"""
    try:
        analytics = await store.analytics_query("flow_usage")
        
        # Update business metrics
        if isinstance(analytics, dict) and 'total_flows' in analytics:
            telemetry_manager.record_business_metrics({
                'flows_count': analytics.get('total_flows', 0),
                'storage_bytes': analytics.get('estimated_storage_bytes', 0)
            })
        
        return analytics
    except Exception as e:
        logger.error("Failed to get flow usage analytics: %s", e)
        telemetry_manager.record_error("analytics_error", "/analytics/flow-usage", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/storage-usage")
@trace_operation("storage_usage_analytics")
@monitor_operation("analytics", "storage")
async def get_storage_usage_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get storage usage analytics"""
    try:
        analytics = await store.analytics_query("storage_usage")
        
        # Update business metrics
        if isinstance(analytics, dict):
            telemetry_manager.record_business_metrics({
                'segments_count': analytics.get('total_objects', 0),
                'storage_bytes': analytics.get('total_size_bytes', 0)
            })
        
        return analytics
    except Exception as e:
        logger.error("Failed to get storage usage analytics: %s", e)
        telemetry_manager.record_error("analytics_error", "/analytics/storage-usage", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/time-range-analysis")
@trace_operation("time_range_analytics")
@monitor_operation("analytics", "timerange")
async def get_time_range_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get time range analytics"""
    try:
        analytics = await store.analytics_query("time_range_analysis")
        
        # Update business metrics
        if isinstance(analytics, dict) and 'total_segments' in analytics:
            telemetry_manager.record_business_metrics({
                'segments_count': analytics.get('total_segments', 0)
            })
        
        return analytics
    except Exception as e:
        logger.error("Failed to get time range analytics: %s", e)
        telemetry_manager.record_error("analytics_error", "/analytics/time-range-analysis", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") 
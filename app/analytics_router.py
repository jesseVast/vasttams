"""
Analytics API router for TAMS
"""
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_vast_store
from app.vast_store import VASTStore
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/flow-usage")
async def get_flow_usage_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow usage analytics"""
    try:
        analytics = await store.analytics_query("flow_usage")
        return analytics
    except Exception as e:
        logger.error(f"Failed to get flow usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/storage-usage")
async def get_storage_usage_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get storage usage analytics"""
    try:
        analytics = await store.analytics_query("storage_usage")
        return analytics
    except Exception as e:
        logger.error(f"Failed to get storage usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/time-range-analysis")
async def get_time_range_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get time range analytics"""
    try:
        analytics = await store.analytics_query("time_range_analysis")
        return analytics
    except Exception as e:
        logger.error(f"Failed to get time range analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 
"""
HLS Router

Provides HLS API endpoints for streaming TAMS content.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from ..core.dependencies import get_vast_db, get_s3_client
from .manager import HLSManager
from ..auth.rbac import require_admin, require_editor, require_viewer
from ..auth.middleware import UserSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hls", tags=["hls"])


@router.get("/flows/{flow_id}/playlist.m3u8")
async def get_hls_playlist(
    flow_id: str,
    vast_db=Depends(get_vast_db),
    s3_client=Depends(get_s3_client),
    user_session: UserSession = Depends(require_viewer)
):
    """
    Get HLS playlist for a flow
    
    Returns M3U8 format HLS playlist that can be played in standard HLS players.
    
    Example: GET /hls/flows/{flow_id}/playlist.m3u8
    """
    try:
        # Verify flow exists
        from ..flows.service import FlowStorageService
        flow_service = FlowStorageService(vast_db, s3_client)
        
        flow = await flow_service.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Generate HLS playlist
        hls_manager = HLSManager(vast_db, s3_client)
        playlist = await hls_manager.generate_playlist(flow_id)
        
        if not playlist or not playlist.segments:
            raise HTTPException(
                status_code=404, 
                detail="No segments found for flow or segments are not HLS-compatible"
            )
        
        # Convert to M3U8 format
        m3u8_content = hls_manager.playlist_to_m3u8(playlist)
        
        # Return with proper content type
        return Response(
            content=m3u8_content,
            media_type="application/vnd.apple.mpegurl",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Access-Control-Allow-Origin": "*"  # Allow CORS for playback
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate HLS playlist for flow {flow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate HLS playlist: {str(e)}"
        )


@router.get("/flows/{flow_id}/status")
async def get_hls_status(
    flow_id: str,
    vast_db=Depends(get_vast_db),
    s3_client=Depends(get_s3_client)
):
    """
    Get HLS status for a flow
    
    Returns information about HLS compatibility and segment availability.
    """
    try:
        from ..flows.service import FlowStorageService
        from ..segments.service import SegmentStorageService
        from ..core.config import get_settings
        
        settings = get_settings()
        flow_service = FlowStorageService(vast_db, s3_client)
        segment_service = SegmentStorageService(vast_db, s3_client, settings)
        
        # Check flow
        flow = await flow_service.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Check segments
        segments = await segment_service.get_flow_segments(flow_id)
        
        if not segments:
            return {
                "flow_id": flow_id,
                "hls_ready": False,
                "reason": "No segments found"
            }
        
        # Check if segments have URLs
        hls_compatible = all(
            segment.get_urls and len(segment.get_urls) > 0 
            for segment in segments
        )
        
        return {
            "flow_id": flow_id,
            "hls_ready": hls_compatible,
            "segment_count": len(segments),
            "reason": None if hls_compatible else "Some segments missing URLs",
            "playlist_url": f"/hls/flows/{flow_id}/playlist.m3u8" if hls_compatible else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get HLS status for flow {flow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get HLS status: {str(e)}")


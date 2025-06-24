"""
TAMS (Time-addressable Media Store) FastAPI Application

This implements the BBC TAMS API specification with support for:
- Sources and flows management
- Flow segments with time ranges
- Media object storage
- Webhooks and event streaming
- Analytics via VAST database
"""

import logging
import uuid
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .models import (
    Service, ServiceResponse, Source, SourcesResponse, Flow, FlowsResponse,
    FlowSegment, Object, Webhook, WebhookPost, WebhooksResponse,
    FlowStoragePost, FlowStorage, DeletionRequest, DeletionRequestsResponse,
    SourceFilters, FlowFilters, FlowDetailFilters, PagingInfo
)
from .vast_store import VASTStore
from .config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TAMS API",
    description="Time-addressable Media Store API",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize VAST store
vast_store = None

@app.on_event("startup")
async def startup_event():
    """Initialize VAST store on startup"""
    global vast_store
    settings = get_settings()
    
    # Initialize VAST store with vastdbmanager
    vast_store = VASTStore(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema
    )
    logger.info("TAMS API started with VAST store using vastdbmanager")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global vast_store
    if vast_store:
        await vast_store.close()
    logger.info("TAMS API shutdown complete")

# Dependency to get VAST store
def get_vast_store() -> VASTStore:
    if vast_store is None:
        raise HTTPException(status_code=500, detail="VAST store not initialized")
    return vast_store

# Service endpoints
@app.get("/", response_model=ServiceResponse)
async def get_service_info():
    """Get service information"""
    return ServiceResponse(
        data=Service(
            name="TAMS API",
            description="Time-addressable Media Store API",
            type="urn:x-tams:service:api",
            api_version="6.0",
            service_version="1.0.0",
            media_store={"type": "http_object_store"},
            event_stream_mechanisms=[
                {"name": "webhooks", "description": "HTTP webhooks for event notifications"}
            ]
        )
    )

# Source endpoints
@app.get("/sources", response_model=SourcesResponse)
async def list_sources(
    label: Optional[str] = Query(None, description="Filter by label"),
    format: Optional[str] = Query(None, description="Filter by format"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results"),
    store: VASTStore = Depends(get_vast_store)
):
    """List sources with optional filtering"""
    try:
        filters = {}
        if label:
            filters['label'] = label
        if format:
            filters['format'] = format
        
        sources = await store.list_sources(filters=filters, limit=limit)
        
        # Create paging info
        paging = None
        if len(sources) == limit:
            paging = PagingInfo(limit=limit, next_key=str(uuid.uuid4()))
        
        return SourcesResponse(data=sources, paging=paging)
        
    except Exception as e:
        logger.error(f"Failed to list sources: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/sources/{source_id}", response_model=Source)
async def get_source(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source by ID"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/sources", response_model=Source, status_code=201)
async def create_source(
    source: Source,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new source"""
    try:
        # Set timestamps
        now = datetime.utcnow()
        source.created = now
        source.updated = now
        
        success = await store.create_source(source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create source")
        
        return source
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create source: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow endpoints
@app.get("/flows", response_model=FlowsResponse)
async def list_flows(
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    format: Optional[str] = Query(None, description="Filter by format"),
    codec: Optional[str] = Query(None, description="Filter by codec"),
    label: Optional[str] = Query(None, description="Filter by label"),
    frame_width: Optional[int] = Query(None, description="Filter by frame width"),
    frame_height: Optional[int] = Query(None, description="Filter by frame height"),
    page: Optional[str] = Query(None, description="Pagination key"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Number of results"),
    store: VASTStore = Depends(get_vast_store)
):
    """List flows with optional filtering"""
    try:
        filters = {}
        if source_id:
            filters['source_id'] = source_id
        if format:
            filters['format'] = format
        if codec:
            filters['codec'] = codec
        if label:
            filters['label'] = label
        
        flows = await store.list_flows(filters=filters, limit=limit)
        
        # Create paging info
        paging = None
        if len(flows) == limit:
            paging = PagingInfo(limit=limit, next_key=str(uuid.uuid4()))
        
        return FlowsResponse(data=flows, paging=paging)
        
    except Exception as e:
        logger.error(f"Failed to list flows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/flows/{flow_id}", response_model=Flow)
async def get_flow(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow by ID"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/flows", response_model=Flow, status_code=201)
async def create_flow(
    flow: Flow,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new flow"""
    try:
        # Set timestamps
        now = datetime.utcnow()
        flow.created = now
        flow.updated = now
        
        success = await store.create_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create flow")
        
        return flow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create flow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow segments endpoints
@app.get("/flows/{flow_id}/segments", response_model=List[FlowSegment])
async def get_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow segments for a specific flow"""
    try:
        # Verify flow exists
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        segments = await store.get_flow_segments(flow_id, timerange=timerange)
        return segments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow segments for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/flows/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_flow_segment(
    flow_id: str,
    segment: FlowSegment,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new flow segment"""
    try:
        # Verify flow exists
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        success = await store.create_flow_segment(segment, flow_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create flow segment")
        
        return segment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create flow segment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Object endpoints
@app.get("/objects/{object_id}", response_model=Object)
async def get_object(
    object_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get media object by ID"""
    try:
        obj = await store.get_object(object_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        return obj
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/objects", response_model=Object, status_code=201)
async def create_object(
    obj: Object,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new media object"""
    try:
        # Set timestamp
        obj.created = datetime.utcnow()
        
        success = await store.create_object(obj)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create object")
        
        return obj
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create object: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Webhook endpoints
@app.get("/webhooks", response_model=WebhooksResponse)
async def list_webhooks(
    store: VASTStore = Depends(get_vast_store)
):
    """List webhooks"""
    try:
        # For now, return empty list - webhook storage not implemented
        return WebhooksResponse(data=[])
        
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/webhooks", response_model=Webhook, status_code=201)
async def create_webhook(
    webhook: WebhookPost,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new webhook"""
    try:
        # For now, just return the webhook - storage not implemented
        return Webhook(
            url=webhook.url,
            api_key_name=webhook.api_key_name,
            api_key_value=webhook.api_key_value,
            events=webhook.events
        )
        
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow storage endpoints
@app.post("/flows/{flow_id}/storage", response_model=FlowStorage)
async def allocate_flow_storage(
    flow_id: str,
    storage_request: FlowStoragePost,
    store: VASTStore = Depends(get_vast_store)
):
    """Allocate storage for flow objects"""
    try:
        # Verify flow exists
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Generate storage locations
        storage_locations = []
        object_ids = storage_request.object_ids or [f"obj_{i}" for i in range(storage_request.limit or 1)]
        
        for obj_id in object_ids:
            storage_locations.append({
                "object_id": obj_id,
                "put_url": f"https://storage.example.com/upload/{obj_id}",
                "bucket_put_url": f"https://storage.example.com/bucket/{obj_id}",
                "cors_put_url": f"https://storage.example.com/cors/{obj_id}"
            })
        
        return FlowStorage(storage_locations=storage_locations)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to allocate storage for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Deletion request endpoints
@app.get("/deletion-requests", response_model=DeletionRequestsResponse)
async def list_deletion_requests(
    store: VASTStore = Depends(get_vast_store)
):
    """List deletion requests"""
    try:
        # For now, return empty list - deletion request storage not implemented
        return DeletionRequestsResponse(data={"requests": []})
        
    except Exception as e:
        logger.error(f"Failed to list deletion requests: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/deletion-requests", response_model=DeletionRequest, status_code=201)
async def create_deletion_request(
    deletion_request: DeletionRequest,
    background_tasks: BackgroundTasks,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new deletion request"""
    try:
        # Verify flow exists
        flow = await store.get_flow(str(deletion_request.flow_id))
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Set timestamps
        now = datetime.utcnow()
        deletion_request.created = now
        deletion_request.updated = now
        
        # Add background task to process deletion
        background_tasks.add_task(process_deletion_request, deletion_request)
        
        return deletion_request
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create deletion request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Analytics endpoints
@app.get("/analytics/flow-usage")
async def get_flow_usage_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow usage analytics"""
    try:
        results = await store.analytics_query("flow_usage")
        return results
        
    except Exception as e:
        logger.error(f"Failed to get flow usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/analytics/storage-usage")
async def get_storage_usage_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get storage usage analytics"""
    try:
        results = await store.analytics_query("storage_usage")
        return results
        
    except Exception as e:
        logger.error(f"Failed to get storage usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/analytics/time-range-analysis")
async def get_time_range_analytics(
    store: VASTStore = Depends(get_vast_store)
):
    """Get time range analysis"""
    try:
        results = await store.analytics_query("time_range_analysis")
        return results
        
    except Exception as e:
        logger.error(f"Failed to get time range analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Background task for processing deletion requests
async def process_deletion_request(deletion_request: DeletionRequest):
    """Process deletion request in background"""
    try:
        logger.info(f"Processing deletion request {deletion_request.request_id}")
        
        # Update status to in_progress
        deletion_request.status = "in_progress"
        deletion_request.updated = datetime.utcnow()
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Update status to completed
        deletion_request.status = "completed"
        deletion_request.updated = datetime.utcnow()
        
        logger.info(f"Completed deletion request {deletion_request.request_id}")
        
    except Exception as e:
        logger.error(f"Failed to process deletion request {deletion_request.request_id}: {e}")
        deletion_request.status = "failed"
        deletion_request.updated = datetime.utcnow()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
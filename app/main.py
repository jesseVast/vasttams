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
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn

from .models import (
    Service, ServiceResponse, Source, SourcesResponse, Flow, FlowsResponse,
    FlowSegment, Object, Webhook, WebhookPost, WebhooksResponse,
    FlowStoragePost, FlowStorage, DeletionRequest, DeletionRequestsResponse,
    SourceFilters, FlowFilters, FlowDetailFilters, PagingInfo, Tags, MediaStore, EventStreamMechanism, StorageLocation
)
from .vast_store import VASTStore
from .config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global VAST store instance
vast_store = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    global vast_store
    
    # Startup
    settings = get_settings()
    vast_store = VASTStore(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema,
        s3_endpoint_url=settings.s3_endpoint_url,
        s3_access_key_id=settings.s3_access_key_id,
        s3_secret_access_key=settings.s3_secret_access_key,
        s3_bucket_name=settings.s3_bucket_name,
        s3_use_ssl=settings.s3_use_ssl
    )
    logger.info("TAMS API started with VAST store using vastdbmanager and S3 for segments")
    
    yield
    
    # Shutdown
    if vast_store:
        await vast_store.close()
    logger.info("TAMS API shutdown complete")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="TAMS API",
    description="Time-addressable Media Store API",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Dependency to get VAST store
def get_vast_store() -> VASTStore:
    if vast_store is None:
        raise HTTPException(status_code=500, detail="VAST store not initialized")
    return vast_store

# Service endpoints
@app.head("/")
async def head_root():
    """Return root path headers"""
    return {}

@app.get("/", response_model=List[str])
async def get_root():
    """List of paths available from this API"""
    return ["service", "flows", "sources", "flow-delete-requests"]

@app.head("/service")
async def head_service():
    """Return service path headers"""
    return {}

@app.get("/service", response_model=Service)
async def get_service():
    """Get service information"""
    return Service(
        name="TAMS API",
        description="Time-addressable Media Store API",
        type="urn:x-tams:service:api",
        api_version="6.0",
        service_version="1.0.0",
        media_store=MediaStore(type="http_object_store"),
        event_stream_mechanisms=[
            EventStreamMechanism(name="webhooks", description="HTTP webhooks for event notifications")
        ]
    )

@app.post("/service", status_code=200)
async def update_service(service: Service):
    """Update service information"""
    # In a real implementation, this would update the service configuration
    return {"message": "Service information updated"}

# Source endpoints
@app.head("/sources")
async def head_sources():
    """Return sources path headers"""
    return {}

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

@app.head("/sources/{source_id}")
async def head_source(source_id: str):
    """Return source path headers"""
    return {}

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
        now = datetime.now(timezone.utc)
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

# Source tags endpoints
@app.head("/sources/{source_id}/tags")
async def head_source_tags(source_id: str):
    """Return source tags path headers"""
    return {}

@app.get("/sources/{source_id}/tags")
async def get_source_tags(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source tags"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source.tags.root if source.tags else {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source tags {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.head("/sources/{source_id}/tags/{name}")
async def head_source_tag(source_id: str, name: str):
    """Return source tag path headers"""
    return {}

@app.get("/sources/{source_id}/tags/{name}")
async def get_source_tag(
    source_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get specific source tag"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not source.tags or name not in source.tags.root:
            raise HTTPException(status_code=404, detail="Tag not found")
        return {name: source.tags.root[name]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source tag {source_id}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/sources/{source_id}/tags/{name}")
async def update_source_tag(
    source_id: str,
    name: str,
    value: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update source tag"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Update tag
        if not source.tags:
            source.tags = Tags({})
        source.tags.root[name] = value
        source.updated = datetime.now(timezone.utc)
        
        success = await store.update_source(source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source tag")
        
        return {name: value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source tag {source_id}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/sources/{source_id}/tags/{name}")
async def delete_source_tag(
    source_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete source tag"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        if not source.tags or name not in source.tags.root:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Remove tag
        del source.tags.root[name]
        source.updated = datetime.now(timezone.utc)
        
        success = await store.update_source(source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source tag")
        
        return {"message": "Tag deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source tag {source_id}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Source description endpoints
@app.head("/sources/{source_id}/description")
async def head_source_description(source_id: str):
    """Return source description path headers"""
    return {}

@app.get("/sources/{source_id}/description")
async def get_source_description(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source description"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return {"description": source.description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source description {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/sources/{source_id}/description")
async def update_source_description(
    source_id: str,
    description: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update source description"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.description = description
        source.updated = datetime.now(timezone.utc)
        
        success = await store.update_source(source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source description")
        
        return {"description": description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source description {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/sources/{source_id}/description")
async def delete_source_description(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete source description"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.description = None
        source.updated = datetime.now(timezone.utc)
        
        success = await store.update_source(source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source description")
        
        return {"message": "Description deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source description {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Source label endpoints
@app.head("/sources/{source_id}/label")
async def head_source_label(source_id: str):
    """Return source label path headers"""
    return {}

@app.get("/sources/{source_id}/label")
async def get_source_label(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get source label"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return {"label": source.label}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source label {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/sources/{source_id}/label")
async def update_source_label(
    source_id: str,
    label: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update source label"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.label = label
        source.updated = datetime.now(timezone.utc)
        
        success = await store.update_source(source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update source label")
        
        return {"label": label}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update source label {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/sources/{source_id}/label")
async def delete_source_label(
    source_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete source label"""
    try:
        source = await store.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.label = None
        source.updated = datetime.now(timezone.utc)
        
        success = await store.update_source(source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source label")
        
        return {"message": "Label deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source label {source_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow endpoints
@app.head("/flows")
async def head_flows():
    """Return flows path headers"""
    return {}

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

@app.head("/flows/{flow_id}")
async def head_flow(flow_id: str):
    """Return flow path headers"""
    return {}

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

@app.put("/flows/{flow_id}", response_model=Flow)
async def update_flow(
    flow_id: str,
    flow: Flow,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow"""
    try:
        existing_flow = await store.get_flow(flow_id)
        if not existing_flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Update fields
        flow.id = existing_flow.id  # Preserve ID
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow")
        
        return flow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/flows/{flow_id}")
async def delete_flow(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow"""
    try:
        success = await store.delete_flow(flow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        return {"message": "Flow deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/flows", response_model=Flow, status_code=201)
async def create_flow(
    flow: Flow,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new flow"""
    try:
        # Set timestamps
        now = datetime.now(timezone.utc)
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

# Flow tags endpoints
@app.head("/flows/{flow_id}/tags")
async def head_flow_tags(flow_id: str):
    """Return flow tags path headers"""
    return {}

@app.get("/flows/{flow_id}/tags")
async def get_flow_tags(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow tags"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return flow.tags.root if flow.tags else {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow tags {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.head("/flows/{flow_id}/tags/{name}")
async def head_flow_tag(flow_id: str, name: str):
    """Return flow tag path headers"""
    return {}

@app.get("/flows/{flow_id}/tags/{name}")
async def get_flow_tag(
    flow_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get specific flow tag"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        if not flow.tags or name not in flow.tags.root:
            raise HTTPException(status_code=404, detail="Tag not found")
        return {name: flow.tags.root[name]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow tag {flow_id}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/flows/{flow_id}/tags/{name}")
async def update_flow_tag(
    flow_id: str,
    name: str,
    value: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow tag"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Update tag
        if not flow.tags:
            flow.tags = Tags({})
        flow.tags.root[name] = value
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow tag")
        
        return {name: value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow tag {flow_id}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/flows/{flow_id}/tags/{name}")
async def delete_flow_tag(
    flow_id: str,
    name: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow tag"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        if not flow.tags or name not in flow.tags.root:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Remove tag
        del flow.tags.root[name]
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow tag")
        
        return {"message": "Tag deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow tag {flow_id}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow description endpoints
@app.head("/flows/{flow_id}/description")
async def head_flow_description(flow_id: str):
    """Return flow description path headers"""
    return {}

@app.get("/flows/{flow_id}/description")
async def get_flow_description(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow description"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"description": flow.description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow description {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/flows/{flow_id}/description")
async def update_flow_description(
    flow_id: str,
    description: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow description"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.description = description
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow description")
        
        return {"description": description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow description {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/flows/{flow_id}/description")
async def delete_flow_description(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow description"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.description = None
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow description")
        
        return {"message": "Description deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow description {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow label endpoints
@app.head("/flows/{flow_id}/label")
async def head_flow_label(flow_id: str):
    """Return flow label path headers"""
    return {}

@app.get("/flows/{flow_id}/label")
async def get_flow_label(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow label"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"label": flow.label}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow label {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/flows/{flow_id}/label")
async def update_flow_label(
    flow_id: str,
    label: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow label"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.label = label
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow label")
        
        return {"label": label}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow label {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/flows/{flow_id}/label")
async def delete_flow_label(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow label"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.label = None
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow label")
        
        return {"message": "Label deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow label {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow read-only endpoints
@app.head("/flows/{flow_id}/read_only")
async def head_flow_read_only(flow_id: str):
    """Return flow read-only path headers"""
    return {}

@app.get("/flows/{flow_id}/read_only")
async def get_flow_read_only(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow read-only status"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"read_only": flow.read_only}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow read-only {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/flows/{flow_id}/read_only")
async def update_flow_read_only(
    flow_id: str,
    read_only: bool,
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow read-only status"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        flow.read_only = read_only
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow read-only status")
        
        return {"read_only": read_only}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow read-only {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow collection endpoints (for MultiFlow)
@app.head("/flows/{flow_id}/flow_collection")
async def head_flow_collection(flow_id: str):
    """Return flow collection path headers"""
    return {}

@app.get("/flows/{flow_id}/flow_collection")
async def get_flow_collection(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow collection"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        if not hasattr(flow, 'flow_collection'):
            raise HTTPException(status_code=404, detail="Flow collection not found")
        return {"flow_collection": [str(uuid) for uuid in flow.flow_collection]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow collection {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/flows/{flow_id}/flow_collection")
async def update_flow_collection(
    flow_id: str,
    flow_collection: List[str],
    store: VASTStore = Depends(get_vast_store)
):
    """Update flow collection"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        if not hasattr(flow, 'flow_collection'):
            raise HTTPException(status_code=400, detail="Flow does not support collections")
        
        flow.flow_collection = [UUID(uuid) for uuid in flow_collection]
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flow collection")
        
        return {"flow_collection": flow_collection}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update flow collection {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/flows/{flow_id}/flow_collection")
async def delete_flow_collection(
    flow_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow collection"""
    try:
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        if not hasattr(flow, 'flow_collection'):
            raise HTTPException(status_code=400, detail="Flow does not support collections")
        
        flow.flow_collection = []
        flow.updated = datetime.now(timezone.utc)
        
        success = await store.update_flow(flow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow collection")
        
        return {"message": "Flow collection deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow collection {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow segments endpoints
@app.head("/flows/{flow_id}/segments")
async def head_flow_segments(flow_id: str):
    """Return flow segments path headers"""
    return {}

@app.get("/flows/{flow_id}/segments", response_model=List[FlowSegment])
async def get_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Filter by time range"),
    store: VASTStore = Depends(get_vast_store)
):
    """Get flow segment metadata and S3 URLs (not the data itself)"""
    try:
        segments = await store.get_flow_segments(flow_id, timerange=timerange)
        return segments
    except Exception as e:
        logger.error(f"Failed to get flow segments for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/flows/{flow_id}/segments", response_model=FlowSegment, status_code=201)
async def create_flow_segment(
    flow_id: str,
    segment: FlowSegment,
    file: UploadFile = File(...),
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new flow segment (media data goes to S3, metadata to DB)"""
    try:
        data = await file.read()
        success = await store.create_flow_segment(segment, flow_id, data, file.content_type)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create flow segment")
        
        return segment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create flow segment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/flows/{flow_id}/segments")
async def delete_flow_segments(
    flow_id: str,
    timerange: Optional[str] = Query(None, description="Delete segments in time range"),
    store: VASTStore = Depends(get_vast_store)
):
    """Delete flow segments"""
    try:
        success = await store.delete_flow_segments(flow_id, timerange=timerange)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete flow segments")
        
        return {"message": "Flow segments deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete flow segments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Flow storage endpoints
@app.post("/flows/{flow_id}/storage", response_model=FlowStorage)
async def allocate_flow_storage(
    flow_id: str,
    storage_request: FlowStoragePost,
    store: VASTStore = Depends(get_vast_store)
):
    """Allocate storage for flow segments"""
    try:
        # Check if flow exists
        flow = await store.get_flow(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        # Generate storage locations
        storage_locations = []
        object_ids = storage_request.object_ids or [str(uuid.uuid4()) for _ in range(storage_request.limit or 1)]
        
        for object_id in object_ids:
            # Generate presigned URLs for S3 upload
            put_url = await store.s3_store.generate_presigned_url(
                flow_id, object_id, "[0:0)", 'put_object'
            )
            
            storage_locations.append(StorageLocation(
                object_id=object_id,
                put_url=put_url or "",
                bucket_put_url=None
            ))
        
        return FlowStorage(storage_locations=storage_locations)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to allocate storage for flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Object endpoints
@app.head("/objects/{object_id}")
async def head_object(object_id: str):
    """Return object path headers"""
    return {}

@app.get("/objects/{object_id}", response_model=Object)
async def get_object(
    object_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get object by ID"""
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
    """Create a new object"""
    try:
        # Set timestamps
        now = datetime.now(timezone.utc)
        obj.created = now
        
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
@app.head("/service/webhooks")
async def head_webhooks():
    """Return webhooks path headers"""
    return {}

@app.get("/service/webhooks", response_model=WebhooksResponse)
async def list_webhooks(
    store: VASTStore = Depends(get_vast_store)
):
    """List webhooks"""
    try:
        webhooks = await store.list_webhooks()
        return WebhooksResponse(data=webhooks)
        
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/service/webhooks", response_model=Webhook, status_code=201)
async def create_webhook(
    webhook: WebhookPost,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new webhook"""
    try:
        success = await store.create_webhook(webhook)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create webhook")
        
        return Webhook(
            url=webhook.url,
            api_key_name=webhook.api_key_name,
            events=webhook.events
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Deletion requests endpoints
@app.head("/flow-delete-requests")
async def head_deletion_requests():
    """Return deletion requests path headers"""
    return {}

@app.get("/flow-delete-requests", response_model=DeletionRequestsResponse)
async def list_deletion_requests(
    store: VASTStore = Depends(get_vast_store)
):
    """List deletion requests"""
    try:
        requests = await store.list_deletion_requests()
        return DeletionRequestsResponse(data=requests)
        
    except Exception as e:
        logger.error(f"Failed to list deletion requests: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.head("/flow-delete-requests/{request_id}")
async def head_deletion_request(request_id: str):
    """Return deletion request path headers"""
    return {}

@app.get("/flow-delete-requests/{request_id}", response_model=DeletionRequest)
async def get_deletion_request(
    request_id: str,
    store: VASTStore = Depends(get_vast_store)
):
    """Get deletion request by ID"""
    try:
        request = await store.get_deletion_request(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Deletion request not found")
        return request
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deletion request {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/flow-delete-requests", response_model=DeletionRequest, status_code=201)
async def create_deletion_request(
    deletion_request: DeletionRequest,
    background_tasks: BackgroundTasks,
    store: VASTStore = Depends(get_vast_store)
):
    """Create a new deletion request"""
    try:
        # Set timestamps
        now = datetime.now(timezone.utc)
        deletion_request.created = now
        deletion_request.updated = now
        
        success = await store.create_deletion_request(deletion_request)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create deletion request")
        
        # Process deletion in background
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
        analytics = await store.analytics_query("flow_usage")
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to get flow usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/analytics/storage-usage")
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

@app.get("/analytics/time-range-analysis")
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

# Background task for processing deletion requests
async def process_deletion_request(deletion_request: DeletionRequest):
    """Process deletion request in background"""
    try:
        logger.info(f"Processing deletion request {deletion_request.request_id}")
        # Implementation would delete flow segments and update request status
        # This is a placeholder for the actual deletion logic
        await asyncio.sleep(1)  # Simulate processing time
        logger.info(f"Completed deletion request {deletion_request.request_id}")
    except Exception as e:
        logger.error(f"Failed to process deletion request {deletion_request.request_id}: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
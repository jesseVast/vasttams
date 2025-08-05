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
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, cast
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import uvicorn
from uuid import UUID, uuid4

from .models import (
    Service, ServiceResponse, Source, SourcesResponse, Flow, FlowsResponse,
    FlowSegment, Object, Webhook, WebhookPost, WebhooksResponse,
    FlowStoragePost, FlowStorage, DeletionRequest, DeletionRequestsResponse,
    SourceFilters, FlowFilters, FlowDetailFilters, PagingInfo, Tags, MediaStore, EventStreamMechanism, StorageLocation,
    DeletionRequestsList, StorageBackendsList, StorageBackendsResponse, StorageBackend
)
from .vast_store import VASTStore
from .config import get_settings
from app.segments import SegmentManager
from app.flows import FlowManager
from app.sources import SourceManager
from app.objects import ObjectManager
from app.flows_router import router as flows_router
from app.segments_router import router as segments_router
from app.sources_router import router as sources_router
from app.objects_router import router as objects_router
from app.analytics_router import router as analytics_router
from .dependencies import get_vast_store, set_vast_store
from .telemetry import telemetry_manager, telemetry_middleware, metrics_endpoint, enhanced_health_check
from .auth import login_basic, logout, require_authentication, require_admin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global VAST store instance
vast_store = None
segment_manager = SegmentManager()
flow_manager = FlowManager()
source_manager = SourceManager()
object_manager = ObjectManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
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
    set_vast_store(vast_store)  # Set the global store instance
    logger.info("TAMS API started with VAST store using vastdbmanager and S3 for segments")
    
    yield
    
    # Shutdown
    if vast_store:
        await vast_store.close()
    logger.info("TAMS API shutdown complete")

def custom_openapi() -> Dict[str, Any]:
    """Generate custom OpenAPI schema"""
    if app.openapi_schema:
        return cast(Dict[str, Any], app.openapi_schema)
    # Try to load from file first
    openapi_file = os.path.join(os.path.dirname(__file__), "..", "api", "openapi.json")
    if os.path.exists(openapi_file):
        try:
            with open(openapi_file, 'r') as f:
                app.openapi_schema = json.load(f)
                return cast(Dict[str, Any], app.openapi_schema)
        except Exception as e:
            logger.warning(f"Failed to load OpenAPI file: {e}")
    # Fallback to auto-generated schema
    try:
        app.openapi_schema = get_openapi(
            title="TAMS API",
            version="7.0.0",
            description="Time-addressable Media Store API",
            routes=app.routes,
        )
        return cast(Dict[str, Any], app.openapi_schema)
    except Exception as e:
        logger.error(f"Failed to generate OpenAPI schema: {e}")
        return {}  # Always return a dict

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="TAMS API",
    description="Time-addressable Media Store API",
    version="7.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Service", "description": "The service root and documentation about the service itself"},
        {"name": "Sources", "description": "The ephemeral concept of an individual piece of media without being rendered to a specific encoding/packaging."},
        {"name": "Flows", "description": "Sources which have been 'rendered' to a specific encoding/packaging format."},
        {"name": "FlowSegments", "description": "A timerange segment of a Flow that references a media object in the object store."},
        {"name": "Objects", "description": "The object in the object store that contains the media essence."},
        {"name": "MediaStorage", "description": "The system that stores the media objects referenced by flow segments."},
        {"name": "FlowDeleteRequests", "description": "Resource for monitoring long running deletion of flows and flow segments."},
        {"name": "Webhooks", "description": "Configures webhooks to deliver notifications externally. Optional, and may not be implemented"},
        {"name": "Authentication", "description": "Authentication and authorization endpoints"}
    ]
)

# Initialize telemetry
telemetry_manager.initialize("tams-api", "7.0.0")
telemetry_manager.instrument_fastapi(app)

# Add telemetry middleware
app.middleware("http")(telemetry_middleware)

# Set custom OpenAPI schema
app.openapi = custom_openapi

# Register modular routers
app.include_router(flows_router)
app.include_router(segments_router)
app.include_router(sources_router)
app.include_router(objects_router)
app.include_router(analytics_router)

# Authentication endpoints
@app.post("/auth/login", tags=["Authentication"])
async def login(credentials=Depends(login_basic)):
    """Login with basic authentication and return a bearer token"""
    return credentials

@app.post("/auth/logout", tags=["Authentication"])
async def logout_endpoint(current_user=Depends(require_authentication)):
    """Logout and invalidate the current token"""
    return await logout(current_user)

# OpenAPI JSON endpoint
@app.get("/openapi.json")
async def get_openapi_json():
    """Get OpenAPI specification as JSON"""
    return JSONResponse(content=app.openapi())

# Service endpoints
@app.head("/")
async def head_root():
    """Return root path headers"""
    return {}

@app.get("/", response_model=List[str])
async def get_root():
    """List of paths available from this API"""
    return ["service", "flows", "sources", "flow-delete-requests", "openapi.json"]

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
        api_version="7.0",
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

# Storage backends endpoint
@app.head("/service/storage-backends")
async def head_storage_backends():
    """Return storage backends path headers"""
    return {}

@app.get("/service/storage-backends", response_model=StorageBackendsResponse)
async def get_storage_backends(
    store: VASTStore = Depends(get_vast_store)
):
    """Get storage backends information"""
    try:
        # In a real implementation, this would return actual storage backend info
        # For now, return a default storage backend
        storage_backends = [
            StorageBackend(
                storage_id=uuid4(),
                label="default",
                description="Default HTTP object store",
                type="http_object_store"
            )
        ]
        return StorageBackendsResponse(data=StorageBackendsList(storage_backends=storage_backends))
        
    except Exception as e:
        logger.error(f"Failed to get storage backends: {e}")
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
        return DeletionRequestsResponse(data=DeletionRequestsList(requests=requests))
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
    return enhanced_health_check()

# Prometheus metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
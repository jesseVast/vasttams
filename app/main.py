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
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import uvicorn
from uuid import UUID

from .models.models import (
    Service, ServiceResponse, Source, SourcesResponse, Flow, FlowsResponse,
    FlowSegment, Object, Webhook, WebhookPost, WebhooksResponse,
    FlowStoragePost, FlowStorage, DeletionRequest, DeletionRequestsResponse,
    SourceFilters, FlowFilters, FlowDetailFilters, PagingInfo, Tags, MediaStore, EventStreamMechanism, 
    DeletionRequestsList, StorageBackend, StorageBackendsList, HttpRequest, MediaObject
)
from .storage.vast_store import VASTStore
from .core.config import get_settings, update_settings
from .core.utils import log_pydantic_validation_error
from .api.segments import SegmentManager
from .api.flows import FlowManager
from .api.sources import SourceManager
from .api.objects import ObjectManager
from .api.flows_router import router as flows_router
from .api.segments_router import router as segments_router
from .api.sources_router import router as sources_router
from .api.objects_router import router as objects_router

from .core.dependencies import get_vast_store, set_vast_store
from .core.telemetry import telemetry_manager, telemetry_middleware, metrics_endpoint, enhanced_health_check

# Import simplified logging (auto-configures on import)
from .core import simple_logging

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
    # Initialize VAST store with single endpoint
    
    vast_store = VASTStore(
        endpoint=settings.vast_endpoint,  # Use single endpoint
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema
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
    # Always use auto-generated schema to include all registered routes
    try:
        app.openapi_schema = get_openapi(
            title="TAMS API",
            version="7.0",
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
    version="7.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Initialize telemetry
telemetry_manager.initialize("tams-api", "7.0")
telemetry_manager.instrument_fastapi(app)

# Add telemetry middleware
app.middleware("http")(telemetry_middleware)

# Set custom OpenAPI schema
app.openapi = custom_openapi

# Add global validation exception handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Global handler for Pydantic validation errors from FastAPI
    
    This catches validation errors that occur during request parsing
    and logs them with detailed information for troubleshooting.
    """
    
    # Extract request details for context
    method = request.method
    url = str(request.url)
    
    # Try to get the request body for logging
    request_body = None
    try:
        # Note: request.body() can only be called once, so this might not work
        # in all cases, but we'll try
        if hasattr(request, '_body'):
            request_body = request._body
        elif method in ["POST", "PUT", "PATCH"]:
            # Attempt to read body, but it might be consumed already
            try:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        request_body = body_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        request_body = f"Binary data (length: {len(body_bytes)})"
            except Exception as body_error:
                request_body = f"Unable to read request body: {str(body_error)}"
    except Exception as body_error:
        request_body = f"Error reading request body: {str(body_error)}"
    
    # Log the detailed validation error directly from the RequestValidationError
    error_msg = log_pydantic_validation_error(
        error=exc,
        context=f"{method} {url}",
        input_data={"request_body": request_body} if request_body else None,
        model_name="Request"
    )
    
    # Return FastAPI's standard validation error response
    # Ensure we only return serializable data
    try:
        # Convert exc.errors() to a serializable format
        serializable_errors = []
        for error in exc.errors():
            serializable_error = {
                "loc": error.get("loc", []),
                "msg": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
                "input": str(error.get("input", "")) if error.get("input") is not None else None
            }
            serializable_errors.append(serializable_error)
        
        return JSONResponse(
            status_code=422,
            content={
                "detail": serializable_errors,
                "message": error_msg
            }
        )
    except Exception as response_error:
        # Fallback to a simple error response if serialization fails
        logger.error("Error creating response: %s", str(response_error))
        return JSONResponse(
            status_code=422,
            content={
                "detail": [{"msg": "Validation error", "type": "validation_error"}],
                "message": error_msg
            }
        )

# Register modular routers
app.include_router(flows_router)
app.include_router(segments_router)
app.include_router(sources_router)
app.include_router(objects_router)

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

# Storage backends endpoints
@app.head("/service/storage-backends")
async def head_storage_backends():
    """Return storage backends path headers"""
    return {}

@app.get("/service/storage-backends", response_model=List[StorageBackend])
async def list_storage_backends():
    """Provide information about the storage backends available on this service instance"""
    # For now, return our S3-compatible backend configuration
    # In a real implementation, this would be configured at deployment time
    return [
        StorageBackend(
            id="550e8400-e29b-41d4-a716-446655440000",
            store_type="http_object_store",
            provider="VAST Data",
            store_product="VAST S3 Compatible Store",
            region="us-west-1",
            label="Primary VAST Storage",
            default_storage=True
        )
    ]

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
            events=webhook.events,
            # Ownership fields for TAMS API v7.0 compliance
            owner_id=webhook.owner_id,
            created_by=webhook.created_by,
            created=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Analytics endpoints
@app.head("/flow-usage")
async def head_flow_usage():
    """Return flow usage analytics path headers"""
    return {}

@app.get("/flow-usage")
async def get_flow_usage(
    store: VASTStore = Depends(get_vast_store),
    start_time: Optional[str] = Query(None, description="Start time for analytics (ISO 8601 format)"),
    end_time: Optional[str] = Query(None, description="End time for analytics (ISO 8601 format)"),
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    format: Optional[str] = Query(None, description="Filter by flow format")
):
    """Get flow usage analytics"""
    try:
        analytics_params = {}
        if start_time:
            analytics_params['start_time'] = start_time
        if end_time:
            analytics_params['end_time'] = end_time
        if source_id:
            analytics_params['source_id'] = source_id
        if format:
            analytics_params['format'] = format
            
        result = await store.analytics_query('flow_usage', **analytics_params)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get flow usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.head("/storage-usage")
async def head_storage_usage():
    """Return storage usage analytics path headers"""
    return {}

@app.get("/storage-usage")
async def get_storage_usage(
    store: VASTStore = Depends(get_vast_store),
    start_time: Optional[str] = Query(None, description="Start time for analytics (ISO 8601 format)"),
    end_time: Optional[str] = Query(None, description="End time for analytics (ISO 8601 format)"),
    storage_backend_id: Optional[str] = Query(None, description="Filter by storage backend ID")
):
    """Get storage usage analytics"""
    try:
        analytics_params = {}
        if start_time:
            analytics_params['start_time'] = start_time
        if end_time:
            analytics_params['end_time'] = end_time
        if storage_backend_id:
            analytics_params['storage_backend_id'] = storage_backend_id
            
        result = await store.analytics_query('storage_usage', **analytics_params)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get storage usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.head("/time-range-analysis")
async def head_time_range_analysis():
    """Return time range analysis path headers"""
    return {}

@app.get("/time-range-analysis")
async def get_time_range_analysis(
    store: VASTStore = Depends(get_vast_store),
    start_time: Optional[str] = Query(None, description="Start time for analysis (ISO 8601 format)"),
    end_time: Optional[str] = Query(None, description="End time for analysis (ISO 8601 format)"),
    flow_id: Optional[str] = Query(None, description="Filter by flow ID"),
    source_id: Optional[str] = Query(None, description="Filter by source ID")
):
    """Get time range analysis for flows and segments"""
    try:
        analytics_params = {}
        if start_time:
            analytics_params['start_time'] = start_time
        if end_time:
            analytics_params['end_time'] = end_time
        if flow_id:
            analytics_params['flow_id'] = flow_id
        if source_id:
            analytics_params['source_id'] = source_id
            
        result = await store.analytics_query('time_range_analysis', **analytics_params)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get time range analysis: {e}")
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
@app.head("/health")
async def health_check_head():
    """Health check endpoint HEAD method"""
    return {}

@app.options("/health")
async def health_check_options():
    """Health check endpoint OPTIONS method for CORS preflight"""
    return {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return enhanced_health_check()

# Prometheus metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()

# Configuration management endpoints
@app.get("/config/async-deletion-threshold")
async def get_async_deletion_threshold():
    """Get current async deletion threshold"""
    settings = get_settings()
    return {
        "async_deletion_threshold": settings.async_deletion_threshold,
        "description": "Threshold for async deletion (number of segments). Flows with more segments than this will use async deletion."
    }

@app.put("/config/async-deletion-threshold")
async def update_async_deletion_threshold(threshold: int):
    """Update async deletion threshold at runtime
    
    Args:
        threshold (int): New threshold value (must be >= 1)
        
    Returns:
        dict: Confirmation of the update
    """
    if threshold < 1:
        raise HTTPException(status_code=400, detail="Async deletion threshold must be at least 1")
    
    update_settings(async_deletion_threshold=threshold)
    
    return {
        "message": f"Async deletion threshold updated to {threshold} segments",
        "async_deletion_threshold": threshold
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
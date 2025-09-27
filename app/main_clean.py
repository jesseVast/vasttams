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

from .models import (
    Service, ServiceResponse, Source, SourcesResponse, Flow, FlowsResponse,
    FlowSegment, Object, Webhook, WebhookPost, WebhooksResponse,
    FlowStoragePost, FlowStorage, DeletionRequest, DeletionRequestsResponse,
    SourceFilters, FlowFilters, FlowDetailFilters, PagingInfo, Tags, MediaStore, EventStreamMechanism, 
    DeletionRequestsList, StorageBackend, StorageBackendsList, HttpRequest, MediaObject
)

# Storage now handled by storage service architecture
from .core.config import get_settings, update_settings
from .core.utils import log_pydantic_validation_error
from .api.flows_router import router as flows_router
from .api.segments_router import router as segments_router
from .api.sources_router import router as sources_router
from .api.objects_router import router as objects_router
from .api.service_router import router as service_router
from .api.deletion_requests_router import router as deletion_requests_router
from .api.analytics_router import router as analytics_router

from .core.dependencies import get_vast_db, get_s3_client
from .core.telemetry import telemetry_manager, telemetry_middleware, metrics_endpoint, enhanced_health_check

# Import simplified logging (auto-configures on import)
from .core import simple_logging

logger = logging.getLogger(__name__)

# Global VAST store instance (legacy - now using storage service)
vast_store = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    global vast_store
    try:
        logger.info("Starting TAMS API...")
        
        # Initialize telemetry
        telemetry_manager.initialize()
        logger.info("Telemetry initialized")
        
        # Initialize storage service (handled by dependency injection)
        logger.info("Storage service initialized via dependency injection")
        
        logger.info("TAMS API startup complete")
        yield
        
    except Exception as e:
        logger.error("Failed to start TAMS API: %s", e)
        raise
    finally:
        # Shutdown
        logger.info("Shutting down TAMS API...")
        
        if vast_store:
            await vast_store.close()
            logger.info("VAST store closed")
        
        # Cleanup telemetry
        telemetry_manager.cleanup()
        logger.info("Telemetry cleaned up")
        
        logger.info("TAMS API shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="TAMS API",
    description="Time-addressable Media Store API - BBC TAMS 7.0 Implementation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add telemetry middleware
app.middleware("http")(telemetry_middleware)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="TAMS API",
        version="1.0.0",
        description="Time-addressable Media Store API - BBC TAMS 7.0 Implementation",
        routes=app.routes,
    )
    
    # Add custom tags
    openapi_schema["tags"] = [
        {"name": "flows", "description": "Flow management operations"},
        {"name": "sources", "description": "Source management operations"},
        {"name": "objects", "description": "Media object operations"},
        {"name": "segments", "description": "Flow segment operations"},
        {"name": "service", "description": "Service information and configuration"},
        {"name": "deletion-requests", "description": "Deletion request management"},
        {"name": "analytics", "description": "Analytics and reporting"},
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    logger.error("HTTP Exception: %s - %s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages"""
    error_msg = log_pydantic_validation_error(
        error=exc,
        context=f"{request.method} {request.url.path}",
        input_data=exc.body,
        model_name="Request"
    )
    
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
app.include_router(service_router)
app.include_router(deletion_requests_router)
app.include_router(analytics_router)

# OpenAPI JSON endpoint
@app.get("/openapi.json")
async def get_openapi_json():
    """Get OpenAPI specification as JSON"""
    return JSONResponse(content=app.openapi())

# Root endpoints
@app.head("/")
async def head_root():
    """Return root path headers"""
    return {}

@app.get("/", response_model=List[str])
async def get_root():
    """List of paths available from this API"""
    return [
        "service", 
        "flows", 
        "sources", 
        "objects",
        "flow-delete-requests", 
        "analytics",
        "openapi.json",
        "docs",
        "redoc"
    ]

# Health and metrics endpoints
@app.head("/health")
async def head_health():
    """Return health check headers"""
    return {}

@app.get("/health")
async def health_check():
    """Enhanced health check with storage service status"""
    return await enhanced_health_check()

@app.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics"""
    return metrics_endpoint()

# Configuration endpoints
@app.get("/config/async-deletion-threshold")
async def get_async_deletion_threshold():
    """Get async deletion threshold configuration"""
    settings = get_settings()
    return {"async_deletion_threshold": settings.async_deletion_threshold}

@app.put("/config/async-deletion-threshold")
async def update_async_deletion_threshold(threshold: int):
    """Update async deletion threshold configuration"""
    if threshold < 0:
        raise HTTPException(status_code=400, detail="Threshold must be non-negative")
    
    update_settings({"async_deletion_threshold": threshold})
    return {"message": "Async deletion threshold updated", "threshold": threshold}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


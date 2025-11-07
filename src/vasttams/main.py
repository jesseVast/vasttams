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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import uvicorn
from uuid import UUID

# Import models from their resource modules
from .flows.models import Flow
from .sources.models import Source
from .segments.models import FlowSegment
from .objects.models import Object
from .service.models import Service
from .service.webhooks import Webhook, WebhookPost
from .service.deletion import DeletionRequest, DeletionRequestsList
from .service.storage_models import StorageBackend, StorageBackendsList

# Import shared/common models
from .common.models import Tags, EventStreamMechanism, HttpRequest
from .service.storage_models import MediaObject, FlowStoragePost, FlowStorage
from .common.filters import SourceFilters, FlowFilters, FlowDetailFilters
from .common.responses import ServiceResponse, SourcesResponse, FlowsResponse, WebhooksResponse, PagingInfo

# Storage now handled by storage service architecture
from .core.config import get_settings, update_settings
from .core.utils import log_pydantic_validation_error
from .flows.router import router as flows_router
from .segments.router import router as segments_router
from .sources.router import router as sources_router
from .objects.router import router as objects_router
from .service.router import router as service_router
from .storagebackends.router import router as storage_backends_router
from .auth.router import router as auth_router, login_router, users_router
from .webhooks.router import router as webhooks_router
from .hls.router import router as hls_router
from .analytics.router import router as analytics_router

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
        
        # Initialize storage service and verify tables
        from .core.dependencies import get_vast_db
        from .common.storage.table_initializer import TAMSTableInitializer
        
        vast_db = get_vast_db()
        if vast_db:
            table_initializer = TAMSTableInitializer(vast_db)
            
            # Verify tables exist, create if missing
            table_status = await table_initializer.verify_tables_exist()
            missing_tables = [name for name, exists in table_status.items() if not exists]
            
            if missing_tables:
                logger.warning(f"Missing tables detected: {missing_tables}")
                logger.info("Attempting to create missing tables...")
                
                # Create only missing tables
                results = await table_initializer.initialize_all_tables(force_recreate=False)
                successful = sum(1 for success in results.values() if success)
                total = len(results)
                
                if successful == total:
                    logger.info("✅ All missing tables created successfully")
                else:
                    failed = [name for name, success in results.items() if not success]
                    logger.error(f"❌ Failed to create tables: {failed}")
            else:
                logger.info("✅ All required tables exist")
            
            # Initialize default users if they don't exist
            try:
                from .auth.user_service import UserService
                from .auth.models import UserRole
                
                user_service = UserService(vast_db)
                default_users = [
                    ("admin", UserRole.ADMIN),
                    ("editor", UserRole.EDITOR),
                    ("viewer", UserRole.VIEWER)
                ]
                
                logger.info("Checking for default users...")
                for username, role in default_users:
                    existing_user = await user_service.get_user_by_username(username)
                    if not existing_user:
                        logger.info(f"Creating default user: {username} with role {role.value}")
                        await user_service.create_user(username, "vastdata", role)
                    else:
                        logger.debug(f"Default user {username} already exists")
                
                logger.info("✅ Default users verified")
            except Exception as e:
                logger.warning(f"Could not initialize default users: {e}")
            
            # Initialize storage backends from config if none exist
            try:
                from .storagebackends.service import StorageBackendService
                settings = get_settings()
                backend_service = StorageBackendService(vast_db, get_s3_client())
                existing = await backend_service.get_storage_backends()
                
                if not existing:
                    # Check if storage_backends are defined in config
                    storage_backends_config = getattr(settings, 'storage_backends_config', None)
                    
                    if storage_backends_config:
                        # Initialize all backends from config
                        from .storagebackends.models import StorageBackendPost
                        logger.info(f"Initializing {len(storage_backends_config)} storage backend(s) from config...")
                        for backend_config in storage_backends_config:
                            # Extract required fields
                            backend_post = StorageBackendPost(
                                label=backend_config.get('label', 'unnamed-backend'),
                                store_type=backend_config.get('store_type', 'http_object_store'),
                                provider=backend_config.get('provider', 'minio'),
                                store_product=backend_config.get('store_product', 'minio'),
                                region=backend_config.get('region'),
                                availability_zone=backend_config.get('availability_zone'),
                                endpoint_url=backend_config.get('endpoint_url'),
                                access_key=backend_config.get('access_key'),
                                secret_key=backend_config.get('secret_key'),
                                bucket_name=backend_config.get('bucket_name'),
                                root_path=backend_config.get('root_path'),
                                use_ssl=backend_config.get('use_ssl', False),
                                default_storage=backend_config.get('default_storage', False)
                            )
                            created = await backend_service.create_storage_backend(backend_post)
                            logger.info(f"✅ Created storage backend: {created.id} ({created.label})")
                        logger.info("✅ All storage backends initialized from config")
                    elif settings.s3_endpoint_url and settings.s3_bucket_name:
                        # Fallback to legacy S3 config
                        from .storagebackends.models import StorageBackendPost
                        logger.info("No storage backends found. Creating default from S3 config...")
                        backend_post = StorageBackendPost(
                            label="default-s3",
                            store_type="http_object_store",
                            provider=getattr(settings, 's3_provider', 'minio'),
                            store_product=getattr(settings, 's3_store_product', 'minio'),
                            region=settings.s3_region,
                            availability_zone=None,
                            endpoint_url=settings.s3_endpoint_url,
                            access_key=settings.s3_access_key_id,
                            secret_key=settings.s3_secret_access_key,
                            bucket_name=getattr(settings, 's3_bucket_name', None),
                            root_path=getattr(settings, 's3_root_path', None),
                            use_ssl=getattr(settings, 's3_use_ssl', False),
                            default_storage=True
                        )
                        await backend_service.create_storage_backend(backend_post)
                        logger.info("✅ Default storage backend created from legacy S3 config")
                    else:
                        logger.info("No storage backends configured; skipping initialization")
                else:
                    logger.info("Storage backends already exist; skipping initialization")
            except Exception as e:
                logger.warning(f"Could not initialize storage backends: {e}")
        
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
        
        # Telemetry cleanup handled automatically
        logger.info("Telemetry cleanup handled automatically")
        
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
from .auth.core import AuthManager
from .auth.providers.jwt import JWTProvider
from .auth.providers.basic import BasicAuthProvider

_auth_manager = AuthManager()
_auth_manager.add_provider(JWTProvider())
vast_db = get_vast_db()
if vast_db:
    _auth_manager.add_provider(BasicAuthProvider(vast_store=vast_db))

from .auth.middleware import AuthMiddleware
auth_middleware = AuthMiddleware(_auth_manager, require_auth=False)
app.middleware("http")(auth_middleware)

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
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    # 401 errors are expected for unauthenticated requests, log at DEBUG level
    # 400-499 client errors are typically expected, log at WARNING level
    # 500+ server errors are unexpected, log at ERROR level
    if exc.status_code == 401:
        logger.debug("HTTP Exception: %s - %s", exc.status_code, exc.detail)
    elif 400 <= exc.status_code < 500:
        logger.warning("HTTP Exception: %s - %s", exc.status_code, exc.detail)
    else:
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

@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError):
    """Handle timeout errors - return 503 Service Unavailable when server is overloaded"""
    logger.warning("Request timeout for %s %s - server may be overloaded", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service temporarily unavailable - server is overloaded. Please retry later.",
            "status_code": 503,
            "error_code": "SERVICE_UNAVAILABLE"
        }
    )

@app.exception_handler(ConnectionError)
async def connection_exception_handler(request: Request, exc: ConnectionError):
    """Handle connection errors - return 503 Service Unavailable"""
    logger.error("Connection error for %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service temporarily unavailable - connection error. Please retry later.",
            "status_code": 503,
            "error_code": "SERVICE_UNAVAILABLE"
        }
    )

# Register modular routers
app.include_router(flows_router)
app.include_router(segments_router)
app.include_router(sources_router)
app.include_router(objects_router)
app.include_router(service_router)
app.include_router(storage_backends_router)
app.include_router(auth_router)
app.include_router(login_router)
app.include_router(users_router)
app.include_router(webhooks_router)
app.include_router(hls_router)
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
    return enhanced_health_check()

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

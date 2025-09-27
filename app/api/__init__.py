"""
API module for TAMS API
Contains all API routers and business logic
"""

from .flows_router import router as flows_router
from .segments_router import router as segments_router
from .sources_router import router as sources_router
from .objects_router import router as objects_router
from .service_router import router as service_router
from .deletion_requests_router import router as deletion_requests_router

__all__ = [
    "flows_router",
    "segments_router", 
    "sources_router",
    "objects_router",
    "service_router",
    "deletion_requests_router"
] 
"""
API module for TAMS API
Contains all API routers and business logic
"""

from .flows_router import router as flows_router
from .segments_router import router as segments_router
from .sources_router import router as sources_router
from .objects_router import router as objects_router
from .analytics_router import router as analytics_router

__all__ = [
    "flows_router",
    "segments_router", 
    "sources_router",
    "objects_router",
    "analytics_router"
] 
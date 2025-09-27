"""
TAMS API Models

This package contains all the Pydantic models for the TAMS API specification.
Models are organized by functionality for better maintainability.
"""

from .core import (
    Timestamp,
    TimeRange,
    Tags,
    CollectionItem,
    ContainerMapping,
    FlowCollectionItem,
    FlowCollection,
    EventStreamMechanism,
    HttpRequest,
    SegmentDuration,
)

from .sources import Source

from .flows import (
    FlowCore,
    VideoFlow,
    AudioFlow,
    ImageFlow,
    DataFlow,
    MultiFlow,
    Flow,
    VideoEssenceParameters,
    AudioEssenceParameters,
    ImageEssenceParameters,
    DataEssenceParameters,
)

from .segments import FlowSegment, GetUrl

from .service import Service

from .webhooks import Webhook, WebhookPost

from .storage import (
    StorageBackend,
    StorageBackendsList,
    MediaObject,
    PreAction,
    FlowStorage,
    FlowStoragePost,
)

from .objects import Object

from .deletion import DeletionRequest, DeletionRequestsList

from .responses import (
    PagingInfo,
    ServiceResponse,
    SourcesResponse,
    FlowsResponse,
    WebhooksResponse,
    DeletionRequestsResponse,
)

from .filters import SourceFilters, FlowFilters, FlowDetailFilters

from .legacy import (
    PathTemplateType,
    HierarchicalPath,
    PathSegment,
    HierarchicalPathResult,
)

__all__ = [
    # Core types
    "Timestamp",
    "TimeRange", 
    "Tags",
    "CollectionItem",
    "ContainerMapping",
    "FlowCollectionItem",
    "FlowCollection",
    "EventStreamMechanism",
    "HttpRequest",
    "SegmentDuration",
    
    # Sources
    "Source",
    
    # Flows
    "FlowCore",
    "VideoFlow",
    "AudioFlow", 
    "ImageFlow",
    "DataFlow",
    "MultiFlow",
    "Flow",
    "VideoEssenceParameters",
    "AudioEssenceParameters",
    "ImageEssenceParameters", 
    "DataEssenceParameters",
    
    # Segments
    "FlowSegment",
    "GetUrl",
    
    # Service
    "Service",
    
    # Webhooks
    "Webhook",
    "WebhookPost",
    
    # Storage
    "StorageBackend",
    "StorageBackendsList",
    "MediaObject",
    "PreAction",
    "FlowStorage",
    "FlowStoragePost",
    
    # Objects
    "Object",
    
    # Deletion
    "DeletionRequest",
    "DeletionRequestsList",
    
    # Responses
    "PagingInfo",
    "ServiceResponse",
    "SourcesResponse",
    "FlowsResponse",
    "WebhooksResponse",
    "DeletionRequestsResponse",
    
    # Filters
    "SourceFilters",
    "FlowFilters", 
    "FlowDetailFilters",
    
    # Legacy
    "PathTemplateType",
    "HierarchicalPath",
    "PathSegment",
    "HierarchicalPathResult",
]

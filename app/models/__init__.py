"""
BBC TAMS Models Package

This package contains all the data models used by the TAMS API.
"""

from .models import (
    # Core models
    Source, Flow, FlowSegment, Object, Service, StorageBackend, Tags,
    CollectionItem, FlowCollection, SourceCollection, SegmentDuration,
    
    # Event models
    Event, EventData, SourceEventData, FlowEventData, FlowSegmentEventData, 
    ObjectEventData, CollectionEventData, EventStreamMechanism,
    
    # Webhook models
    Webhook, WebhookPost, WebhooksResponse,
    
    # Request/Response models
    DeletionRequest, DeletionRequestsList, DeletionRequestsResponse,
    FlowStoragePost, FlowStorage, MediaStore, HierarchicalPath,
    FlowStorage, StorageBackendsList,
    
    # Utility models
    HttpRequest, PagingInfo, PreAction, MediaObject,
    SourceFilters, FlowFilters, FlowDetailFilters,
    
    # User and Auth models
    User, UserCreate, UserUpdate, UserPasswordChange,
    ApiToken, ApiTokenCreate, AuthLog,
    UsersResponse, ApiTokensResponse, AuthLogsResponse,
    
    # Flow type models
    VideoFlow, AudioFlow, DataFlow, ImageFlow, MultiFlow,
    
    # Response models
    ServiceResponse, SourcesResponse, FlowsResponse
)

__all__ = [
    # Core models
    "Source", "Flow", "FlowSegment", "Object", "Service", "StorageBackend", "Tags",
    "CollectionItem", "FlowCollection", "SourceCollection", "SegmentDuration",
    
    # Event models
    "Event", "EventData", "SourceEventData", "FlowEventData", "FlowSegmentEventData",
    "ObjectEventData", "CollectionEventData", "EventStreamMechanism",
    
    # Webhook models
    "Webhook", "WebhookPost", "WebhooksResponse",
    
    # Request/Response models
    "DeletionRequest", "DeletionRequestsList", "DeletionRequestsResponse",
    "FlowStoragePost", "FlowStorage", "MediaStore", "HierarchicalPath",
    "FlowStorage", "StorageBackendsList",
    
    # Utility models
    "HttpRequest", "PagingInfo", "PreAction", "MediaObject",
    "SourceFilters", "FlowFilters", "FlowDetailFilters",
    
    # User and Auth models
    "User", "UserCreate", "UserUpdate", "UserPasswordChange",
    "ApiToken", "ApiTokenCreate", "AuthLog",
    "UsersResponse", "ApiTokensResponse", "AuthLogsResponse",
    
    # Flow type models
    "VideoFlow", "AudioFlow", "DataFlow", "ImageFlow", "MultiFlow",
    
    # Response models
    "ServiceResponse", "SourcesResponse", "FlowsResponse"
] 
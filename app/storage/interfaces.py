"""
Storage Interface Definitions

This module defines the abstract interfaces for storage operations in the TAMS API.
These interfaces provide a contract for storage implementations and enable easy
testing and swapping of storage backends.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models import (
    Source, Flow, FlowSegment, Object, Service, StorageBackend,
    SourceFilters, FlowFilters, FlowDetailFilters,
    FlowStorage, FlowStoragePost, MediaObject,
    Tags, CollectionItem, TimeRange
)


class StorageInterface(ABC):
    """Abstract base class for TAMS storage operations"""
    
    # Source operations
    @abstractmethod
    async def get_sources(self, filters: SourceFilters) -> List[Source]:
        """Get sources with filtering"""
        pass
    
    @abstractmethod
    async def get_source(self, source_id: str) -> Optional[Source]:
        """Get a specific source by ID"""
        pass
    
    @abstractmethod
    async def create_source(self, source: Source) -> bool:
        """Create a new source"""
        pass
    
    @abstractmethod
    async def update_source(self, source_id: str, source: Source) -> bool:
        """Update an existing source"""
        pass
    
    @abstractmethod
    async def delete_source(self, source_id: str, cascade: bool = True) -> bool:
        """Delete a source"""
        pass
    
    # Flow operations
    @abstractmethod
    async def get_flows(self, filters: FlowFilters) -> List[Flow]:
        """Get flows with filtering"""
        pass
    
    @abstractmethod
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get a specific flow by ID"""
        pass
    
    @abstractmethod
    async def create_flow(self, flow: Flow) -> bool:
        """Create a new flow"""
        pass
    
    @abstractmethod
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """Update an existing flow"""
        pass
    
    @abstractmethod
    async def delete_flow(self, flow_id: str) -> bool:
        """Delete a flow"""
        pass
    
    # Flow segment operations
    @abstractmethod
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> List[FlowSegment]:
        """Get flow segments with optional timerange filtering"""
        pass
    
    @abstractmethod
    async def create_flow_segment(self, flow_id: str, segment: FlowSegment) -> bool:
        """Create a new flow segment"""
        pass
    
    @abstractmethod
    async def delete_flow_segments(self, flow_id: str, timerange: Optional[str] = None) -> bool:
        """Delete flow segments"""
        pass
    
    # Object operations
    @abstractmethod
    async def get_object(self, object_id: str) -> Optional[Object]:
        """Get a specific object by ID"""
        pass
    
    @abstractmethod
    async def create_object(self, obj: Object) -> bool:
        """Create a new object"""
        pass
    
    @abstractmethod
    async def delete_object(self, object_id: str) -> bool:
        """Delete an object"""
        pass
    
    # Storage allocation operations
    @abstractmethod
    async def create_flow_storage(self, flow_id: str, storage_request: FlowStoragePost) -> Optional[FlowStorage]:
        """Create storage allocation for a flow"""
        pass
    
    # Tag operations
    @abstractmethod
    async def get_source_tags(self, source_id: str) -> Optional[Tags]:
        """Get source tags"""
        pass
    
    @abstractmethod
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """Update source tags"""
        pass
    
    @abstractmethod
    async def get_source_tag(self, source_id: str, name: str) -> Optional[str]:
        """Get a specific source tag"""
        pass
    
    @abstractmethod
    async def update_source_tag(self, source_id: str, name: str, value: str) -> bool:
        """Update a specific source tag"""
        pass
    
    @abstractmethod
    async def delete_source_tag(self, source_id: str, name: str) -> bool:
        """Delete a specific source tag"""
        pass
    
    # Collection operations
    @abstractmethod
    async def get_source_collections(self, source_id: str) -> List[CollectionItem]:
        """Get source collections"""
        pass
    
    @abstractmethod
    async def add_source_to_collection(self, collection_id: str, source_id: str, label: str, description: str) -> bool:
        """Add source to collection"""
        pass
    
    @abstractmethod
    async def remove_source_from_collection(self, collection_id: str, source_id: str) -> bool:
        """Remove source from collection"""
        pass
    
    # Service operations
    @abstractmethod
    async def get_service_info(self) -> Service:
        """Get service information"""
        pass
    
    @abstractmethod
    async def get_storage_backends(self) -> List[StorageBackend]:
        """Get storage backends"""
        pass
    
    # Utility operations
    @abstractmethod
    async def check_flow_read_only(self, flow_id: str) -> bool:
        """Check if a flow is read-only"""
        pass
    
    @abstractmethod
    async def generate_presigned_url(self, key: str, operation: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 operations"""
        pass
    
    # Analytics operations
    @abstractmethod
    async def get_analytics(self, query_type: str, **kwargs) -> Dict[str, Any]:
        """Get analytics data for the specified query type"""
        pass

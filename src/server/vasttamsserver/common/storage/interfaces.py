"""
Storage Interface Definitions

This module defines the abstract interfaces for storage operations in the TAMS API.
These interfaces provide a contract for storage implementations and enable easy
testing and swapping of storage backends.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

from ...sources.models import Source
from ...segments.models import FlowSegment
from ...objects.models import Object, ObjectInstance
from ...service.models import Service
from ...service.storage_models import StorageBackend, MediaObject, FlowStorage, FlowStoragePost
from ..filters import SourceFilters, FlowFilters, FlowDetailFilters
from ..models import Tags, CollectionItem, TimeRange

# Avoid circular import by using TYPE_CHECKING
if TYPE_CHECKING:
    from ...flows.models import Flow


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
    async def get_flows(self, filters: FlowFilters) -> List['Flow']:
        """Get flows with filtering"""
        pass
    
    @abstractmethod
    async def get_flow(self, flow_id: str, filters: Optional[FlowDetailFilters] = None) -> Optional['Flow']:
        """Get a specific flow by ID with optional filters for timerange handling"""
        pass
    
    @abstractmethod
    async def create_flow(self, flow: 'Flow') -> bool:
        """Create a new flow"""
        pass
    
    @abstractmethod
    async def update_flow(self, flow_id: str, flow: 'Flow') -> bool:
        """Update an existing flow"""
        pass
    
    @abstractmethod
    async def update_flow_description(self, flow_id: str, description: str) -> bool:
        """Update flow description only"""
        pass
    
    @abstractmethod
    async def delete_flow_description(self, flow_id: str) -> bool:
        """Delete flow description only"""
        pass
    
    @abstractmethod
    async def update_flow_label(self, flow_id: str, label: str) -> bool:
        """Update flow label only"""
        pass
    
    @abstractmethod
    async def delete_flow_label(self, flow_id: str) -> bool:
        """Delete flow label only"""
        pass
    
    @abstractmethod
    async def update_flow_read_only(self, flow_id: str, read_only: bool) -> bool:
        """Update flow read_only status only"""
        pass
    
    @abstractmethod
    async def delete_flow(self, flow_id: str, cascade: bool = True) -> bool:
        """Delete a flow"""
        pass
    
    # Flow segment operations
    @abstractmethod
    async def get_flow_segments(self, flow_id: str, timerange: Optional[str] = None, skip_get_urls_generation: bool = False) -> List[FlowSegment]:
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
    async def get_objects(self) -> List[Object]:
        """Get all objects"""
        pass
    
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
    
    # Object instance operations (TAMS 8.0)
    @abstractmethod
    async def create_object_instance(self, object_id: str, instance: ObjectInstance) -> bool:
        """Create a new object instance"""
        pass
    
    @abstractmethod
    async def list_object_instances(self, object_id: str) -> List[ObjectInstance]:
        """List all instances for an object"""
        pass
    
    @abstractmethod
    async def delete_object_instance(self, object_id: str, label: Optional[str] = None, storage_id: Optional[str] = None) -> bool:
        """Delete an object instance by label or storage_id"""
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
    
    # Flow tag methods
    @abstractmethod
    async def get_flow_tags(self, flow_id: str) -> Optional[Tags]:
        """Get flow tags"""
        pass
    
    @abstractmethod
    async def update_flow_tags(self, flow_id: str, tags: Tags) -> bool:
        """Update flow tags"""
        pass
    
    @abstractmethod
    async def update_flow_tag(self, flow_id: str, name: str, value: str) -> bool:
        """Update a specific flow tag"""
        pass
    
    @abstractmethod
    async def delete_flow_tag(self, flow_id: str, name: str) -> bool:
        """Delete a specific flow tag"""
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
    
    # Deletion request operations
    @abstractmethod
    async def get_deletion_requests(self) -> List[Dict[str, Any]]:
        """Get all deletion requests"""
        pass
    
    @abstractmethod
    async def get_deletion_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific deletion request by ID"""
        pass
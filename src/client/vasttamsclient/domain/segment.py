"""
TAMS Segment Domain Object

Encapsulates segment operations.
"""

from typing import Optional, Dict, Any
from .base import TAMSDomainObject
from ..api import segments as segment_api
from ..exceptions import TAMSClientError


class TAMSSegment(TAMSDomainObject):
    """TAMS Segment domain object."""
    
    def __init__(self, client, flow_id: str, segment_data: Dict[str, Any]):
        """
        Represent a TAMS segment.
        
        Args:
            client: TAMSClient instance
            flow_id: Flow ID this segment belongs to
            segment_data: Segment data dictionary
        """
        object_id = segment_data.get("object_id", "")
        super().__init__(client, object_id, segment_data)
        self._flow_id = flow_id
    
    @property
    def flow_id(self) -> str:
        """Get flow ID."""
        return self._flow_id
    
    @property
    def object_id(self) -> str:
        """Get object ID."""
        return self._id
    
    @property
    def timerange(self) -> Dict[str, Any]:
        """Get timerange."""
        return self._data.get("timerange", {})
    
    async def refresh(self):
        """Refresh segment data from server."""
        segments = await segment_api.list_segments(self._client, self._flow_id, {"object_id": self._id})
        if segments:
            self._data.update(segments[0])
        else:
            raise TAMSClientError(f"Segment {self._id} not found")
    
    async def delete(self) -> Optional[Dict[str, Any]]:
        """Delete segment.
        
        Returns:
            None if deletion completed synchronously
            Dict with deletion request info if async deletion was created (202 response)
        """
        return await segment_api.delete_segments(self._client, self._flow_id, {"object_id": self._id})
    
    async def update(self, **updates):
        """Update segment metadata."""
        # Note: TAMS API may have limited segment update capabilities
        self._data.update(updates)
        # Implementation depends on TAMS API support for segment updates


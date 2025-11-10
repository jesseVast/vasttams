"""
TAMS Deletion Request Domain Object

Encapsulates deletion request operations and provides fluent API.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from .base import TAMSDomainObject
from ..api import deletion_requests as deletion_request_api
from ..exceptions import TAMSClientError


class TAMSDeletionRequest(TAMSDomainObject):
    """TAMS Deletion Request domain object."""
    
    def __init__(self, client, id: str, deletion_request_data: Optional[Dict[str, Any]] = None):
        """
        Represent a TAMS deletion request.
        
        Args:
            client: TAMSClient instance
            id: Deletion request ID
            deletion_request_data: Optional deletion request data dictionary
        """
        super().__init__(client, id, deletion_request_data or {})
    
    @property
    def flow_id(self) -> str:
        """Get flow ID."""
        return self._data.get("flow_id", "")
    
    @property
    def status(self) -> str:
        """Get deletion request status."""
        return self._data.get("status", "unknown")
    
    @property
    def timerange_to_delete(self) -> Optional[Dict[str, Any]]:
        """Get timerange to delete."""
        return self._data.get("timerange_to_delete")
    
    @property
    def timerange_remaining(self) -> Optional[Dict[str, Any]]:
        """Get remaining timerange."""
        return self._data.get("timerange_remaining")
    
    @property
    def delete_flow(self) -> bool:
        """Get whether flow should be deleted."""
        return self._data.get("delete_flow", False)
    
    @property
    def created(self) -> Optional[datetime]:
        """Get creation timestamp."""
        created_str = self._data.get("created")
        if created_str:
            try:
                return datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            except:
                return None
        return None
    
    @property
    def updated(self) -> Optional[datetime]:
        """Get last update timestamp."""
        updated_str = self._data.get("updated")
        if updated_str:
            try:
                return datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            except:
                return None
        return None
    
    @property
    def error(self) -> Optional[Dict[str, Any]]:
        """Get error information if status is 'error'."""
        return self._data.get("error")
    
    async def refresh(self):
        """Refresh deletion request data from server."""
        deletion_request_data = await deletion_request_api.get_deletion_request(self._client, self._id)
        if deletion_request_data:
            self._data.update(deletion_request_data)
        else:
            raise TAMSClientError(f"Deletion request {self._id} not found")
    
    def is_done(self) -> bool:
        """Check if deletion request is done."""
        return self.status == "done"
    
    def is_error(self) -> bool:
        """Check if deletion request has error."""
        return self.status == "error"
    
    def is_in_progress(self) -> bool:
        """Check if deletion request is in progress."""
        return self.status in ("created", "started")


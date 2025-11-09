"""
TAMS Source Domain Object

Encapsulates source operations and provides fluent API.
"""

import uuid
from typing import Optional, Dict, Any, List, Union
from .base import TAMSDomainObject
from .flow import TAMSFlow
from ..api import sources as source_api
from ..api import tags as tag_api
from ..exceptions import TAMSClientError


class TAMSSource(TAMSDomainObject):
    """TAMS Source domain object."""
    
    def __init__(self, client, id: Optional[str] = None, **source_data):
        """
        Create or represent a TAMS source.
        
        Args:
            client: TAMSClient instance
            id: Optional source ID (if None, creates new source)
            **source_data: Source data (format, label, description, etc.)
        """
        if id is None:
            # Create new source
            if "format" not in source_data:
                raise ValueError("format is required for new source")
            if "id" not in source_data:
                source_data["id"] = str(uuid.uuid4())
        else:
            # Represent existing source
            source_data["id"] = id
        
        super().__init__(client, source_data["id"], source_data)
        self._created = id is None
    
    async def _ensure_created(self):
        """Ensure source is created on server."""
        if self._created:
            try:
                result = await source_api.create_source(self._client, self._data)
                self._data.update(result)
                self._created = False
            except Exception as e:
                raise TAMSClientError(f"Failed to create source: {e}")
    
    async def add_flow(self, flow: 'TAMSFlow') -> 'TAMSFlow':
        """
        Add a flow to this source.
        
        Args:
            flow: TAMSFlow instance (may be uncreated)
            
        Returns:
            TAMSFlow: Created flow instance
        """
        await self._ensure_created()
        flow._data["source_id"] = self._id
        await flow._ensure_created()
        return flow
    
    def TAMSFlow(self, format: str, codec: str, label: Optional[str] = None, **flow_data) -> 'TAMSFlow':
        """
        Create a new flow for this source (convenience method).
        
        Args:
            format: Flow format URN
            codec: Flow codec MIME type
            label: Optional flow label
            **flow_data: Additional flow data
            
        Returns:
            TAMSFlow: New flow instance (not yet created)
        """
        flow_data.update({
            "format": format,
            "codec": codec,
            "label": label
        })
        return TAMSFlow(self._client, source=self, **flow_data)
    
    async def get_flow(self, flow_id: str) -> Optional['TAMSFlow']:
        """Get a flow by ID."""
        from ..api import flows as flow_api
        flow_data = await flow_api.get_flow(self._client, flow_id)
        if flow_data:
            # Remove id from flow_data since we pass it as a keyword argument
            flow_data_copy = {k: v for k, v in flow_data.items() if k != "id"}
            return TAMSFlow(self._client, id=flow_id, **flow_data_copy)
        return None
    
    async def list_flows(self, **query_params) -> List['TAMSFlow']:
        """List flows for this source."""
        from ..api import flows as flow_api
        query_params["source_id"] = self._id
        flows_data = await flow_api.list_flows(self._client, query_params)
        result = []
        for f in flows_data:
            # Remove id from flow_data since we pass it as a keyword argument
            flow_id = f.pop("id", None)
            if flow_id:
                result.append(TAMSFlow(self._client, id=flow_id, **f))
        return result
    
    async def refresh(self):
        """Refresh source data from server."""
        source_data = await source_api.get_source(self._client, self._id)
        if source_data:
            self._data.update(source_data)
            # Clear tags cache since data may have changed
            self._tags_cache = None
        else:
            raise TAMSClientError(f"Source {self._id} not found")
    
    async def update(self, **updates):
        """Update source metadata using specific endpoints."""
        # Update label if provided
        if "label" in updates:
            await source_api.update_source_label(self._client, self._id, updates["label"])
            self._data["label"] = updates["label"]
        
        # Update description if provided
        if "description" in updates:
            await source_api.update_source_description(self._client, self._id, updates["description"])
            self._data["description"] = updates["description"]
        
        # Refresh to get any other updated fields
        await self.refresh()
        # Note: Tags cache cleared in refresh()
    
    async def delete(self):
        """Delete source."""
        await source_api.delete_source(self._client, self._id)
        # Remove from client cache
        if hasattr(self._client, '_cache') and "source" in self._client._cache:
            self._client._cache["source"].pop(self._id, None)
    
    async def get_tags(self, use_cache: bool = True) -> Dict[str, Union[str, List[str]]]:
        """
        Get all tags.
        
        Args:
            use_cache: If True, return cached tags if available
            
        Returns:
            Dict mapping tag names to values (string or list of strings)
        """
        # Return cached tags if available
        if use_cache and self._tags_cache is not None:
            return self._tags_cache
        
        # Fetch from server
        tags = await tag_api.get_tags(self._client, "source", self._id)
        # Cache the result (empty dict is valid, so we cache it)
        self._tags_cache = tags
        return tags
    
    async def get_tag(self, name: str, use_cache: bool = True) -> Optional[Union[str, List[str]]]:
        """
        Get a specific tag.
        
        Args:
            name: Tag name
            use_cache: If True, check cached tags first
            
        Returns:
            Tag value (string or list of strings) or None if not found
        """
        # Check cache first
        if use_cache and self._tags_cache is not None:
            return self._tags_cache.get(name)
        
        # Fetch from server
        value = await tag_api.get_tag(self._client, "source", self._id, name)
        # Update cache if we have one
        if self._tags_cache is not None:
            if value is None:
                self._tags_cache.pop(name, None)
            else:
                self._tags_cache[name] = value
        return value
    
    async def set_tag(self, name: str, value: Union[str, List[str]]):
        """
        Set or update a tag.
        
        Args:
            name: Tag name
            value: Tag value (string or list of strings)
        """
        await tag_api.set_tag(self._client, "source", self._id, name, value)
        # Update cache
        if self._tags_cache is None:
            self._tags_cache = {}
        self._tags_cache[name] = value
    
    async def delete_tag(self, name: str):
        """
        Delete a tag.
        
        Args:
            name: Tag name
        """
        await tag_api.delete_tag(self._client, "source", self._id, name)
        # Update cache
        if self._tags_cache is not None:
            self._tags_cache.pop(name, None)
    
    def clear_tags_cache(self):
        """Clear the tags cache (force refresh on next get_tags/get_tag call)."""
        self._tags_cache = None
    
    # Properties
    @property
    def format(self) -> str:
        return self._data.get("format", "")
    
    @property
    def label(self) -> Optional[str]:
        return self._data.get("label")
    
    @property
    def description(self) -> Optional[str]:
        return self._data.get("description")


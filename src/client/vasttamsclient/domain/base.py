"""
Base Domain Object

Base class for all TAMS domain objects.
"""

import asyncio
from typing import Any, Optional, Dict, Union, List


class TAMSDomainObject:
    """Base class for TAMS domain objects."""
    
    def __init__(self, client, id: str, data: Optional[dict] = None):
        """
        Initialize domain object.
        
        Args:
            client: TAMSClient instance
            id: Object ID
            data: Optional data dictionary
        """
        self._client = client
        self._id = id
        self._data = data or {}
        # Tag cache: None means not loaded, {} means loaded but empty, dict means cached
        self._tags_cache: Optional[Dict[str, Union[str, List[str]]]] = None
    
    @property
    def id(self) -> str:
        """Get object ID."""
        return self._id
    
    @property
    def client(self):
        """Get client instance."""
        return self._client
    
    def _sync_wrapper(self, coro):
        """Synchronous wrapper for async methods."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot use sync wrapper in async context. Use await instead.")
        except RuntimeError:
            pass
        return asyncio.run(coro)
    
    async def refresh(self):
        """Refresh object data from server."""
        raise NotImplementedError("Subclasses must implement refresh()")
    
    async def delete(self):
        """Delete object from server."""
        raise NotImplementedError("Subclasses must implement delete()")
    
    async def update(self, **updates):
        """Update object on server."""
        raise NotImplementedError("Subclasses must implement update()")


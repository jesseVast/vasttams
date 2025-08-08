"""
Dependencies module for TAMS API.
Contains dependency injection functions to avoid circular imports.
"""
from fastapi import HTTPException
from ..storage.vast_store import VASTStore

# Global VAST store instance
vast_store = None

def get_vast_store() -> VASTStore:
    """Get the global VAST store instance."""
    if vast_store is None:
        raise HTTPException(status_code=500, detail="VAST store not initialized")
    return vast_store

def set_vast_store(store: VASTStore):
    """Set the global VAST store instance."""
    global vast_store
    vast_store = store 
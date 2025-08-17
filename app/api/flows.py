"""
Flows submodule for TAMS API.
Handles flow-related operations and business logic.
"""
from typing import List, Optional, Dict
from fastapi import HTTPException
from datetime import datetime, timezone
from ..models.models import Flow, FlowsResponse, PagingInfo, FlowFilters, FlowDetailFilters, Tags
from ..storage.vast_store import VASTStore
import logging
import uuid

logger = logging.getLogger(__name__)

# Standalone functions for router use
async def get_flows(store: VASTStore, filters: FlowFilters) -> List[Flow]:
    """Get flows with filtering"""
    try:
        filter_dict = {}
        if filters.source_id:
            filter_dict['source_id'] = str(filters.source_id)
        if filters.timerange:
            filter_dict['timerange'] = filters.timerange
        if filters.format:
            filter_dict['format'] = filters.format
        if filters.codec:
            filter_dict['codec'] = filters.codec
        if filters.label:
            filter_dict['label'] = filters.label
        if filters.frame_width:
            filter_dict['frame_width'] = filters.frame_width
        if filters.frame_height:
            filter_dict['frame_height'] = filters.frame_height
        
        flows = await store.list_flows(filters=filter_dict, limit=filters.limit)
        return flows
    except Exception as e:
        logger.error("Failed to get flows: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

async def get_flow(store: VASTStore, flow_id: str, filters: Optional[FlowDetailFilters] = None) -> Optional[Flow]:
    """Get a specific flow by ID"""
    try:
        flow = await store.get_flow(flow_id)
        return flow
    except Exception as e:
        logger.error("Failed to get flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_flow(store: VASTStore, flow: Flow) -> bool:
    """Create a new flow"""
    try:
        now = datetime.now(timezone.utc)
        flow.created = now
        flow.updated = now
        success = await store.create_flow(flow)
        return success
    except Exception as e:
        logger.error("Failed to create flow: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

async def update_flow(store: VASTStore, flow_id: str, flow: Flow) -> Optional[Flow]:
    """Update a flow"""
    try:
        flow.updated = datetime.now(timezone.utc)
        success = await store.update_flow(flow_id, flow)
        if success:
            return flow
        return None
    except Exception as e:
        logger.error("Failed to update flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

async def delete_flow(store: VASTStore, flow_id: str, cascade: bool = True) -> bool:
    """Delete a flow (hard delete only - TAMS compliant)"""
    try:
        success = await store.delete_flow(flow_id, cascade=cascade)
        return success
    except Exception as e:
        logger.error("Failed to delete flow %s: %s", flow_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")

class FlowManager:
    """Manager for flow operations (create, retrieve, update, delete, etc.)."""
    def __init__(self, store: Optional[VASTStore] = None):
        self.store = store

    async def _check_flow_read_only(self, flow_id: str, store: Optional[VASTStore] = None) -> None:
        """
        Check if a flow is read-only and raise 403 Forbidden if it is.
        
        Args:
            flow_id: Flow ID to check
            store: VAST store instance
            
        Raises:
            HTTPException: 403 Forbidden if flow is read-only
            HTTPException: 404 Not Found if flow doesn't exist
        """
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        
        try:
            flow = await store.get_flow(flow_id)
            if not flow:
                raise HTTPException(status_code=404, detail="Flow not found")
            
            if flow.read_only:
                raise HTTPException(
                    status_code=403, 
                    detail="Forbidden. You do not have permission to modify this flow. It may be marked read-only."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to check flow read-only status for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def list_flows(self, filters: Dict, limit: int, store: Optional[VASTStore] = None) -> FlowsResponse:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            flows = await store.list_flows(filters=filters, limit=limit)
            paging = None
            if len(flows) == limit:
                paging = None  # PagingInfo can be added if needed
            return FlowsResponse(data=flows, paging=paging)
        except Exception as e:
            logger.error("Failed to list flows: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_flow(self, flow_id: str, store: Optional[VASTStore] = None) -> Flow:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            flow = await store.get_flow(flow_id)
            if not flow:
                raise HTTPException(status_code=404, detail="Flow not found")
            return flow
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_flow(self, flow: Flow, store: Optional[VASTStore] = None) -> Flow:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            now = datetime.now(timezone.utc)
            flow.created = now
            flow.updated = now
            success = await store.create_flow(flow)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create flow")
            return flow
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to create flow: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def update_flow(self, flow_id: str, flow: Flow, store: Optional[VASTStore] = None) -> Flow:
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            # Check if flow is read-only before updating
            await self._check_flow_read_only(flow_id, store)
            
            flow.updated = datetime.now(timezone.utc)
            success = await store.update_flow(flow_id, flow)
            if not success:
                raise HTTPException(status_code=404, detail="Flow not found")
            return flow
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to update flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def delete_flow(self, flow_id: str, store: Optional[VASTStore] = None, cascade: bool = True):
        store = store or self.store
        if store is None:
            raise HTTPException(status_code=500, detail="VAST store is not initialized")
        try:
            # Check if flow is read-only before deleting
            await self._check_flow_read_only(flow_id, store)
            
            success = await store.delete_flow(flow_id, cascade=cascade)
            if not success:
                raise HTTPException(status_code=404, detail="Flow not found")
            
            cascade_msg = " with cascade" if cascade else ""
            return {"message": f"Flow hard deleted{cascade_msg}"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to delete flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")



    async def get_tags(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Retrieve all tags for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            dict: Dictionary of tag names and values.
        """
        flow = await self.get_flow(flow_id, store)
        return flow.tags.root if flow.tags else {}

    async def get_tag(self, flow_id: str, name: str, store: Optional[VASTStore] = None):
        """
        Retrieve a specific tag for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            name (str): The tag name to retrieve.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            dict: The tag name and value.

        Raises:
            HTTPException: 404 if the tag is not found.
        """
        flow = await self.get_flow(flow_id, store)
        if not flow.tags or name not in flow.tags.root:
            raise HTTPException(status_code=404, detail="Tag not found")
        return {name: flow.tags.root[name]}

    async def update_tag(self, flow_id: str, name: str, value: str, store: Optional[VASTStore] = None):
        """
        Update or add a tag for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            name (str): The tag name to update or add.
            value (str): The new value for the tag.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object.
        """
        flow = await self.get_flow(flow_id, store)
        if not flow.tags:
            flow.tags = Tags({})
        flow.tags.root[name] = value
        return await self.update_flow(flow_id, flow, store)

    async def delete_tag(self, flow_id: str, name: str, store: Optional[VASTStore] = None):
        """
        Delete a tag from a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            name (str): The tag name to delete.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object.

        Raises:
            HTTPException: 404 if the tag is not found.
        """
        flow = await self.get_flow(flow_id, store)
        if not flow.tags or name not in flow.tags.root:
            raise HTTPException(status_code=404, detail="Tag not found")
        del flow.tags.root[name]
        return await self.update_flow(flow_id, flow, store)

    async def get_description(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Retrieve the description for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            dict: The description of the flow.
        """
        flow = await self.get_flow(flow_id, store)
        return {"description": flow.description}

    async def update_description(self, flow_id: str, description: str, store: Optional[VASTStore] = None):
        """
        Update the description for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            description (str): The new description for the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object.
        """
        flow = await self.get_flow(flow_id, store)
        flow.description = description
        return await self.update_flow(flow_id, flow, store)

    async def delete_description(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Delete the description for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object with description set to None.
        """
        flow = await self.get_flow(flow_id, store)
        flow.description = None
        return await self.update_flow(flow_id, flow, store)

    async def get_label(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Retrieve the label for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            dict: The label of the flow.
        """
        flow = await self.get_flow(flow_id, store)
        return {"label": flow.label}

    async def update_label(self, flow_id: str, label: str, store: Optional[VASTStore] = None):
        """
        Update the label for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            label (str): The new label for the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object.
        """
        flow = await self.get_flow(flow_id, store)
        flow.label = label
        return await self.update_flow(flow_id, flow, store)

    async def delete_label(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Delete the label for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object with label set to None.
        """
        flow = await self.get_flow(flow_id, store)
        flow.label = None
        return await self.update_flow(flow_id, flow, store)

    async def get_read_only(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Retrieve the read-only status for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            dict: The read-only status of the flow.
        """
        flow = await self.get_flow(flow_id, store)
        return {"read_only": flow.read_only}

    async def update_read_only(self, flow_id: str, read_only: bool, store: Optional[VASTStore] = None):
        """
        Update the read-only status for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            read_only (bool): The new read-only status for the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object.
        """
        flow = await self.get_flow(flow_id, store)
        flow.read_only = read_only
        return await self.update_flow(flow_id, flow, store)

    async def get_collection(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Retrieve the flow collection for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            dict: The flow collection of the flow.
        """
        flow = await self.get_flow(flow_id, store)
        return {"flow_collection": getattr(flow, 'flow_collection', [])}

    async def update_collection(self, flow_id: str, flow_collection: List[str], store: Optional[VASTStore] = None):
        """
        Update the flow collection for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            flow_collection (List[str]): The new flow collection for the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object.
        """
        flow = await self.get_flow(flow_id, store)
        setattr(flow, 'flow_collection', flow_collection)
        return await self.update_flow(flow_id, flow, store)

    async def delete_collection(self, flow_id: str, store: Optional[VASTStore] = None):
        """
        Delete the flow collection for a given flow.

        Args:
            flow_id (str): The unique identifier of the flow.
            store (Optional[VASTStore]): Optional VASTStore instance to use. Defaults to the manager's store.

        Returns:
            Flow: The updated flow object with flow_collection set to empty list.
        """
        flow = await self.get_flow(flow_id, store)
        setattr(flow, 'flow_collection', [])
        return await self.update_flow(flow_id, flow, store) 
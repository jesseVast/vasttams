"""
Flow Storage Service

This module handles all flow-related storage operations including
CRUD operations, filtering, and flow management.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from .interfaces import StorageInterface
from ..models import Flow, FlowFilters, FlowDetailFilters

logger = logging.getLogger(__name__)


class FlowStorageService:
    """Handles flow-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_flows(self, filters: FlowFilters) -> List[Flow]:
        """Get flows with filtering"""
        try:
            # Build query using vaststore
            query = self.vast_db.query("flows").select("*")
            
            # Add filters
            if filters.source_id:
                query = query.where(f"source_id = '{filters.source_id}'")
            if filters.label:
                query = query.where(f"label = '{filters.label}'")
            if filters.format:
                query = query.where(f"format = '{filters.format}'")
            
            # Add limit
            if filters.limit:
                query = query.limit(filters.limit)
            
            result = query.execute()
            
            # Convert to Flow objects
            flows = []
            for row in result:
                flow_data = dict(row)
                flows.append(Flow(**flow_data))
            
            return flows
        except Exception as e:
            logger.error("Failed to get flows: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get a specific flow by ID"""
        try:
            result = self.vast_db.query("flows").select("*").where(f"id = '{flow_id}'").execute()
            
            if not result or len(result) == 0:
                return None
            
            flow_data = dict(result[0])
            return Flow(**flow_data)
        except Exception as e:
            logger.error("Failed to get flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_flow(self, flow: Flow) -> bool:
        """Create a new flow"""
        try:
            now = datetime.now(timezone.utc)
            flow.created = now
            flow.metadata_updated = now
            flow.segments_updated = now
            
            flow_data = flow.model_dump()
            self.vast_db.insert_record("flows", flow_data)
            return True
        except Exception as e:
            logger.error("Failed to create flow: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow(self, flow_id: str, flow: Flow) -> bool:
        """Update an existing flow"""
        try:
            flow.metadata_updated = datetime.now(timezone.utc)
            flow_data = flow.model_dump()
            
            self.vast_db.query("flows").update().set(**flow_data).where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to update flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow(self, flow_id: str) -> bool:
        """Delete a flow"""
        try:
            # Delete flow segments first
            await self._delete_flow_segments(flow_id)
            
            # Delete flow
            self.vast_db.query("flows").delete().where(f"id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_flow_read_only(self, flow_id: str) -> bool:
        """Check if a flow is read-only"""
        try:
            result = self.vast_db.query("flows").select("read_only").where(f"id = '{flow_id}'").execute()
            if not result or len(result) == 0:
                return False
            
            return result[0].get('read_only', False)
        except Exception as e:
            logger.error("Failed to check flow read-only status for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _delete_flow_segments(self, flow_id: str) -> bool:
        """Delete flow segments for a flow"""
        try:
            self.vast_db.query("segments").delete().where(f"flow_id = '{flow_id}'").execute()
            return True
        except Exception as e:
            logger.error("Failed to delete flow segments for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")

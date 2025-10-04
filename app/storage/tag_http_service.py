"""
Tag HTTP Service

This module provides HTTP-aware wrapper methods for the generic tag service.
It handles HTTP exceptions and provides the interface expected by API endpoints.
"""

import logging
from typing import Optional, Dict, Any, List

from fastapi import HTTPException
from .tag_service import TagStorageService
from ..models import Tags

logger = logging.getLogger(__name__)


class TagHTTPService:
    """HTTP wrapper for the generic tag storage service"""
    
    def __init__(self, tag_service: TagStorageService):
        self.tag_service = tag_service
    
    # Source tag methods with HTTP exception handling
    async def get_source_tags(self, source_id: str) -> Optional[Tags]:
        """Get source tags with HTTP exception handling"""
        try:
            return await self.tag_service.get_source_tags(source_id)
        except Exception as e:
            logger.error("Failed to get source tags for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source_tags(self, source_id: str, tags: Tags) -> bool:
        """Update source tags with HTTP exception handling"""
        try:
            return await self.tag_service.update_source_tags(source_id, tags)
        except ValueError as e:
            # Tag validation errors
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to update source tags for %s: %s", source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_source_tag(self, source_id: str, name: str) -> Optional[str]:
        """Get a specific source tag with HTTP exception handling"""
        try:
            return await self.tag_service.get_source_tag(source_id, name)
        except Exception as e:
            logger.error("Failed to get source tag %s for %s: %s", name, source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_source_tag(self, source_id: str, name: str, value: str) -> bool:
        """Update a specific source tag with HTTP exception handling"""
        try:
            return await self.tag_service.update_source_tag(source_id, name, value)
        except ValueError as e:
            # Tag validation errors
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to update source tag %s for %s: %s", name, source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_source_tag(self, source_id: str, name: str) -> bool:
        """Delete a specific source tag with HTTP exception handling"""
        try:
            return await self.tag_service.delete_source_tag(source_id, name)
        except Exception as e:
            logger.error("Failed to delete source tag %s for %s: %s", name, source_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Flow tag methods with HTTP exception handling
    async def get_flow_tags(self, flow_id: str) -> Optional[Tags]:
        """Get flow tags with HTTP exception handling"""
        try:
            return await self.tag_service.get_flow_tags(flow_id)
        except Exception as e:
            logger.error("Failed to get flow tags for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_tags(self, flow_id: str, tags: Tags) -> bool:
        """Update flow tags with HTTP exception handling"""
        try:
            return await self.tag_service.update_flow_tags(flow_id, tags)
        except ValueError as e:
            # Tag validation errors
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to update flow tags for %s: %s", flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_flow_tag(self, flow_id: str, name: str, value: str) -> bool:
        """Update a specific flow tag with HTTP exception handling"""
        try:
            return await self.tag_service.update_flow_tag(flow_id, name, value)
        except ValueError as e:
            # Tag validation errors
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to update flow tag %s for %s: %s", name, flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_flow_tag(self, flow_id: str, name: str) -> bool:
        """Delete a specific flow tag with HTTP exception handling"""
        try:
            return await self.tag_service.delete_flow_tag(flow_id, name)
        except Exception as e:
            logger.error("Failed to delete flow tag %s for %s: %s", name, flow_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Generic entity tag methods with HTTP exception handling
    async def get_entity_tags(self, entity_type: str, entity_id: str) -> Optional[Tags]:
        """Get tags for any entity type with HTTP exception handling"""
        try:
            return await self.tag_service.get_entity_tags(entity_type, entity_id)
        except Exception as e:
            logger.error("Failed to get tags for %s %s: %s", entity_type, entity_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_entity_tags(self, entity_type: str, entity_id: str, tags: Tags) -> bool:
        """Update tags for any entity type with HTTP exception handling"""
        try:
            return await self.tag_service.update_entity_tags(entity_type, entity_id, tags)
        except ValueError as e:
            # Tag validation errors
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to update tags for %s %s: %s", entity_type, entity_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_entity_tag(self, entity_type: str, entity_id: str, name: str) -> Optional[str]:
        """Get a specific tag for any entity type with HTTP exception handling"""
        try:
            return await self.tag_service.get_entity_tag(entity_type, entity_id, name)
        except Exception as e:
            logger.error("Failed to get tag %s for %s %s: %s", name, entity_type, entity_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_entity_tag(self, entity_type: str, entity_id: str, name: str, value: str) -> bool:
        """Update a specific tag for any entity type with HTTP exception handling"""
        try:
            return await self.tag_service.update_entity_tag(entity_type, entity_id, name, value)
        except ValueError as e:
            # Tag validation errors
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to update tag %s for %s %s: %s", name, entity_type, entity_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_entity_tag(self, entity_type: str, entity_id: str, name: str) -> bool:
        """Delete a specific tag for any entity type with HTTP exception handling"""
        try:
            return await self.tag_service.delete_entity_tag(entity_type, entity_id, name)
        except Exception as e:
            logger.error("Failed to delete tag %s for %s %s: %s", name, entity_type, entity_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # Query and analytics methods with HTTP exception handling
    async def query_entities_by_tags(self, entity_type: str, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query entities by tag filters with HTTP exception handling"""
        try:
            return await self.tag_service.query_entities_by_tags(entity_type, tag_filters, limit)
        except Exception as e:
            logger.error("Failed to query %s by tags: %s", entity_type, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def query_sources_by_tags(self, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query sources by tag filters with HTTP exception handling"""
        try:
            return await self.tag_service.query_sources_by_tags(tag_filters, limit)
        except Exception as e:
            logger.error("Failed to query sources by tags: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def query_flows_by_tags(self, tag_filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query flows by tag filters with HTTP exception handling"""
        try:
            return await self.tag_service.query_flows_by_tags(tag_filters, limit)
        except Exception as e:
            logger.error("Failed to query flows by tags: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_tag_analytics(self, entity_type: str = "sources") -> Dict[str, Any]:
        """Get tag usage analytics with HTTP exception handling"""
        try:
            return await self.tag_service.get_tag_analytics(entity_type)
        except Exception as e:
            logger.error("Failed to get tag analytics for %s: %s", entity_type, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_standardized_tags(self) -> Dict[str, Any]:
        """Get standardized tag definitions with HTTP exception handling"""
        try:
            return await self.tag_service.get_standardized_tags()
        except Exception as e:
            logger.error("Failed to get standardized tags: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_tag_proposal(self, name: str, description: str, data_type: str,
                                justification: str, examples: List[str], proposed_by: str) -> Dict[str, Any]:
        """Create a new tag proposal with HTTP exception handling"""
        try:
            return await self.tag_service.create_tag_proposal(
                name, description, data_type, justification, examples, proposed_by
            )
        except Exception as e:
            logger.error("Failed to create tag proposal: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")


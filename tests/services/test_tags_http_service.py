#!/usr/bin/env python3
"""
Service Layer Tests for Tag HTTP Service

Tests common/tags/http_service.py to achieve coverage.
Tests HTTP exception handling and wrapper methods.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.common.tags.http_service import TagHTTPService
from vasttams.common.tags.service import TagStorageService
from vasttams.common.models import Tags
import uuid


# Helper to generate TAMS-compliant UUIDs
def tams_uuid():
    """Generate a TAMS-compliant UUID string"""
    return str(uuid.uuid4())


class TestTagHTTPService:
    """Test TagHTTPService HTTP wrapper methods"""
    
    @pytest.fixture
    def mock_tag_service(self):
        """Create a mock TagStorageService"""
        return Mock(spec=TagStorageService)
    
    @pytest.fixture
    def service(self, mock_tag_service):
        """Create TagHTTPService instance"""
        return TagHTTPService(mock_tag_service)
    
    @pytest.fixture
    def source_id(self):
        """Generate a TAMS-compliant source ID"""
        return tams_uuid()
    
    @pytest.fixture
    def flow_id(self):
        """Generate a TAMS-compliant flow ID"""
        return tams_uuid()
    
    # Source tag methods
    @pytest.mark.asyncio
    async def test_get_source_tags_success(self, service, mock_tag_service, source_id):
        """Test get_source_tags success"""
        tags = Tags({"environment": "production"})
        mock_tag_service.get_source_tags = AsyncMock(return_value=tags)
        
        result = await service.get_source_tags(source_id)
        
        assert result == tags
        mock_tag_service.get_source_tags.assert_called_once_with(source_id)
    
    @pytest.mark.asyncio
    async def test_get_source_tags_exception(self, service, mock_tag_service, source_id):
        """Test get_source_tags raises HTTPException on error"""
        mock_tag_service.get_source_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_source_tags(source_id)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_update_source_tags_success(self, service, mock_tag_service, source_id):
        """Test update_source_tags success"""
        tags = Tags({"environment": "production"})
        mock_tag_service.update_source_tags = AsyncMock(return_value=True)
        
        result = await service.update_source_tags(source_id, tags)
        
        assert result is True
        mock_tag_service.update_source_tags.assert_called_once_with(source_id, tags)
    
    @pytest.mark.asyncio
    async def test_update_source_tags_validation_error(self, service, mock_tag_service, source_id):
        """Test update_source_tags raises HTTPException on validation error"""
        tags = Tags({"invalid!tag": "value"})
        mock_tag_service.update_source_tags = AsyncMock(side_effect=ValueError("Invalid tag name"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_source_tags(source_id, tags)
        
        assert exc_info.value.status_code == 400
        assert "Invalid tag name" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_source_tags_exception(self, service, mock_tag_service, source_id):
        """Test update_source_tags raises HTTPException on error"""
        tags = Tags({"environment": "production"})
        mock_tag_service.update_source_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_source_tags(source_id, tags)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_source_tag_success(self, service, mock_tag_service, source_id):
        """Test get_source_tag success"""
        mock_tag_service.get_source_tag = AsyncMock(return_value="production")
        
        result = await service.get_source_tag(source_id, "environment")
        
        assert result == "production"
        mock_tag_service.get_source_tag.assert_called_once_with(source_id, "environment")
    
    @pytest.mark.asyncio
    async def test_get_source_tag_exception(self, service, mock_tag_service, source_id):
        """Test get_source_tag raises HTTPException on error"""
        mock_tag_service.get_source_tag = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_source_tag(source_id, "environment")
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_update_source_tag_success(self, service, mock_tag_service, source_id):
        """Test update_source_tag success"""
        mock_tag_service.update_source_tag = AsyncMock(return_value=True)
        
        result = await service.update_source_tag(source_id, "environment", "production")
        
        assert result is True
        mock_tag_service.update_source_tag.assert_called_once_with(source_id, "environment", "production")
    
    @pytest.mark.asyncio
    async def test_update_source_tag_validation_error(self, service, mock_tag_service, source_id):
        """Test update_source_tag raises HTTPException on validation error"""
        mock_tag_service.update_source_tag = AsyncMock(side_effect=ValueError("Invalid tag name"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_source_tag(source_id, "invalid!tag", "value")
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_update_source_tag_exception(self, service, mock_tag_service, source_id):
        """Test update_source_tag raises HTTPException on error"""
        mock_tag_service.update_source_tag = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_source_tag(source_id, "environment", "production")
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_delete_source_tag_success(self, service, mock_tag_service, source_id):
        """Test delete_source_tag success"""
        mock_tag_service.delete_source_tag = AsyncMock(return_value=True)
        
        result = await service.delete_source_tag(source_id, "environment")
        
        assert result is True
        mock_tag_service.delete_source_tag.assert_called_once_with(source_id, "environment")
    
    @pytest.mark.asyncio
    async def test_delete_source_tag_exception(self, service, mock_tag_service, source_id):
        """Test delete_source_tag raises HTTPException on error"""
        mock_tag_service.delete_source_tag = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_source_tag(source_id, "environment")
        
        assert exc_info.value.status_code == 500
    
    # Flow tag methods
    @pytest.mark.asyncio
    async def test_get_flow_tags_success(self, service, mock_tag_service, flow_id):
        """Test get_flow_tags success"""
        tags = Tags({"format": "video"})
        mock_tag_service.get_flow_tags = AsyncMock(return_value=tags)
        
        result = await service.get_flow_tags(flow_id)
        
        assert result == tags
        mock_tag_service.get_flow_tags.assert_called_once_with(flow_id)
    
    @pytest.mark.asyncio
    async def test_get_flow_tags_exception(self, service, mock_tag_service, flow_id):
        """Test get_flow_tags raises HTTPException on error"""
        mock_tag_service.get_flow_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_flow_tags(flow_id)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_update_flow_tags_success(self, service, mock_tag_service, flow_id):
        """Test update_flow_tags success"""
        tags = Tags({"format": "video"})
        mock_tag_service.update_flow_tags = AsyncMock(return_value=True)
        
        result = await service.update_flow_tags(flow_id, tags)
        
        assert result is True
        mock_tag_service.update_flow_tags.assert_called_once_with(flow_id, tags)
    
    @pytest.mark.asyncio
    async def test_update_flow_tags_validation_error(self, service, mock_tag_service, flow_id):
        """Test update_flow_tags raises HTTPException on validation error"""
        tags = Tags({"invalid!tag": "value"})
        mock_tag_service.update_flow_tags = AsyncMock(side_effect=ValueError("Invalid tag name"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_flow_tags(flow_id, tags)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_update_flow_tag_success(self, service, mock_tag_service, flow_id):
        """Test update_flow_tag success"""
        mock_tag_service.update_flow_tag = AsyncMock(return_value=True)
        
        result = await service.update_flow_tag(flow_id, "format", "video")
        
        assert result is True
        mock_tag_service.update_flow_tag.assert_called_once_with(flow_id, "format", "video")
    
    @pytest.mark.asyncio
    async def test_update_flow_tag_validation_error(self, service, mock_tag_service, flow_id):
        """Test update_flow_tag raises HTTPException on validation error"""
        mock_tag_service.update_flow_tag = AsyncMock(side_effect=ValueError("Invalid tag name"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_flow_tag(flow_id, "invalid!tag", "value")
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_delete_flow_tag_success(self, service, mock_tag_service, flow_id):
        """Test delete_flow_tag success"""
        mock_tag_service.delete_flow_tag = AsyncMock(return_value=True)
        
        result = await service.delete_flow_tag(flow_id, "format")
        
        assert result is True
        mock_tag_service.delete_flow_tag.assert_called_once_with(flow_id, "format")
    
    @pytest.mark.asyncio
    async def test_delete_flow_tag_exception(self, service, mock_tag_service, flow_id):
        """Test delete_flow_tag raises HTTPException on error"""
        mock_tag_service.delete_flow_tag = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_flow_tag(flow_id, "format")
        
        assert exc_info.value.status_code == 500
    
    # Generic entity tag methods
    @pytest.mark.asyncio
    async def test_get_entity_tags_success(self, service, mock_tag_service):
        """Test get_entity_tags success"""
        entity_id = tams_uuid()
        tags = Tags({"category": "test"})
        mock_tag_service.get_entity_tags = AsyncMock(return_value=tags)
        
        result = await service.get_entity_tags("source", entity_id)
        
        assert result == tags
        mock_tag_service.get_entity_tags.assert_called_once_with("source", entity_id)
    
    @pytest.mark.asyncio
    async def test_get_entity_tags_exception(self, service, mock_tag_service):
        """Test get_entity_tags raises HTTPException on error"""
        entity_id = tams_uuid()
        mock_tag_service.get_entity_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_entity_tags("source", entity_id)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_update_entity_tags_success(self, service, mock_tag_service):
        """Test update_entity_tags success"""
        entity_id = tams_uuid()
        tags = Tags({"category": "test"})
        mock_tag_service.update_entity_tags = AsyncMock(return_value=True)
        
        result = await service.update_entity_tags("source", entity_id, tags)
        
        assert result is True
        mock_tag_service.update_entity_tags.assert_called_once_with("source", entity_id, tags)
    
    @pytest.mark.asyncio
    async def test_update_entity_tags_validation_error(self, service, mock_tag_service):
        """Test update_entity_tags raises HTTPException on validation error"""
        entity_id = tams_uuid()
        tags = Tags({"invalid!tag": "value"})
        mock_tag_service.update_entity_tags = AsyncMock(side_effect=ValueError("Invalid tag name"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_entity_tags("source", entity_id, tags)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_update_entity_tags_exception(self, service, mock_tag_service):
        """Test update_entity_tags raises HTTPException on error"""
        entity_id = tams_uuid()
        tags = Tags({"category": "test"})
        mock_tag_service.update_entity_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_entity_tags("source", entity_id, tags)
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_entity_tag_success(self, service, mock_tag_service):
        """Test get_entity_tag success"""
        entity_id = tams_uuid()
        mock_tag_service.get_entity_tag = AsyncMock(return_value="test")
        
        result = await service.get_entity_tag("source", entity_id, "category")
        
        assert result == "test"
        mock_tag_service.get_entity_tag.assert_called_once_with("source", entity_id, "category")
    
    @pytest.mark.asyncio
    async def test_get_entity_tag_exception(self, service, mock_tag_service):
        """Test get_entity_tag raises HTTPException on error"""
        entity_id = tams_uuid()
        mock_tag_service.get_entity_tag = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_entity_tag("source", entity_id, "category")
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_update_entity_tag_success(self, service, mock_tag_service):
        """Test update_entity_tag success"""
        entity_id = tams_uuid()
        mock_tag_service.update_entity_tag = AsyncMock(return_value=True)
        
        result = await service.update_entity_tag("source", entity_id, "category", "test")
        
        assert result is True
        mock_tag_service.update_entity_tag.assert_called_once_with("source", entity_id, "category", "test")
    
    @pytest.mark.asyncio
    async def test_update_entity_tag_validation_error(self, service, mock_tag_service):
        """Test update_entity_tag raises HTTPException on validation error"""
        entity_id = tams_uuid()
        mock_tag_service.update_entity_tag = AsyncMock(side_effect=ValueError("Invalid tag name"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_entity_tag("source", entity_id, "invalid!tag", "value")
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_update_entity_tag_exception(self, service, mock_tag_service):
        """Test update_entity_tag raises HTTPException on error"""
        entity_id = tams_uuid()
        mock_tag_service.update_entity_tag = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_entity_tag("source", entity_id, "category", "test")
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_delete_entity_tag_success(self, service, mock_tag_service):
        """Test delete_entity_tag success"""
        entity_id = tams_uuid()
        mock_tag_service.delete_entity_tag = AsyncMock(return_value=True)
        
        result = await service.delete_entity_tag("source", entity_id, "category")
        
        assert result is True
        mock_tag_service.delete_entity_tag.assert_called_once_with("source", entity_id, "category")
    
    @pytest.mark.asyncio
    async def test_delete_entity_tag_exception(self, service, mock_tag_service):
        """Test delete_entity_tag raises HTTPException on error"""
        entity_id = tams_uuid()
        mock_tag_service.delete_entity_tag = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_entity_tag("source", entity_id, "category")
        
        assert exc_info.value.status_code == 500
    
    # Query and analytics methods
    @pytest.mark.asyncio
    async def test_query_entities_by_tags_success(self, service, mock_tag_service):
        """Test query_entities_by_tags success"""
        mock_tag_service.query_entities_by_tags = AsyncMock(return_value=[{"id": "123"}])
        
        result = await service.query_entities_by_tags("source", {"category": "test"})
        
        assert isinstance(result, list)
        assert len(result) == 1
        mock_tag_service.query_entities_by_tags.assert_called_once_with("source", {"category": "test"}, 100)
    
    @pytest.mark.asyncio
    async def test_query_entities_by_tags_exception(self, service, mock_tag_service):
        """Test query_entities_by_tags raises HTTPException on error"""
        mock_tag_service.query_entities_by_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.query_entities_by_tags("source", {"category": "test"})
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_query_sources_by_tags_success(self, service, mock_tag_service):
        """Test query_sources_by_tags success"""
        mock_tag_service.query_sources_by_tags = AsyncMock(return_value=[{"id": "123"}])
        
        result = await service.query_sources_by_tags({"category": "test"})
        
        assert isinstance(result, list)
        mock_tag_service.query_sources_by_tags.assert_called_once_with({"category": "test"}, 100)
    
    @pytest.mark.asyncio
    async def test_query_sources_by_tags_exception(self, service, mock_tag_service):
        """Test query_sources_by_tags raises HTTPException on error"""
        mock_tag_service.query_sources_by_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.query_sources_by_tags({"category": "test"})
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_query_flows_by_tags_success(self, service, mock_tag_service):
        """Test query_flows_by_tags success"""
        mock_tag_service.query_flows_by_tags = AsyncMock(return_value=[{"id": "123"}])
        
        result = await service.query_flows_by_tags({"category": "test"})
        
        assert isinstance(result, list)
        mock_tag_service.query_flows_by_tags.assert_called_once_with({"category": "test"}, 100)
    
    @pytest.mark.asyncio
    async def test_query_flows_by_tags_exception(self, service, mock_tag_service):
        """Test query_flows_by_tags raises HTTPException on error"""
        mock_tag_service.query_flows_by_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.query_flows_by_tags({"category": "test"})
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_tag_analytics_success(self, service, mock_tag_service):
        """Test get_tag_analytics success"""
        mock_tag_service.get_tag_analytics = AsyncMock(return_value={"total_tags": 10})
        
        result = await service.get_tag_analytics("sources")
        
        assert isinstance(result, dict)
        assert result["total_tags"] == 10
        mock_tag_service.get_tag_analytics.assert_called_once_with("sources")
    
    @pytest.mark.asyncio
    async def test_get_tag_analytics_exception(self, service, mock_tag_service):
        """Test get_tag_analytics raises HTTPException on error"""
        mock_tag_service.get_tag_analytics = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_tag_analytics("sources")
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_standardized_tags_success(self, service, mock_tag_service):
        """Test get_standardized_tags success"""
        mock_tag_service.get_standardized_tags = AsyncMock(return_value={"tag1": {}})
        
        result = await service.get_standardized_tags()
        
        assert isinstance(result, dict)
        mock_tag_service.get_standardized_tags.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_standardized_tags_exception(self, service, mock_tag_service):
        """Test get_standardized_tags raises HTTPException on error"""
        mock_tag_service.get_standardized_tags = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.get_standardized_tags()
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_create_tag_proposal_success(self, service, mock_tag_service):
        """Test create_tag_proposal success"""
        mock_tag_service.create_tag_proposal = AsyncMock(return_value={"name": "new_tag", "status": "pending"})
        
        result = await service.create_tag_proposal(
            "new_tag", "Description", "string", "Justification", ["example"], "user123"
        )
        
        assert isinstance(result, dict)
        assert result["name"] == "new_tag"
        mock_tag_service.create_tag_proposal.assert_called_once_with(
            "new_tag", "Description", "string", "Justification", ["example"], "user123"
        )
    
    @pytest.mark.asyncio
    async def test_create_tag_proposal_exception(self, service, mock_tag_service):
        """Test create_tag_proposal raises HTTPException on error"""
        mock_tag_service.create_tag_proposal = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.create_tag_proposal(
                "new_tag", "Description", "string", "Justification", ["example"], "user123"
            )
        
        assert exc_info.value.status_code == 500


#!/usr/bin/env python3
"""
Tests for object summary endpoints in VAST module.

Tests the new endpoints:
- GET /api/vast/objects/{object_id}/summary - Get object summary
- PUT /api/vast/objects/{object_id}/summary - Update object summary
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.objects.service import ObjectStorageService
from fastapi import HTTPException


class TestObjectSummary:
    """Test object summary operations"""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock ObjectStorageService"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = ObjectStorageService(mock_db, mock_s3)
        return service
    
    @pytest.mark.asyncio
    async def test_get_object_summary_success(self, mock_service):
        """Test successful summary retrieval"""
        object_id = str(uuid.uuid4())
        expected_summary = "This is a test summary"
        
        # Mock database query result
        mock_result = {
            'data': {
                'summary': [expected_summary]
            }
        }
        mock_service.vast_db.execute_sql = Mock(return_value=mock_result)
        
        summary = await mock_service.get_object_summary(object_id)
        
        assert summary == expected_summary
        mock_service.vast_db.execute_sql.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_object_summary_not_found(self, mock_service):
        """Test summary retrieval when object doesn't exist"""
        object_id = str(uuid.uuid4())
        
        # Mock empty result
        mock_result = {
            'data': {
                'summary': []
            }
        }
        mock_service.vast_db.execute_sql = Mock(return_value=mock_result)
        
        summary = await mock_service.get_object_summary(object_id)
        
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_get_object_summary_none(self, mock_service):
        """Test summary retrieval when summary is None"""
        object_id = str(uuid.uuid4())
        
        # Mock result with None summary
        mock_result = {
            'data': {
                'summary': [None]
            }
        }
        mock_service.vast_db.execute_sql = Mock(return_value=mock_result)
        
        summary = await mock_service.get_object_summary(object_id)
        
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_update_object_summary_success(self, mock_service):
        """Test successful summary update"""
        object_id = str(uuid.uuid4())
        new_summary = "Updated summary"
        
        # Mock get_object to return a valid object
        from vasttamsserver.objects.models import Object
        from vasttamsserver.common.models import TimeRange
        mock_object = Object(
            id=object_id,
            referenced_by_flows=[],
            timerange=TimeRange(value="0:0")
        )
        mock_service.get_object = AsyncMock(return_value=mock_object)
        
        # Mock query builder for UPDATE
        mock_query_builder = Mock()
        mock_query_builder.where.return_value = mock_query_builder
        mock_query_builder.execute.return_value = True
        mock_service.vast_db.query.return_value = mock_query_builder
        
        result = await mock_service.update_object_summary(object_id, new_summary)
        
        assert result is True
        mock_service.vast_db.query.assert_called_once_with("objects")
    
    @pytest.mark.asyncio
    async def test_update_object_summary_clear(self, mock_service):
        """Test clearing summary by setting to None"""
        object_id = str(uuid.uuid4())
        
        # Mock get_object to return a valid object
        from vasttamsserver.objects.models import Object
        from vasttamsserver.common.models import TimeRange
        mock_object = Object(
            id=object_id,
            referenced_by_flows=[],
            timerange=TimeRange(value="0:0")
        )
        mock_service.get_object = AsyncMock(return_value=mock_object)
        
        # Mock query builder for UPDATE
        mock_query_builder = Mock()
        mock_query_builder.where.return_value = mock_query_builder
        mock_query_builder.execute.return_value = True
        mock_service.vast_db.query.return_value = mock_query_builder
        
        result = await mock_service.update_object_summary(object_id, None)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_object_summary_empty_string(self, mock_service):
        """Test updating summary to empty string"""
        object_id = str(uuid.uuid4())
        
        # Mock get_object to return a valid object
        from vasttamsserver.objects.models import Object
        from vasttamsserver.common.models import TimeRange
        mock_object = Object(
            id=object_id,
            referenced_by_flows=[],
            timerange=TimeRange(value="0:0")
        )
        mock_service.get_object = AsyncMock(return_value=mock_object)
        
        # Mock query builder for UPDATE
        mock_query_builder = Mock()
        mock_query_builder.where.return_value = mock_query_builder
        mock_query_builder.execute.return_value = True
        mock_service.vast_db.query.return_value = mock_query_builder
        
        result = await mock_service.update_object_summary(object_id, "")
        
        assert result is True


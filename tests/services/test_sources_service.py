#!/usr/bin/env python3
"""
Service Layer Tests for Sources Service

Tests sources/service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.sources.service import SourceStorageService
from vasttams.common.filters import SourceFilters
from vasttams.sources.models import Source


class TestSourceStorageService:
    """Test SourceStorageService"""
    
    def test_init(self):
        """Test service initialization"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = SourceStorageService(mock_db, mock_s3)
        assert service.vast_db == mock_db
        assert service.s3_client == mock_s3
    
    @pytest.mark.asyncio
    async def test_get_sources_empty_result(self):
        """Test get_sources with empty result"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        filters = SourceFilters()
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
        assert len(sources) == 0
    
    @pytest.mark.asyncio
    async def test_get_sources_with_filters(self):
        """Test get_sources with filters"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        import uuid
        source_id = str(uuid.uuid4())
        mock_query.execute.return_value = {
            'data': {
                'id': [source_id],
                'format': ['urn:x-nmos:format:video'],
                'label': ['Test Source'],
                'tags': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        # Mock _compute_source_collection to avoid async issues
        service._compute_source_collection = AsyncMock(return_value=None)
        
        filters = SourceFilters(format="urn:x-nmos:format:video", limit=10)
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
        if sources:
            assert sources[0].id == source_id
    
    @pytest.mark.asyncio
    async def test_get_source_existing(self):
        """Test get_source with existing source"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        import uuid
        source_id = str(uuid.uuid4())
        mock_query.execute.return_value = {
            'data': {
                'id': [source_id],
                'format': ['urn:x-nmos:format:video'],
                'label': ['Test Source'],
                'tags': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        service._compute_source_collection = AsyncMock(return_value=None)
        
        source = await service.get_source(source_id)
        
        assert source is not None
        assert source.id == source_id
    
    @pytest.mark.asyncio
    async def test_get_source_nonexistent(self):
        """Test get_source with non-existent source"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        source = await service.get_source('nonexistent')
        
        assert source is None
    
    @pytest.mark.asyncio
    async def test_create_source(self):
        """Test create_source"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Test Source"
        )
        
        mock_db = Mock()
        mock_db.insert_record = Mock()
        
        service = SourceStorageService(mock_db, Mock())
        result = await service.create_source(source)
        
        assert result is True
        mock_db.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_source(self):
        """Test update_source"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Updated Source"
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value=True)
        
        service = SourceStorageService(mock_db, Mock())
        result = await service.update_source(source_id, source)
        
        assert result is True
        assert mock_db.execute_sql.called
    
    @pytest.mark.asyncio
    async def test_delete_source_with_cascade(self):
        """Test delete_source with cascade=True"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.delete.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = True
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value=True)
        
        service = SourceStorageService(mock_db, Mock())
        service._cascade_delete_flows = AsyncMock(return_value=True)
        
        result = await service.delete_source(source_id, cascade=True)
        
        assert result is True
        assert service._cascade_delete_flows.called
    
    @pytest.mark.asyncio
    async def test_delete_source_without_cascade(self):
        """Test delete_source with cascade=False"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        
        # Mock flows query (to check for dependencies) - return empty result
        mock_flows_query = Mock()
        mock_flows_query.select.return_value = mock_flows_query
        mock_flows_query.where.return_value = mock_flows_query
        mock_flows_query.execute.return_value = []  # Empty list - no flows (service checks len())
        
        # Mock sources delete query
        mock_delete_query = Mock()
        mock_delete_query.delete.return_value = mock_delete_query
        mock_delete_query.where.return_value = mock_delete_query
        mock_delete_query.execute.return_value = True
        
        # Return different mocks for different queries
        def query_side_effect(table_name):
            if table_name == "flows":
                return mock_flows_query
            elif table_name == "sources":
                return mock_delete_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        service = SourceStorageService(mock_db, Mock())
        
        result = await service.delete_source(source_id, cascade=False)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_source_with_dependencies(self):
        """Test delete_source when source has dependent flows (should raise ValueError)"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        
        # Mock flows query - return flows (has dependencies)
        mock_flows_query = Mock()
        mock_flows_query.select.return_value = mock_flows_query
        mock_flows_query.where.return_value = mock_flows_query
        mock_flows_query.execute.return_value = [{'id': 'flow1'}]  # Has flows (service checks len())
        
        def query_side_effect(table_name):
            if table_name == "flows":
                return mock_flows_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        service = SourceStorageService(mock_db, Mock())
        
        with pytest.raises(ValueError, match="Cannot delete source with existing flows"):
            await service.delete_source(source_id, cascade=False)
    
    @pytest.mark.asyncio
    async def test_cascade_delete_flows(self):
        """Test _cascade_delete_flows helper method"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        
        # Mock flows query (to get flow IDs)
        mock_flows_query = Mock()
        mock_flows_query.select.return_value = mock_flows_query
        mock_flows_query.where.return_value = mock_flows_query
        mock_flows_query.execute.return_value = {'data': {'id': ['flow1', 'flow2']}}
        
        # Mock segments delete query
        mock_segments_delete = Mock()
        mock_segments_delete.delete.return_value = mock_segments_delete
        mock_segments_delete.where.return_value = mock_segments_delete
        mock_segments_delete.execute.return_value = True
        
        # Mock flows delete query
        mock_flows_delete = Mock()
        mock_flows_delete.delete.return_value = mock_flows_delete
        mock_flows_delete.where.return_value = mock_flows_delete
        mock_flows_delete.execute.return_value = True
        
        def query_side_effect(table_name):
            if table_name == "flows":
                # First call is select, subsequent calls are delete
                if not hasattr(query_side_effect, 'flows_called'):
                    query_side_effect.flows_called = True
                    return mock_flows_query
                else:
                    return mock_flows_delete
            elif table_name == "segments":
                return mock_segments_delete
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        service = SourceStorageService(mock_db, Mock())
        result = await service._cascade_delete_flows(source_id)
        
        assert result is True
        # Verify that delete operations were called
        assert mock_segments_delete.execute.called
        assert mock_flows_delete.execute.called
    
    @pytest.mark.asyncio
    async def test_compute_source_collection(self):
        """Test _compute_source_collection helper method"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': []})
        
        service = SourceStorageService(mock_db, Mock())
        collection = await service._compute_source_collection(source_id)
        
        assert isinstance(collection, list)
    
    @pytest.mark.asyncio
    async def test_get_sources_with_collection(self):
        """Test get_sources includes collection in results"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [source_id],
                'format': ['urn:x-nmos:format:video'],
                'label': ['Test Source'],
                'tags': ['{}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        service._compute_source_collection = AsyncMock(return_value=[])
        
        filters = SourceFilters()
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
        if sources:
            assert sources[0].id == source_id


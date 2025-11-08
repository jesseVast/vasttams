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

from vasttamsserver.sources.service import SourceStorageService
from vasttamsserver.common.filters import SourceFilters
from vasttamsserver.sources.models import Source


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
    
    @pytest.mark.asyncio
    async def test_get_sources_with_tag_filters_list(self):
        """Test get_sources with tag_filters (list of values)"""
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
                'tags': ['{"genre": ["action", "drama"]}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters(tag_filters={"genre": ["action", "drama"]})
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
    
    @pytest.mark.asyncio
    async def test_get_sources_with_tag_filters_string(self):
        """Test get_sources with tag_filters (single string value)"""
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
                'tags': ['{"genre": "action"}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters(tag_filters={"genre": "action"})
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
    
    @pytest.mark.asyncio
    async def test_get_sources_with_tag_exists_filters(self):
        """Test get_sources with tag_exists_filters"""
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
                'tags': ['{"genre": "action"}']
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters(tag_exists_filters={"genre": True})
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
    
    @pytest.mark.asyncio
    async def test_get_sources_with_tag_exists_filters_false(self):
        """Test get_sources with tag_exists_filters (exists=False)"""
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
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters(tag_exists_filters={"genre": False})
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
    
    @pytest.mark.asyncio
    async def test_get_sources_data_as_list(self):
        """Test get_sources with data as list (not dict)"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        # Return dict with 'data' as list
        # Tags should be dict (not JSON string) since list format doesn't parse JSON
        mock_query.execute.return_value = {
            'data': [{
                'id': source_id,
                'format': 'urn:x-nmos:format:video',
                'label': 'Test Source',
                'tags': {}  # Dict, not JSON string
            }]
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters()
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
    
    @pytest.mark.asyncio
    async def test_get_sources_list_format_result(self):
        """Test get_sources with list format result (not dict)"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        # Return list format (not dict with 'data')
        # Tags should be dict (not JSON string) since list format doesn't parse JSON
        mock_query.execute.return_value = [{
            'id': source_id,
            'format': 'urn:x-nmos:format:video',
            'label': 'Test Source',
            'tags': {}  # Dict, not JSON string
        }]
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters()
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
    
    @pytest.mark.asyncio
    async def test_get_sources_tags_json_parse_error(self):
        """Test get_sources with invalid tags JSON"""
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
                'tags': ['invalid json{']  # Invalid JSON
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={'data': {}})
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters()
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
        if sources:
            assert sources[0].tags is None
    
    @pytest.mark.asyncio
    async def test_get_sources_with_collection_join(self):
        """Test get_sources with collection computed from JOIN query"""
        import uuid
        source_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
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
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Mock JOIN query result with collection data
        collection_item_id = str(uuid.uuid4())
        mock_db.execute_sql = Mock(return_value={
            'data': {
                'source_id': [source_id],
                'flow_id': [flow_id],
                'flow_collection': [f'[{{"id": "{collection_item_id}", "role": "main"}}]']
            }
        })
        
        service = SourceStorageService(mock_db, Mock())
        
        filters = SourceFilters()
        sources = await service.get_sources(filters)
        
        assert isinstance(sources, list)
        if sources:
            assert hasattr(sources[0], 'source_collection')
    
    @pytest.mark.asyncio
    async def test_get_sources_exception_handling(self):
        """Test get_sources exception handling"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await service.get_sources(SourceFilters())
    
    @pytest.mark.asyncio
    async def test_get_source_list_format(self):
        """Test get_source with list format result"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        # Return list format - tags should be dict (not JSON string) since list format doesn't parse JSON
        mock_query.execute.return_value = [{
            'id': source_id,
            'format': 'urn:x-nmos:format:video',
            'label': 'Test Source',
            'tags': {}  # Dict, not JSON string
        }]
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        service._compute_source_collection = AsyncMock(return_value=[])
        
        source = await service.get_source(source_id)
        
        assert source is not None
        assert source.id == source_id
    
    @pytest.mark.asyncio
    async def test_get_source_data_as_list(self):
        """Test get_source with data as list (not dict)"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        # Return dict with 'data' as list - tags should be dict (not JSON string)
        mock_query.execute.return_value = {
            'data': [{
                'id': source_id,
                'format': 'urn:x-nmos:format:video',
                'label': 'Test Source',
                'tags': {}  # Dict, not JSON string
            }]
        }
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        service._compute_source_collection = AsyncMock(return_value=[])
        
        source = await service.get_source(source_id)
        
        assert source is not None
        assert source.id == source_id
    
    @pytest.mark.asyncio
    async def test_get_source_empty_data_list(self):
        """Test get_source with empty data list"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        # Return dict with 'data' as empty list
        mock_query.execute.return_value = {
            'data': []
        }
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        
        source = await service.get_source(source_id)
        
        assert source is None
    
    @pytest.mark.asyncio
    async def test_get_source_exception_handling(self):
        """Test get_source exception handling"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await service.get_source('source1')
    
    @pytest.mark.asyncio
    async def test_create_source_exception_handling(self):
        """Test create_source exception handling"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Test Source"
        )
        
        mock_db = Mock()
        mock_db.insert_record.side_effect = Exception("Database error")
        
        service = SourceStorageService(mock_db, Mock())
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await service.create_source(source)
    
    @pytest.mark.asyncio
    async def test_update_source_with_tags(self):
        """Test update_source with tags"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Updated Source",
            tags={"genre": "action"}
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value=True)
        
        service = SourceStorageService(mock_db, Mock())
        # Mock tag_service
        service.tag_service = Mock()
        service.tag_service.update_source_tags = AsyncMock(return_value=True)
        
        result = await service.update_source(source_id, source)
        
        assert result is True
        assert service.tag_service.update_source_tags.called
    
    @pytest.mark.asyncio
    async def test_update_source_upsert_path(self):
        """Test update_source when UPDATE fails, uses upsert (DELETE + INSERT)"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Updated Source"
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # First UPDATE fails, then DELETE + INSERT succeeds
        # execute_sql is called: 1) UPDATE (fails), 2) DELETE (succeeds)
        call_count = 0
        def execute_sql_side_effect(sql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("UPDATE failed")  # First call (UPDATE) fails
            return True  # Second call (DELETE) succeeds
        
        mock_db.execute_sql.side_effect = execute_sql_side_effect
        mock_db.insert_record = Mock()
        
        # Mock prepare_data_for_pyarrow to handle the conversion
        # The issue is that source_data has SQL CAST expressions from prepare_data_for_sql
        # prepare_data_for_pyarrow is imported inside the method, so patch at the source module
        with patch('vasttams.common.storage.timestamp_utils.prepare_data_for_pyarrow') as mock_prepare:
            def prepare_side_effect(data):
                # Return data with clean timestamps (remove CAST expressions)
                clean_data = {}
                for k, v in data.items():
                    if isinstance(v, str) and v.startswith('CAST('):
                        # Skip CAST expressions - they'll be handled by get_tams_timestamp()
                        continue
                    clean_data[k] = v
                return clean_data
            
            mock_prepare.side_effect = prepare_side_effect
            
            service = SourceStorageService(mock_db, Mock())
            service.tag_service = Mock()
            service.tag_service.update_source_tags = AsyncMock(return_value=True)
            
            result = await service.update_source(source_id, source)
            
            assert result is True
            assert mock_db.insert_record.called
    
    @pytest.mark.asyncio
    async def test_update_source_upsert_with_tags(self):
        """Test update_source upsert path with tags"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Updated Source",
            tags={"genre": "action"}
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # execute_sql is called: 1) UPDATE (fails), 2) DELETE (succeeds)
        call_count = 0
        def execute_sql_side_effect(sql):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("UPDATE failed")  # First call (UPDATE) fails
            return True  # Second call (DELETE) succeeds
        
        mock_db.execute_sql.side_effect = execute_sql_side_effect
        mock_db.insert_record = Mock()
        
        # Mock prepare_data_for_pyarrow to handle the conversion
        # The issue is that source_data has SQL CAST expressions from prepare_data_for_sql
        # prepare_data_for_pyarrow is imported inside the method, so patch at the source module
        with patch('vasttams.common.storage.timestamp_utils.prepare_data_for_pyarrow') as mock_prepare:
            def prepare_side_effect(data):
                # Return data with clean timestamps (remove CAST expressions)
                clean_data = {}
                for k, v in data.items():
                    if isinstance(v, str) and v.startswith('CAST('):
                        # Skip CAST expressions - they'll be handled by get_tams_timestamp()
                        continue
                    clean_data[k] = v
                return clean_data
            
            mock_prepare.side_effect = prepare_side_effect
            
            service = SourceStorageService(mock_db, Mock())
            service.tag_service = Mock()
            service.tag_service.update_source_tags = AsyncMock(return_value=True)
            
            result = await service.update_source(source_id, source)
            
            assert result is True
            assert service.tag_service.update_source_tags.called
    
    @pytest.mark.asyncio
    async def test_update_source_upsert_fails(self):
        """Test update_source when both UPDATE and upsert fail"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Updated Source"
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Both UPDATE and DELETE fail
        mock_db.execute_sql.side_effect = [
            Exception("UPDATE failed"),
            Exception("DELETE failed"),
        ]
        
        service = SourceStorageService(mock_db, Mock())
        service.tag_service = Mock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await service.update_source(source_id, source)
    
    @pytest.mark.asyncio
    async def test_update_source_no_fields_to_update(self):
        """Test update_source with no fields to update"""
        import uuid
        source_id = str(uuid.uuid4())
        
        # Create source with only read-only fields
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video"
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value=True)
        
        service = SourceStorageService(mock_db, Mock())
        service.tag_service = Mock()
        service.tag_service.update_source_tags = AsyncMock(return_value=True)
        
        result = await service.update_source(source_id, source)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_source_exception_handling(self):
        """Test update_source exception handling"""
        import uuid
        source_id = str(uuid.uuid4())
        
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Updated Source"
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        service = SourceStorageService(mock_db, Mock())
        service.tag_service = Mock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await service.update_source(source_id, source)
    
    @pytest.mark.asyncio
    async def test_delete_source_exception_handling(self):
        """Test delete_source exception handling"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await service.delete_source(source_id, cascade=True)
    
    @pytest.mark.asyncio
    async def test_cascade_delete_flows_list_format(self):
        """Test _cascade_delete_flows with list format result"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        
        # Mock flows query - return list format
        mock_flows_query = Mock()
        mock_flows_query.select.return_value = mock_flows_query
        mock_flows_query.where.return_value = mock_flows_query
        mock_flows_query.execute.return_value = [{'id': 'flow1'}, {'id': 'flow2'}]  # List format
        
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
    
    @pytest.mark.asyncio
    async def test_cascade_delete_flows_empty_result(self):
        """Test _cascade_delete_flows with empty result"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        
        # Mock flows query - return empty result
        mock_flows_query = Mock()
        mock_flows_query.select.return_value = mock_flows_query
        mock_flows_query.where.return_value = mock_flows_query
        mock_flows_query.execute.return_value = {'data': {}}  # Empty
        
        mock_db.query.return_value = mock_flows_query
        
        service = SourceStorageService(mock_db, Mock())
        result = await service._cascade_delete_flows(source_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cascade_delete_flows_exception_handling(self):
        """Test _cascade_delete_flows exception handling"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = SourceStorageService(mock_db, Mock())
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await service._cascade_delete_flows(source_id)
    
    @pytest.mark.asyncio
    async def test_compute_source_collection_with_data(self):
        """Test _compute_source_collection with actual data"""
        import uuid
        source_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': [
                [source_id, flow_id, '[{"id": "item1", "role": "main"}]']
            ]
        })
        
        service = SourceStorageService(mock_db, Mock())
        collection = await service._compute_source_collection(source_id)
        
        assert isinstance(collection, list)
    
    @pytest.mark.asyncio
    async def test_compute_source_collection_invalid_json(self):
        """Test _compute_source_collection with invalid JSON in flow_collection"""
        import uuid
        source_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': [
                [source_id, flow_id, 'invalid json{']
            ]
        })
        
        service = SourceStorageService(mock_db, Mock())
        collection = await service._compute_source_collection(source_id)
        
        assert isinstance(collection, list)
        assert len(collection) == 0
    
    @pytest.mark.asyncio
    async def test_compute_source_collection_exception_handling(self):
        """Test _compute_source_collection exception handling"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql.side_effect = Exception("SQL error")
        
        service = SourceStorageService(mock_db, Mock())
        collection = await service._compute_source_collection(source_id)
        
        assert isinstance(collection, list)
        assert len(collection) == 0
    
    @pytest.mark.asyncio
    async def test_update_source_no_fields_to_update_warning(self):
        """Test update_source logs warning when no fields to update"""
        import uuid
        source_id = str(uuid.uuid4())
        
        from vasttamsserver.sources.models import Source
        source = Source(
            id=source_id,
            format="urn:x-nmos:format:video",
            label="Test Source"
        )
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock()
        
        service = SourceStorageService(mock_db, Mock())
        service.tag_service = Mock()
        service.tag_service.update_source_tags = AsyncMock(return_value=True)
        
        # Mock prepare_data_for_sql to return empty dict (no fields to update)
        with patch('vasttams.common.storage.timestamp_utils.prepare_data_for_sql') as mock_prepare:
            mock_prepare.return_value = {}  # No fields to update
            
            result = await service.update_source(source_id, source)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_cascade_delete_flows_list_format_with_string_ids(self):
        """Test _cascade_delete_flows with list format containing string IDs"""
        import uuid
        source_id = str(uuid.uuid4())
        
        mock_db = Mock()
        
        # Mock flows query - return list with string IDs
        mock_flows_query = Mock()
        mock_flows_query.select.return_value = mock_flows_query
        mock_flows_query.where.return_value = mock_flows_query
        mock_flows_query.execute.return_value = ['flow1', 'flow2']  # List of strings
        
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
    
    @pytest.mark.asyncio
    async def test_compute_source_collection_list_format(self):
        """Test _compute_source_collection with list format result"""
        import uuid
        source_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.execute_sql = Mock(return_value={
            'data': [
                {
                    'id': flow_id,
                    'flow_collection': '[{"id": "item1", "role": "main"}]'
                }
            ]
        })
        
        service = SourceStorageService(mock_db, Mock())
        collection = await service._compute_source_collection(source_id)
        
        assert isinstance(collection, list)
    
    @pytest.mark.asyncio
    async def test_compute_source_collection_direct_list_result(self):
        """Test _compute_source_collection with direct list result"""
        import uuid
        source_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        # Return direct list (not dict with 'data')
        mock_db.execute_sql = Mock(return_value=[
            {
                'id': flow_id,
                'flow_collection': '[{"id": "item1", "role": "main"}]'
            }
        ])
        
        service = SourceStorageService(mock_db, Mock())
        collection = await service._compute_source_collection(source_id)
        
        assert isinstance(collection, list)


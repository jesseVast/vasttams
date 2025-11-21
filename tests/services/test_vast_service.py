#!/usr/bin/env python3
"""
Service Layer Tests for VAST Vector Service

Tests vast/service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
from fastapi import HTTPException

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.vast.service import VastObjectVectorService
from vasttamsserver.objects.models import Object
from vasttamsserver.common.models import TimeRange
from datetime import datetime


def create_mock_vector(dimension=768):
    """Helper to create a mock vector of specified dimension"""
    return [0.1 * i for i in range(dimension)]


def create_mock_object(object_id, flow_id=None):
    """Helper to create a mock Object"""
    flow_id = flow_id or str(uuid.uuid4())
    timerange = TimeRange(value="0:0_100:0")
    return Object(
        id=object_id,
        referenced_by_flows=[flow_id],
        first_referenced_by_flow=flow_id,
        timerange=timerange,
        size=1000000,
        created=datetime.fromisoformat("2024-01-01T00:00:00Z")
    )


def build_mock_query_builder(vector_result):
    """Helper to create a mock query builder chain for vector search"""
    mock_query_builder = Mock()
    mock_query_builder.select.return_value = mock_query_builder
    mock_query_builder.search.return_value = mock_query_builder
    mock_query_builder.limit.return_value = mock_query_builder
    mock_query_builder.execute.return_value = vector_result
    return mock_query_builder


class TestVastObjectVectorService:
    """Test VastObjectVectorService"""
    
    def test_init(self):
        """Test service initialization"""
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.vector_client = Mock()  # Simulate vector client available
        
        service = VastObjectVectorService(mock_db, mock_s3)
        assert service.vast_db == mock_db
        assert service.s3_client == mock_s3
        assert service.vector_client == mock_db.vector_client
    
    def test_init_no_vector_client(self):
        """Test service initialization when vector client is not available"""
        mock_db = Mock()
        del mock_db.vector_client  # Remove vector_client attribute
        mock_s3 = Mock()
        
        service = VastObjectVectorService(mock_db, mock_s3)
        assert service.vast_db == mock_db
        assert service.s3_client == mock_s3
        assert service.vector_client is None
    
    @pytest.mark.asyncio
    async def test_update_object_vector_success(self):
        """Test successful vector update using insert_record"""
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(768)
        summary = "Test summary"
        embedding_model = "test-model"
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_object_service = AsyncMock()
        mock_object = create_mock_object(object_id)
        mock_object_service.get_object = AsyncMock(return_value=mock_object)
        
        # Mock insert_record (upsert behavior)
        mock_db.insert_record = Mock()
        
        service = VastObjectVectorService(mock_db, mock_s3)
        service.object_service = mock_object_service
        
        result = await service.update_object_vector(
            object_id=object_id,
            vector=vector,
            summary=summary,
            embedding_model=embedding_model
        )
        
        assert result is True
        # get_object is called once for validation
        assert mock_object_service.get_object.call_count == 1
        # Verify insert_record was called with object_vector table
        mock_db.insert_record.assert_called_once()
        call_args = mock_db.insert_record.call_args
        assert call_args[0][0] == "object_vector"
        vector_data = call_args[0][1]
        assert vector_data["object_id"] == object_id
        assert vector_data["vector"] == vector
        assert vector_data["summary"] == summary
        assert vector_data["embedding_model"] == embedding_model
    
    @pytest.mark.asyncio
    async def test_update_object_vector_object_not_found(self):
        """Test vector update when object doesn't exist"""
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_object_service = AsyncMock()
        mock_object_service.get_object = AsyncMock(return_value=None)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        service.object_service = mock_object_service
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_object_vector(
                object_id=object_id,
                vector=vector
            )
        
        assert exc_info.value.status_code == 404
        assert object_id in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_update_object_vector_invalid_dimension(self):
        """Test vector update with invalid vector dimension"""
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(512)  # Wrong dimension
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_object_service = AsyncMock()
        mock_object = create_mock_object(object_id)
        mock_object_service.get_object = AsyncMock(return_value=mock_object)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        service.object_service = mock_object_service
        
        with pytest.raises(HTTPException) as exc_info:
            await service.update_object_vector(
                object_id=object_id,
                vector=vector
            )
        
        assert exc_info.value.status_code == 400
        assert "768 dimensions" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_update_object_vector_zero_rows_updated(self):
        """Test vector update - insert_record handles upserts, so this test is no longer applicable"""
        # With insert_record, upserts always succeed if object exists
        # This test case is no longer relevant
        pass
    
    @pytest.mark.asyncio
    async def test_update_object_vector_with_defaults(self):
        """Test vector update with default embedding model"""
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_object_service = AsyncMock()
        mock_object = create_mock_object(object_id)
        mock_object_service.get_object = AsyncMock(return_value=mock_object)
        
        # Mock insert_record
        mock_db.insert_record = Mock()
        
        service = VastObjectVectorService(mock_db, mock_s3)
        service.object_service = mock_object_service
        
        result = await service.update_object_vector(
            object_id=object_id,
            vector=vector,
            summary=None,
            embedding_model=None
        )
        
        assert result is True
        # Verify embedding_model default is set to 'nomic-embed-1.5'
        call_args = mock_db.insert_record.call_args
        vector_data = call_args[0][1]
        assert vector_data["embedding_model"] == "nomic-embed-1.5"
    
    @pytest.mark.asyncio
    async def test_search_vectors_success_with_vector_client(self):
        """Test successful vector search with query builder search() method"""
        query_vector = create_mock_vector(768)
        num_matches = 10
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        
        # Mock query builder search() method
        object_id1 = str(uuid.uuid4())
        object_id2 = str(uuid.uuid4())
        mock_vector_result = {
            'data': {
                'object_id': [object_id1, object_id2],
                'distance': [0.5, 0.7]
            }
        }
        
        # Mock query builder chain
        mock_query_builder = build_mock_query_builder(mock_vector_result)
        mock_db.query = Mock(return_value=mock_query_builder)
        
        # Mock JOIN query result
        segment_id1 = str(uuid.uuid4())
        flow_id1 = str(uuid.uuid4())
        source_id1 = str(uuid.uuid4())
        mock_join_result = {
            'data': {
                'object_id': [object_id1, object_id2],
                'segment_id': [segment_id1, None],
                'flow_id': [flow_id1, None],
                'source_id': [source_id1, None]
            }
        }
        mock_db.execute_sql = Mock(return_value=mock_join_result)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        result = await service.search_vectors(
            query_vector=query_vector,
            num_matches=num_matches
        )
        
        assert 'matches' in result
        assert len(result['matches']) == 2
        assert result['matches'][0]['object_id'] == object_id1
        assert result['matches'][0]['distance'] == 0.5
        assert result['matches'][0]['segment_id'] == segment_id1
        assert result['matches'][0]['flow_id'] == flow_id1
        assert result['matches'][0]['source_id'] == source_id1
        
        # Verify query builder search was called with correct parameters
        mock_db.query.assert_called_once_with("object_vector")
        search_call_kwargs = mock_query_builder.search.call_args[1]
        assert search_call_kwargs['query_vector'] == query_vector
        assert search_call_kwargs['vector_column'] == "vector"
        assert search_call_kwargs['distance_metric'] == "cosine"
    
    @pytest.mark.asyncio
    async def test_search_vectors_invalid_dimension(self):
        """Test vector search with invalid vector dimension"""
        query_vector = create_mock_vector(512)  # Wrong dimension
        
        mock_db = Mock()
        mock_s3 = Mock()
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.search_vectors(query_vector=query_vector)
        
        assert exc_info.value.status_code == 400
        assert "768 dimensions" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_search_vectors_with_distance_threshold(self):
        """Test vector search with distance threshold filtering"""
        query_vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        
        # Mock vector search result with distances
        object_id1 = str(uuid.uuid4())
        object_id2 = str(uuid.uuid4())
        object_id3 = str(uuid.uuid4())
        mock_vector_result = {
            'data': {
                'object_id': [object_id1, object_id2, object_id3],
                'distance': [0.5, 0.8, 0.9]  # Third one exceeds threshold
            }
        }
        
        # Mock query builder chain
        mock_query_builder = build_mock_query_builder(mock_vector_result)
        mock_db.query = Mock(return_value=mock_query_builder)
        
        # Mock JOIN query result
        mock_join_result = {
            'data': {
                'object_id': [object_id1, object_id2],
                'segment_id': [None, None],
                'flow_id': [None, None],
                'source_id': [None, None]
            }
        }
        mock_db.execute_sql = Mock(return_value=mock_join_result)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        # Set distance threshold to 0.75 (should filter out object_id3)
        result = await service.search_vectors(
            query_vector=query_vector,
            distance_numerical_value=0.75
        )
        
        assert 'matches' in result
        # Should only have 2 matches (object_id3 filtered out)
        assert len(result['matches']) == 2
    
    @pytest.mark.asyncio
    async def test_search_vectors_empty_results(self):
        """Test vector search with no matches"""
        query_vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        
        # Mock empty vector search result
        mock_vector_result = {
            'data': {
                'object_id': [],
                'distance': []
            }
        }
        
        # Mock query builder chain
        mock_query_builder = build_mock_query_builder(mock_vector_result)
        mock_db.query = Mock(return_value=mock_query_builder)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        result = await service.search_vectors(query_vector=query_vector)
        
        assert 'matches' in result
        assert result['matches'] == []
    
    @pytest.mark.asyncio
    async def test_search_vectors_vector_client_fallback(self):
        """Test vector search falls back to vector_client when query builder is unavailable"""
        query_vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.query = Mock(side_effect=AttributeError("search not available"))
        
        # Mock vector_client fallback result
        object_id1 = str(uuid.uuid4())
        mock_vector_result = {
            'data': {
                'object_id': [object_id1],
                'distance': [0.42]
            }
        }
        mock_vector_client = Mock()
        mock_vector_client.query_vectors_with_distance = Mock(return_value=mock_vector_result)
        mock_db.vector_client = mock_vector_client
        
        # Mock JOIN query result
        segment_id1 = str(uuid.uuid4())
        flow_id1 = str(uuid.uuid4())
        source_id1 = str(uuid.uuid4())
        mock_join_result = {
            'data': {
                'object_id': [object_id1],
                'segment_id': [segment_id1],
                'flow_id': [flow_id1],
                'source_id': [source_id1]
            }
        }
        mock_db.execute_sql = Mock(return_value=mock_join_result)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        result = await service.search_vectors(query_vector=query_vector)
        
        assert 'matches' in result
        assert len(result['matches']) == 1
        assert result['matches'][0]['object_id'] == object_id1
        assert result['matches'][0]['distance'] == 0.42
        mock_vector_client.query_vectors_with_distance.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_vectors_vector_client_error_fallback(self):
        """Test vector search raises error when both query builder and vector_client fail"""
        query_vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        mock_db.query = Mock(side_effect=AttributeError("search not available"))
        
        mock_vector_client = Mock()
        mock_vector_client.query_vectors_with_distance = Mock(side_effect=Exception("Vector client error"))
        mock_db.vector_client = mock_vector_client
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.search_vectors(query_vector=query_vector)
        
        assert exc_info.value.status_code == 503
    
    @pytest.mark.asyncio
    async def test_search_vectors_distance_metric_normalization(self):
        """Test distance metric normalization"""
        query_vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        
        mock_vector_result = {
            'data': {
                'object_id': [],
                'distance': []
            }
        }
        
        # Mock query builder chain
        mock_query_builder = build_mock_query_builder(mock_vector_result)
        mock_db.query = Mock(return_value=mock_query_builder)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        # Test with uppercase distance metric
        await service.search_vectors(
            query_vector=query_vector,
            distance_metric="COSINE"
        )
        
        # Verify it was normalized to lowercase
        search_call_kwargs = mock_query_builder.search.call_args[1]
        assert search_call_kwargs['distance_metric'] == "cosine"
    
    @pytest.mark.asyncio
    async def test_search_vectors_invalid_distance_metric(self):
        """Test search with invalid distance metric defaults to cosine"""
        query_vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        
        mock_vector_result = {
            'data': {
                'object_id': [],
                'distance': []
            }
        }
        
        # Mock query builder chain
        mock_query_builder = build_mock_query_builder(mock_vector_result)
        mock_db.query = Mock(return_value=mock_query_builder)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        # Test with invalid distance metric
        await service.search_vectors(
            query_vector=query_vector,
            distance_metric="invalid_metric"
        )
        
        # Verify it defaulted to cosine
        search_call_kwargs = mock_query_builder.search.call_args[1]
        assert search_call_kwargs['distance_metric'] == "cosine"
    
    @pytest.mark.asyncio
    async def test_search_vectors_row_format_result(self):
        """Test search handles row format results from JOIN query"""
        query_vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_db.get_qualified_table_name = lambda name: f"vast.schema.{name}"
        
        object_id1 = str(uuid.uuid4())
        mock_vector_result = {
            'data': {
                'object_id': [object_id1],
                'distance': [0.5]
            }
        }
        
        # Mock query builder chain
        mock_query_builder = build_mock_query_builder(mock_vector_result)
        mock_db.query = Mock(return_value=mock_query_builder)
        
        # Mock JOIN query returning list format (not dict)
        segment_id1 = str(uuid.uuid4())
        flow_id1 = str(uuid.uuid4())
        source_id1 = str(uuid.uuid4())
        mock_join_result = [
            {
                'object_id': object_id1,
                'segment_id': segment_id1,
                'flow_id': flow_id1,
                'source_id': source_id1
            }
        ]
        mock_db.execute_sql = Mock(return_value=mock_join_result)
        
        service = VastObjectVectorService(mock_db, mock_s3)
        
        result = await service.search_vectors(query_vector=query_vector)
        
        assert 'matches' in result
        assert len(result['matches']) == 1
        assert result['matches'][0]['object_id'] == object_id1
        assert result['matches'][0]['segment_id'] == segment_id1
    
    @pytest.mark.asyncio
    async def test_update_object_vector_insert_record_call(self):
        """Test that insert_record is called correctly with object_vector table"""
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(768)
        
        mock_db = Mock()
        mock_s3 = Mock()
        mock_object_service = AsyncMock()
        mock_object = create_mock_object(object_id)
        mock_object_service.get_object = AsyncMock(return_value=mock_object)
        
        # Mock insert_record
        mock_db.insert_record = Mock()
        
        service = VastObjectVectorService(mock_db, mock_s3)
        service.object_service = mock_object_service
        
        await service.update_object_vector(
            object_id=object_id,
            vector=vector,
            summary="Test summary"
        )
        
        # Verify insert_record was called with object_vector table
        mock_db.insert_record.assert_called_once()
        call_args = mock_db.insert_record.call_args
        assert call_args[0][0] == "object_vector"
        vector_data = call_args[0][1]
        assert vector_data["object_id"] == object_id
        assert vector_data["vector"] == vector
        assert vector_data["summary"] == "Test summary"
        assert "embedding_date" in vector_data
        assert "embedding_model" in vector_data


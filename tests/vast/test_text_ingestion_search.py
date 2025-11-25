#!/usr/bin/env python3
"""
Tests for text ingestion and text-based vector search in VAST module.

Tests the new endpoints:
- POST /api/vast/objects/ingest - Text ingestion
- POST /api/vast/objects/search/text - Text-based search
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.vast.service import VastObjectVectorService
from fastapi import HTTPException


def create_mock_vector(dimension=768):
    """Helper to create a mock vector of specified dimension"""
    return [0.1 * i for i in range(dimension)]


class TestTextIngestion:
    """Test text ingestion functionality"""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock VastObjectVectorService with embedding service"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = VastObjectVectorService(mock_db, mock_s3)
        
        # Mock embedding service
        service._embedding_service = Mock()
        service._embedding_service.create_embedding = AsyncMock(return_value=create_mock_vector(768))
        
        # Mock update_vector
        service.update_vector = AsyncMock(return_value=True)
        
        return service
    
    @pytest.mark.asyncio
    async def test_ingest_text_success(self, mock_service):
        """Test successful text ingestion"""
        entity_id = str(uuid.uuid4())
        text = "This is a test document"
        
        result = await mock_service.ingest_text(
            text=text,
            entity_id=entity_id,
            entity_type="object"
        )
        
        assert result is True
        mock_service._embedding_service.create_embedding.assert_called_once()
        mock_service.update_vector.assert_called_once()
        
        # Verify update_vector was called with correct parameters
        call_args = mock_service.update_vector.call_args
        assert call_args[1]['entity_id'] == entity_id
        assert call_args[1]['entity_type'] == "object"
        assert call_args[1]['summary'] == text[:500]  # Summary is truncated to 500 chars
    
    @pytest.mark.asyncio
    async def test_ingest_text_long_summary(self, mock_service):
        """Test text ingestion with long text (summary should be truncated)"""
        entity_id = str(uuid.uuid4())
        long_text = "A" * 1000  # 1000 characters
        
        await mock_service.ingest_text(
            text=long_text,
            entity_id=entity_id,
            entity_type="object"
        )
        
        # Verify summary was truncated to 500 chars
        call_args = mock_service.update_vector.call_args
        assert len(call_args[1]['summary']) == 500
    
    @pytest.mark.asyncio
    async def test_ingest_text_different_entity_types(self, mock_service):
        """Test text ingestion for different entity types"""
        text = "Test text"
        
        for entity_type in ["object", "flow", "source", "segment"]:
            entity_id = str(uuid.uuid4())
            await mock_service.ingest_text(
                text=text,
                entity_id=entity_id,
                entity_type=entity_type
            )
            
            call_args = mock_service.update_vector.call_args
            assert call_args[1]['entity_type'] == entity_type
    
    @pytest.mark.asyncio
    async def test_ingest_text_embedding_service_unavailable(self, mock_service):
        """Test text ingestion when embedding service is unavailable"""
        mock_service._embedding_service = None
        
        with pytest.raises(HTTPException) as exc_info:
            await mock_service.ingest_text(
                text="Test",
                entity_id=str(uuid.uuid4()),
                entity_type="object"
            )
        
        assert exc_info.value.status_code == 503
        assert "Embedding service is not available" in exc_info.value.detail


class TestTextSearch:
    """Test text-based vector search functionality"""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock VastObjectVectorService with embedding service"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = VastObjectVectorService(mock_db, mock_s3)
        
        # Mock embedding service
        service._embedding_service = Mock()
        service._embedding_service.create_embedding = AsyncMock(return_value=create_mock_vector(768))
        
        # Mock search_vectors
        service.search_vectors = AsyncMock(return_value={
            'matches': [
                {
                    'entity_id': str(uuid.uuid4()),
                    'entity_type': 'object',
                    'distance': 0.5
                }
            ]
        })
        
        return service
    
    @pytest.mark.asyncio
    async def test_search_by_text_success(self, mock_service):
        """Test successful text-based search"""
        query_text = "Find similar documents"
        
        result = await mock_service.search_by_text(
            text=query_text
        )
        
        assert 'matches' in result
        assert len(result['matches']) == 1
        
        # Verify embedding was created
        mock_service._embedding_service.create_embedding.assert_called_once()
        
        # Verify search_vectors was called
        mock_service.search_vectors.assert_called_once()
        call_args = mock_service.search_vectors.call_args
        assert len(call_args[1]['query_vector']) == 768
    
    @pytest.mark.asyncio
    async def test_search_by_text_with_entity_types_filter(self, mock_service):
        """Test text search with entity type filter"""
        query_text = "Test query"
        
        await mock_service.search_by_text(
            text=query_text,
            entity_types=["object", "flow"]
        )
        
        # Verify search_vectors was called with entity_types filter
        call_args = mock_service.search_vectors.call_args
        assert call_args[1]['entity_types'] == ["object", "flow"]
    
    @pytest.mark.asyncio
    async def test_search_by_text_with_limit(self, mock_service):
        """Test text search with limit"""
        query_text = "Test query"
        
        await mock_service.search_by_text(
            text=query_text,
            limit=5
        )
        
        call_args = mock_service.search_vectors.call_args
        assert call_args[1]['num_matches'] == 5
    
    @pytest.mark.asyncio
    async def test_search_by_text_with_distance_threshold(self, mock_service):
        """Test text search with distance threshold"""
        query_text = "Test query"
        
        await mock_service.search_by_text(
            text=query_text,
            distance_threshold=0.8
        )
        
        call_args = mock_service.search_vectors.call_args
        assert call_args[1]['distance_numerical_value'] == 0.8
    
    @pytest.mark.asyncio
    async def test_search_by_text_embedding_service_unavailable(self, mock_service):
        """Test text search when embedding service is unavailable"""
        mock_service._embedding_service = None
        
        with pytest.raises(HTTPException) as exc_info:
            await mock_service.search_by_text(text="Test")
        
        assert exc_info.value.status_code == 503
        assert "Embedding service is not available" in exc_info.value.detail


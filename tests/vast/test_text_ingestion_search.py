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
from datetime import datetime

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
        
        # Mock update_vector
        service.update_vector = AsyncMock(return_value=True)
        
        # Mock get_tams_timestamp
        with patch('vasttamsserver.vast.service.get_tams_timestamp') as mock_timestamp:
            from datetime import datetime
            mock_timestamp.return_value = datetime.now()
            
            # Mock embedding service - patch where it's imported (inside the method)
            with patch('vasttamsserver.vast.embedding_service.EmbeddingService') as mock_embedding_class:
                mock_embedding_service = Mock()
                mock_embedding_service.create_embedding = AsyncMock(return_value=create_mock_vector(768))
                mock_embedding_service._embedder = Mock()  # Make it available
                mock_embedding_class.return_value = mock_embedding_service
                
                yield service
    
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
        
        # ingest_text returns a dict with results
        assert isinstance(result, dict)
        assert result['entity_id'] == entity_id
        assert result['entity_type'] == "object"
        assert 'embedding_model' in result
        assert 'embedding_date' in result
        assert 'dimension' in result
        
        # Verify update_vector was called (embedding service is created inside the method)
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
    async def test_ingest_text_embedding_service_unavailable(self):
        """Test text ingestion when embedding service is unavailable"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = VastObjectVectorService(mock_db, mock_s3)
        
        # Mock embedding service to be unavailable - patch where it's imported
        with patch('vasttamsserver.vast.embedding_service.EmbeddingService') as mock_embedding_class:
            mock_embedding_service = Mock()
            mock_embedding_service._embedder = None  # Not available
            mock_embedding_class.return_value = mock_embedding_service
            
            with pytest.raises(HTTPException) as exc_info:
                await service.ingest_text(
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
        
        # Mock embedding service - patch where it's imported (inside the method)
        with patch('vasttamsserver.vast.embedding_service.EmbeddingService') as mock_embedding_class:
            mock_embedding_service = Mock()
            mock_embedding_service.create_embedding = AsyncMock(return_value=create_mock_vector(768))
            mock_embedding_service._embedder = Mock()  # Make it available
            mock_embedding_class.return_value = mock_embedding_service
            
            yield service
    
    @pytest.mark.asyncio
    async def test_search_by_text_success(self, mock_service):
        """Test successful text-based search"""
        query_text = "Find similar documents"
        
        result = await mock_service.search_by_text(
            text=query_text
        )
        
        # search_by_text returns a dict with query_text, embedding_model, distance_algorithm, results, etc.
        assert isinstance(result, dict)
        assert 'query_text' in result
        assert 'results' in result
        assert len(result['results']) == 1
        
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
    async def test_search_by_text_embedding_service_unavailable(self):
        """Test text search when embedding service is unavailable"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = VastObjectVectorService(mock_db, mock_s3)
        
        # Mock embedding service to be unavailable - patch where it's imported
        with patch('vasttamsserver.vast.embedding_service.EmbeddingService') as mock_embedding_class:
            mock_embedding_service = Mock()
            mock_embedding_service._embedder = None  # Not available
            mock_embedding_class.return_value = mock_embedding_service
            
            with pytest.raises(HTTPException) as exc_info:
                await service.search_by_text(text="Test")
            
            assert exc_info.value.status_code == 503
            assert "Embedding service is not available" in exc_info.value.detail


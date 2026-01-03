#!/usr/bin/env python3
"""
Router Tests for VAST Vector Endpoints

Tests vast/router.py endpoints.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import uuid
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.vast.models import ObjectVectorPut, VectorSearchRequest, VectorSearchResult, VectorSearchMatch
from vasttamsserver.vast.service import VastObjectVectorService


def create_mock_vector(dimension=768):
    """Helper to create a mock vector of specified dimension"""
    return [0.1 * i for i in range(dimension)]


class TestVastRouter:
    """Test VAST vector router endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock VastObjectVectorService"""
        service = Mock(spec=VastObjectVectorService)
        service.update_object_vector = AsyncMock(return_value=True)
        service.search_vectors = AsyncMock(return_value={'matches': []})
        return service
    
    @pytest.fixture
    def mock_user_session(self):
        """Create a mock user session"""
        session = Mock()
        session.user_id = str(uuid.uuid4())
        session.username = "test_user"
        return session
    
    @pytest.mark.asyncio
    async def test_update_object_vector_endpoint_success(self, mock_service, mock_user_session):
        """Test successful vector update endpoint"""
        from vasttamsserver.vast.router import update_object_vector
        
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(768)
        vector_data = ObjectVectorPut(
            vector=vector,
            summary="Test summary",
            embedding_model="test-model"
        )
        
        result = await update_object_vector(
            object_id=object_id,
            vector_data=vector_data,
            service=mock_service,
            user_session=mock_user_session
        )
        
        assert result["message"] == "Vector updated successfully"
        assert result["object_id"] == object_id
        mock_service.update_vector.assert_called_once_with(
            entity_id=object_id,
            entity_type="object",
            vector=vector,
            summary="Test summary",
            embedding_model="test-model"
        )
    
    @pytest.mark.asyncio
    async def test_update_object_vector_endpoint_invalid_dimension(self, mock_service, mock_user_session):
        """Test vector update endpoint with invalid dimension
        
        Note: Pydantic validation happens before the endpoint code runs,
        so we test the validation error from the model itself.
        """
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(512)  # Wrong dimension
        
        # Pydantic will raise ValidationError before reaching the endpoint
        with pytest.raises(Exception) as exc_info:
            vector_data = ObjectVectorPut(
                vector=vector,
                summary="Test summary"
            )
        
        # Verify it's a validation error about dimensions
        assert "768 dimensions" in str(exc_info.value) or "512" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_object_vector_endpoint_service_failure(self, mock_service, mock_user_session):
        """Test vector update endpoint when service fails"""
        from vasttamsserver.vast.router import update_object_vector
        
        object_id = str(uuid.uuid4())
        vector = create_mock_vector(768)
        vector_data = ObjectVectorPut(vector=vector)
        
        mock_service.update_vector = AsyncMock(return_value=False)
        
        with pytest.raises(HTTPException) as exc_info:
            await update_object_vector(
                object_id=object_id,
                vector_data=vector_data,
                service=mock_service,
                user_session=mock_user_session
            )
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_search_vectors_endpoint_success(self, mock_service, mock_user_session):
        """Test successful vector search endpoint"""
        from vasttamsserver.vast.router import search_vectors
        
        query_vector = create_mock_vector(768)
        search_request = VectorSearchRequest(
            vector=query_vector,
            num_matches=10,
            distance_metric="cosine",
            distance_numerical_value=0.75
        )
        
        # Mock search results
        object_id1 = str(uuid.uuid4())
        segment_id1 = str(uuid.uuid4())
        flow_id1 = str(uuid.uuid4())
        source_id1 = str(uuid.uuid4())
        
        mock_service.search_vectors = AsyncMock(return_value={
            'matches': [
                {
                    'entity_id': object_id1,
                    'entity_type': 'object',
                    'object_id': object_id1,
                    'segment_id': segment_id1,
                    'flow_id': flow_id1,
                    'source_id': source_id1,
                    'distance': 0.5
                }
            ]
        })
        
        result = await search_vectors(
            search_request=search_request,
            service=mock_service,
            user_session=mock_user_session
        )
        
        assert isinstance(result, VectorSearchResult)
        assert len(result.matches) == 1
        assert result.matches[0].object_id == object_id1
        assert result.matches[0].distance == 0.5
        
        mock_service.search_vectors.assert_called_once_with(
            query_vector=query_vector,
            num_matches=10,
            distance_metric="cosine",
            distance_numerical_value=0.75,
            entity_types=None
        )
    
    @pytest.mark.asyncio
    async def test_search_vectors_endpoint_invalid_dimension(self, mock_service, mock_user_session):
        """Test vector search endpoint with invalid dimension
        
        The router validates vector dimension matches the configured model dimension.
        """
        from vasttamsserver.vast.router import search_vectors
        
        query_vector = create_mock_vector(512)  # Wrong dimension (should be 768)
        search_request = VectorSearchRequest(vector=query_vector)
        
        # Router should raise HTTPException for invalid dimension
        with pytest.raises(HTTPException) as exc_info:
            await search_vectors(
                search_request=search_request,
                service=mock_service,
                user_session=mock_user_session
            )
        
        # Verify it's a validation error about dimensions
        assert exc_info.value.status_code == 400
        assert "dimensions" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_search_vectors_endpoint_empty_results(self, mock_service, mock_user_session):
        """Test vector search endpoint with empty results"""
        from vasttamsserver.vast.router import search_vectors
        
        query_vector = create_mock_vector(768)
        search_request = VectorSearchRequest(vector=query_vector)
        
        mock_service.search_vectors = AsyncMock(return_value={'matches': []})
        
        result = await search_vectors(
            search_request=search_request,
            service=mock_service,
            user_session=mock_user_session
        )
        
        assert isinstance(result, VectorSearchResult)
        assert len(result.matches) == 0
    
    @pytest.mark.asyncio
    async def test_search_vectors_endpoint_with_defaults(self, mock_service, mock_user_session):
        """Test vector search endpoint with default parameters"""
        from vasttamsserver.vast.router import search_vectors
        
        query_vector = create_mock_vector(768)
        search_request = VectorSearchRequest(
            vector=query_vector,
            num_matches=None,
            distance_metric=None,
            distance_numerical_value=None
        )
        
        mock_service.search_vectors = AsyncMock(return_value={'matches': []})
        
        await search_vectors(
            search_request=search_request,
            service=mock_service,
            user_session=mock_user_session
        )
        
        # Verify service was called with None values (will use defaults)
        call_args = mock_service.search_vectors.call_args
        assert call_args[1]['num_matches'] is None
        assert call_args[1]['distance_metric'] is None
        assert call_args[1]['distance_numerical_value'] is None
    
    @pytest.mark.asyncio
    async def test_search_vectors_endpoint_service_error(self, mock_service, mock_user_session):
        """Test vector search endpoint when service raises error"""
        from vasttamsserver.vast.router import search_vectors
        
        query_vector = create_mock_vector(768)
        search_request = VectorSearchRequest(vector=query_vector)
        
        mock_service.search_vectors = AsyncMock(side_effect=Exception("Service error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await search_vectors(
                search_request=search_request,
                service=mock_service,
                user_session=mock_user_session
            )
        
        assert exc_info.value.status_code == 500


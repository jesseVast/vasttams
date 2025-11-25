#!/usr/bin/env python3
"""
Tests for entity vectorization service.

Tests automatic vectorization of flows, sources, and objects.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import uuid
import json

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.vast.entity_vectorization import EntityVectorizationService


class TestEntityVectorization:
    """Test entity vectorization service"""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock EntityVectorizationService"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = EntityVectorizationService(mock_db, mock_s3)
        
        # Mock embedding service
        service.embedding_service.create_embedding = AsyncMock(return_value=[0.1] * 768)
        service.embedding_service._embedder = Mock()  # Make it available
        
        # Mock vector service
        service.vector_service.update_vector = AsyncMock(return_value=True)
        
        return service
    
    @pytest.mark.asyncio
    async def test_vectorize_flow(self, mock_service):
        """Test vectorizing a flow"""
        flow_id = str(uuid.uuid4())
        flow_dict = {
            "source_id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "codec": "video/h264",
            "label": "Test Flow"
        }
        
        await mock_service.vectorize_entity(flow_dict, flow_id, "flow")
        
        # Verify embedding was created
        mock_service.embedding_service.create_embedding.assert_called_once()
        
        # Verify vector was stored
        mock_service.vector_service.update_vector.assert_called_once()
        call_args = mock_service.vector_service.update_vector.call_args
        assert call_args[1]['entity_id'] == flow_id
        assert call_args[1]['entity_type'] == "flow"
    
    @pytest.mark.asyncio
    async def test_vectorize_source(self, mock_service):
        """Test vectorizing a source"""
        source_id = str(uuid.uuid4())
        source_dict = {
            "format": "urn:x-nmos:format:video",
            "label": "Test Source"
        }
        
        await mock_service.vectorize_entity(source_dict, source_id, "source")
        
        mock_service.vector_service.update_vector.assert_called_once()
        call_args = mock_service.vector_service.update_vector.call_args
        assert call_args[1]['entity_id'] == source_id
        assert call_args[1]['entity_type'] == "source"
    
    @pytest.mark.asyncio
    async def test_vectorize_object(self, mock_service):
        """Test vectorizing an object"""
        object_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        obj_dict = {
            "referenced_by_flows": [flow_id],
            "first_referenced_by_flow": flow_id,
            "timerange": {"value": "0:0"},
            "size": 1000
        }
        
        await mock_service.vectorize_entity(obj_dict, object_id, "object")
        
        mock_service.vector_service.update_vector.assert_called_once()
        call_args = mock_service.vector_service.update_vector.call_args
        assert call_args[1]['entity_id'] == object_id
        assert call_args[1]['entity_type'] == "object"
    
    @pytest.mark.asyncio
    async def test_delete_entity_vector(self, mock_service):
        """Test removing vector for deleted entity"""
        entity_id = str(uuid.uuid4())
        
        # delete_entity_vector currently just logs and returns True
        # It doesn't actually call delete_vector yet (see TODO in code)
        result = await mock_service.delete_entity_vector(entity_id, "flow")
        
        # Should return True (non-blocking)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_entity_to_text_excludes_id(self, mock_service):
        """Test that entity_to_text excludes ID field"""
        flow_id = str(uuid.uuid4())
        flow_dict = {
            "id": flow_id,
            "source_id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "codec": "video/h264",
            "label": "Test Flow"
        }
        
        text = mock_service._entity_to_text(flow_dict, "flow")
        
        # ID should not be in the text representation
        # The text format is "label: value, codec: value, ..." so we check the dict was processed
        # The _entity_to_text method removes id fields from the dict before converting to text
        # So the flow_id should not appear in the text
        assert flow_id not in text
        # But label and codec should be there
        assert "Test Flow" in text
        assert "video/h264" in text
    
    @pytest.mark.asyncio
    async def test_entity_to_text_excludes_internal_fields(self, mock_service):
        """Test that entity_to_text excludes internal metadata fields"""
        flow_dict = {
            "id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),
            "format": "urn:x-nmos:format:video",
            "codec": "video/h264",
            "label": "Test Flow",
            "created": "2024-01-01T00:00:00Z",
            "metadata_updated": "2024-01-01T00:00:00Z"
        }
        
        text = mock_service._entity_to_text(flow_dict, "flow")
        
        # Internal fields should not be in the text representation
        assert "created" not in text
        assert "metadata_updated" not in text


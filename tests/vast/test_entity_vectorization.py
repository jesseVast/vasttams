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
from vasttamsserver.flows.models import Flow
from vasttamsserver.sources.models import Source
from vasttamsserver.objects.models import Object
from vasttamsserver.common.models import TimeRange
from datetime import datetime


class TestEntityVectorization:
    """Test entity vectorization service"""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock EntityVectorizationService"""
        mock_db = Mock()
        mock_s3 = Mock()
        service = EntityVectorizationService(mock_db, mock_s3)
        
        # Mock embedding service
        service._embedding_service = Mock()
        service._embedding_service.create_embedding = AsyncMock(return_value=[0.1] * 768)
        
        # Mock vector service
        service._vector_service = Mock()
        service._vector_service.update_vector = AsyncMock(return_value=True)
        
        return service
    
    @pytest.mark.asyncio
    async def test_vectorize_flow(self, mock_service):
        """Test vectorizing a flow"""
        flow = Flow(
            id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow"
        )
        
        await mock_service.vectorize_entity(flow, "flow")
        
        # Verify embedding was created
        mock_service._embedding_service.create_embedding.assert_called_once()
        
        # Verify vector was stored
        mock_service._vector_service.update_vector.assert_called_once()
        call_args = mock_service._vector_service.update_vector.call_args
        assert call_args[1]['entity_id'] == flow.id
        assert call_args[1]['entity_type'] == "flow"
    
    @pytest.mark.asyncio
    async def test_vectorize_source(self, mock_service):
        """Test vectorizing a source"""
        source = Source(
            id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            label="Test Source"
        )
        
        await mock_service.vectorize_entity(source, "source")
        
        mock_service._vector_service.update_vector.assert_called_once()
        call_args = mock_service._vector_service.update_vector.call_args
        assert call_args[1]['entity_id'] == source.id
        assert call_args[1]['entity_type'] == "source"
    
    @pytest.mark.asyncio
    async def test_vectorize_object(self, mock_service):
        """Test vectorizing an object"""
        object_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        obj = Object(
            id=object_id,
            referenced_by_flows=[flow_id],
            first_referenced_by_flow=flow_id,
            timerange=TimeRange(value="0:0"),
            size=1000
        )
        
        await mock_service.vectorize_entity(obj, "object")
        
        mock_service._vector_service.update_vector.assert_called_once()
        call_args = mock_service._vector_service.update_vector.call_args
        assert call_args[1]['entity_id'] == object_id
        assert call_args[1]['entity_type'] == "object"
    
    @pytest.mark.asyncio
    async def test_devectorize_entity(self, mock_service):
        """Test removing vector for deleted entity"""
        entity_id = str(uuid.uuid4())
        
        # Mock vector service delete method
        mock_service._vector_service.delete_vector = AsyncMock(return_value=True)
        
        await mock_service.devectorize_entity(entity_id, "flow")
        
        mock_service._vector_service.delete_vector.assert_called_once_with(
            entity_id=entity_id,
            entity_type="flow"
        )
    
    @pytest.mark.asyncio
    async def test_entity_to_text_excludes_id(self, mock_service):
        """Test that entity_to_text excludes ID field"""
        flow = Flow(
            id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow"
        )
        
        text = mock_service._entity_to_text(flow)
        text_dict = json.loads(text)
        
        # ID should not be in the text representation
        assert "id" not in text_dict
    
    @pytest.mark.asyncio
    async def test_entity_to_text_excludes_internal_fields(self, mock_service):
        """Test that entity_to_text excludes internal metadata fields"""
        flow = Flow(
            id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow"
        )
        
        text = mock_service._entity_to_text(flow)
        text_dict = json.loads(text)
        
        # Internal fields should not be present
        assert "_internal_metadata" not in text_dict


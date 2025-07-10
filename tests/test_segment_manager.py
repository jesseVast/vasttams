import pytest
from unittest.mock import AsyncMock, MagicMock
from app.segments import SegmentManager
from app.models import FlowSegment, FlowStoragePost
import uuid
from fastapi import Request, UploadFile
from tests.test_settings import get_test_settings

@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_flow_segments = AsyncMock()
    store.create_flow_segment = AsyncMock()
    store.delete_flow_segments = AsyncMock()
    store.get_flow = AsyncMock()
    store.s3_store = MagicMock()
    store.s3_store.generate_presigned_url = AsyncMock()
    return store

@pytest.fixture
def segment_manager(mock_store):
    return SegmentManager(store=mock_store)

@pytest.mark.asyncio
async def test_get_segments(segment_manager, mock_store):
    mock_store.get_flow_segments.return_value = []
    result = await segment_manager.get_segments("flow1")
    assert result == []

@pytest.mark.asyncio
async def test_create_segment(segment_manager, mock_store):
    request = MagicMock(spec=Request)
    file = MagicMock(spec=UploadFile)
    file.read = AsyncMock(return_value=b"data")
    file.content_type = "video/mp4"
    mock_store.create_flow_segment.return_value = True
    segment_json = '{"object_id": "obj1", "timerange": "[0:0_10:0)"}'
    result = await segment_manager.create_segment("flow1", request, file, segment=segment_json)
    assert result.object_id == "obj1"

@pytest.mark.asyncio
async def test_delete_segments(segment_manager, mock_store):
    mock_store.delete_flow_segments.return_value = True
    result = await segment_manager.delete_segments("flow1")
    assert result["message"] == "Flow segments deleted"

# Add more tests for allocate_storage and edge cases 
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api.flows import FlowManager
from app.models.models import VideoFlow, Tags
import uuid
from datetime import datetime
from tests.test_settings import get_test_settings

@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_flow = AsyncMock()
    store.create_flow = AsyncMock()
    store.update_flow = AsyncMock()
    store.delete_flow = AsyncMock()
    store.list_flows = AsyncMock()
    return store

@pytest.fixture
def flow_manager(mock_store):
    return FlowManager(store=mock_store)

@pytest.mark.asyncio
async def test_create_flow(flow_manager, mock_store):
    flow = VideoFlow(id=uuid.uuid4(), source_id=uuid.uuid4(), format="urn:x-nmos:format:video", codec="video/mp4", frame_width=1920, frame_height=1080, frame_rate="25/1")
    mock_store.create_flow.return_value = True
    result = await flow_manager.create_flow(flow)
    assert result == flow
    mock_store.create_flow.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_flow_found(flow_manager, mock_store):
    flow = VideoFlow(id=uuid.uuid4(), source_id=uuid.uuid4(), format="urn:x-nmos:format:video", codec="video/mp4", frame_width=1920, frame_height=1080, frame_rate="25/1")
    mock_store.get_flow.return_value = flow
    result = await flow_manager.get_flow(str(flow.id))
    assert result == flow

@pytest.mark.asyncio
async def test_get_flow_not_found(flow_manager, mock_store):
    mock_store.get_flow.return_value = None
    with pytest.raises(Exception):
        await flow_manager.get_flow(str(uuid.uuid4()))

@pytest.mark.asyncio
async def test_update_flow(flow_manager, mock_store):
    flow = VideoFlow(id=uuid.uuid4(), source_id=uuid.uuid4(), format="urn:x-nmos:format:video", codec="video/mp4", frame_width=1920, frame_height=1080, frame_rate="25/1")
    mock_store.get_flow.return_value = flow
    mock_store.update_flow.return_value = True
    result = await flow_manager.update_flow(str(flow.id), flow)
    assert result == flow

@pytest.mark.asyncio
async def test_delete_flow(flow_manager, mock_store):
    mock_store.delete_flow.return_value = True
    result = await flow_manager.delete_flow(str(uuid.uuid4()))
    assert result["message"] == "Flow deleted"

# Add more tests for tags, description, label, read_only, and collection methods, including edge cases 
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.objects import ObjectManager
from app.models import Object
import uuid
from datetime import datetime
from tests.test_settings import get_test_settings

@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_object = AsyncMock()
    store.create_object = AsyncMock()
    return store

@pytest.fixture
def object_manager(mock_store):
    return ObjectManager(store=mock_store)

@pytest.mark.asyncio
async def test_create_object(object_manager, mock_store):
    obj = Object(
        id="obj1",  # Changed from object_id to id
        referenced_by_flows=[],  # Changed from flow_references to referenced_by_flows
        first_referenced_by_flow=uuid.uuid4()  # New field
    )
    assert obj.id == "obj1"
    assert len(obj.referenced_by_flows) == 0
    mock_store.create_object.return_value = True
    result = await object_manager.create_object(obj)
    assert result == obj
    mock_store.create_object.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_object_found(object_manager, mock_store):
    obj = Object(
        id="obj1",  # Changed from object_id to id
        referenced_by_flows=[],  # Changed from flow_references to referenced_by_flows
        first_referenced_by_flow=uuid.uuid4()  # New field
    )
    assert obj.id == "obj1"
    # Return a dict instead of Object instance to match the expected format
    mock_store.get_object.return_value = {
        'object_id': 'obj1',
        'flow_references': []
    }
    result = await object_manager.get_object("obj1")
    assert result.id == "obj1"

@pytest.mark.asyncio
async def test_get_object_not_found(object_manager, mock_store):
    mock_store.get_object.return_value = None
    with pytest.raises(Exception):
        await object_manager.get_object("obj2")

# Add more tests for edge cases 
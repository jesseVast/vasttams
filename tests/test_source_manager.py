import pytest
from unittest.mock import AsyncMock, MagicMock
from app.sources import SourceManager
from app.models import Source, Tags
import uuid
from datetime import datetime
from tests.test_settings import get_test_settings

@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_source = AsyncMock()
    store.create_source = AsyncMock()
    store.update_source = AsyncMock()
    store.delete_source = AsyncMock()
    store.list_sources = AsyncMock()
    return store

@pytest.fixture
def source_manager(mock_store):
    return SourceManager(store=mock_store)

@pytest.mark.asyncio
async def test_create_source(source_manager, mock_store):
    source = Source(id=uuid.uuid4(), format="urn:x-nmos:format:video", label="Test Source")
    mock_store.create_source.return_value = True
    result = await source_manager.create_source(source)
    assert result == source
    mock_store.create_source.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_source_found(source_manager, mock_store):
    source = Source(id=uuid.uuid4(), format="urn:x-nmos:format:video", label="Test Source")
    mock_store.get_source.return_value = source
    result = await source_manager.get_source(str(source.id))
    assert result == source

@pytest.mark.asyncio
async def test_get_source_not_found(source_manager, mock_store):
    mock_store.get_source.return_value = None
    with pytest.raises(Exception):
        await source_manager.get_source(str(uuid.uuid4()))

@pytest.mark.asyncio
async def test_update_source(source_manager, mock_store):
    source = Source(id=uuid.uuid4(), format="urn:x-nmos:format:video", label="Test Source")
    mock_store.get_source.return_value = source
    mock_store.update_source.return_value = True
    result = await source_manager.update_source(str(source.id), source)
    assert result == source

@pytest.mark.asyncio
async def test_delete_source(source_manager, mock_store):
    mock_store.delete_source.return_value = True
    result = await source_manager.delete_source(str(uuid.uuid4()))
    assert result["message"] == "Source deleted"

# Add more tests for tags, description, and label methods, including edge cases 
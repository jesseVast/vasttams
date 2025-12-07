"""
Tests for source API methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from vasttamsclient.api import sources as source_api
from vasttamsclient.exceptions import TAMSAPIError


class TestSourceAPI:
    """Tests for source API methods."""
    
    @pytest.fixture
    def mock_client(self, client, mock_session):
        """Create a mock client with session."""
        client._session = mock_session
        return client
    
    @pytest.mark.asyncio
    async def test_create_source_success(self, mock_client, mock_session):
        """Test successful source creation."""
        source_data = {
            "id": "source-123",
            "format": "urn:x-nmos:format:video",
            "label": "Test Source"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json = MagicMock(return_value=source_data)
        
        mock_session.request = AsyncMock(return_value=mock_response)
        
        result = await source_api.create_source(mock_client, source_data)
        assert result == source_data
        mock_session.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_source_error(self, mock_client, mock_session):
        """Test source creation with error."""
        source_data = {"format": "urn:x-nmos:format:video"}
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid format"
        
        mock_session.request = AsyncMock(return_value=mock_response)
        
        with pytest.raises(TAMSAPIError) as exc_info:
            await source_api.create_source(mock_client, source_data)
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_get_source_success(self, mock_client, mock_session):
        """Test getting a source successfully."""
        source_data = {
            "id": "source-123",
            "format": "urn:x-nmos:format:video",
            "label": "Test Source"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=source_data)
        
        mock_session.request = AsyncMock(return_value=mock_response)
        
        result = await source_api.get_source(mock_client, "source-123")
        assert result == source_data
    
    @pytest.mark.asyncio
    async def test_get_source_not_found(self, mock_client, mock_session):
        """Test getting a non-existent source."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_session.request = AsyncMock(return_value=mock_response)
        
        result = await source_api.get_source(mock_client, "nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_source_label_success(self, mock_client, mock_session):
        """Test updating a source label successfully."""
        source_id = "source-123"
        label = "Updated Label"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_session.request = AsyncMock(return_value=mock_response)
        
        await source_api.update_source_label(mock_client, source_id, label)
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[1]["data"] == label
        assert call_args[1]["headers"]["Content-Type"] == "text/plain"
    
    @pytest.mark.asyncio
    async def test_delete_source_success(self, mock_client, mock_session):
        """Test deleting a source successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        
        mock_session.request = AsyncMock(return_value=mock_response)
        
        await source_api.delete_source(mock_client, "source-123")
        mock_session.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_sources_success(self, mock_client, mock_session):
        """Test listing sources successfully."""
        sources_data = [
            {"id": "source-1", "format": "urn:x-nmos:format:video", "label": "Source 1"},
            {"id": "source-2", "format": "urn:x-nmos:format:video", "label": "Source 2"}
        ]
        mock_response_data = {"data": sources_data}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=mock_response_data)
        
        mock_session.request = AsyncMock(return_value=mock_response)
        
        result = await source_api.list_sources(mock_client, {})
        assert result == sources_data


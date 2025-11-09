"""
Tests for object API methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from vasttamsclient.exceptions import TAMSAPIError


class TestObjectAPI:
    """Tests for object API methods."""
    
    @pytest.mark.asyncio
    async def test_get_object_success(self, client):
        """Test getting an object successfully."""
        object_id = "object-123"
        mock_object = {"id": object_id, "label": "Test Object"}
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_object)
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.objects import get_object
        result = await get_object(client, object_id)
        
        assert result == mock_object
        client._session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_object_not_found(self, client):
        """Test getting a non-existent object."""
        object_id = "nonexistent"
        
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.objects import get_object
        result = await get_object(client, object_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_object_error(self, client):
        """Test getting an object with server error."""
        object_id = "object-123"
        
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.objects import get_object
        with pytest.raises(TAMSAPIError) as exc_info:
            await get_object(client, object_id)
        
        assert "Failed to get object" in str(exc_info.value)
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_list_objects_success(self, client):
        """Test listing objects successfully."""
        mock_objects = [
            {"id": "object-1", "label": "Object 1"},
            {"id": "object-2", "label": "Object 2"}
        ]
        mock_response_data = {"data": mock_objects}
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.objects import list_objects
        result = await list_objects(client)
        
        assert result == mock_objects
        client._session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_objects_with_params(self, client):
        """Test listing objects with query parameters."""
        query_params = {"limit": 10, "offset": 0}
        mock_objects = [{"id": "object-1"}]
        mock_response_data = {"data": mock_objects}
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.objects import list_objects
        result = await list_objects(client, query_params=query_params)
        
        assert result == mock_objects
        call_args = client._session.get.call_args
        assert call_args[1]["params"] == query_params
    
    @pytest.mark.asyncio
    async def test_list_objects_error(self, client):
        """Test listing objects with server error."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.objects import list_objects
        with pytest.raises(TAMSAPIError) as exc_info:
            await list_objects(client)
        
        assert "Failed to list objects" in str(exc_info.value)
        assert exc_info.value.status_code == 500


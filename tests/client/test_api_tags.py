"""
Tests for tags API methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from vasttamsclient.exceptions import TAMSAPIError


class TestTagsAPI:
    """Tests for tags API methods."""
    
    @pytest.mark.asyncio
    async def test_get_tags_source_success(self, client):
        """Test getting tags for a source."""
        entity_id = "source-123"
        mock_tags = {"quality": "hd", "bitrate": "high"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=mock_tags)
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tags
        result = await get_tags(client, "source", entity_id)
        
        assert result == mock_tags
    
    @pytest.mark.asyncio
    async def test_get_tags_with_list_values(self, client):
        """Test getting tags with list values."""
        entity_id = "source-123"
        mock_tags = {"quality": ["hd", "4k"], "bitrate": "high"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=mock_tags)
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tags
        result = await get_tags(client, "source", entity_id)
        
        assert result == mock_tags
        assert isinstance(result["quality"], list)
        assert isinstance(result["bitrate"], str)
    
    @pytest.mark.asyncio
    async def test_get_tags_flow_success(self, client):
        """Test getting tags for a flow."""
        entity_id = "flow-123"
        mock_tags = {"quality": "hd"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=mock_tags)
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tags
        result = await get_tags(client, "flow", entity_id)
        
        assert result == mock_tags
    
    @pytest.mark.asyncio
    async def test_get_tags_not_found(self, client):
        """Test getting tags when entity not found."""
        entity_id = "nonexistent"
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tags
        result = await get_tags(client, "source", entity_id)
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_tags_invalid_entity_type(self, client):
        """Test getting tags with invalid entity type."""
        from vasttamsclient.api.tags import get_tags
        with pytest.raises(ValueError) as exc_info:
            await get_tags(client, "invalid", "id-123")
        
        assert "Unsupported entity type" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_tag_success(self, client):
        """Test getting a specific tag."""
        entity_id = "source-123"
        tag_name = "quality"
        tag_value = "hd"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=tag_value)
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tag
        result = await get_tag(client, "source", entity_id, tag_name)
        
        assert result == tag_value
    
    @pytest.mark.asyncio
    async def test_get_tag_json_encoded(self, client):
        """Test getting a tag that's JSON-encoded."""
        entity_id = "source-123"
        tag_name = "quality"
        json_value = "hd"  # JSON response returns decoded value
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=json_value)
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tag
        result = await get_tag(client, "source", entity_id, tag_name)
        
        assert result == "hd"  # Should be decoded from JSON
    
    @pytest.mark.asyncio
    async def test_get_tag_list_value(self, client):
        """Test getting a tag with list value."""
        entity_id = "source-123"
        tag_name = "quality"
        tag_value = ["hd", "4k"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=tag_value)
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tag
        result = await get_tag(client, "source", entity_id, tag_name)
        
        assert result == tag_value
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_tag_not_found(self, client):
        """Test getting a non-existent tag."""
        entity_id = "source-123"
        tag_name = "nonexistent"
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import get_tag
        result = await get_tag(client, "source", entity_id, tag_name)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_tag_success(self, client):
        """Test setting a tag."""
        entity_id = "source-123"
        tag_name = "quality"
        tag_value = "hd"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import set_tag
        await set_tag(client, "source", entity_id, tag_name, tag_value)
        
        client._request.assert_called_once()
        call_args = client._request.call_args
        assert call_args[1]["data"] == tag_value
        assert call_args[1]["headers"]["Content-Type"] == "text/plain"
    
    @pytest.mark.asyncio
    async def test_set_tag_list_value(self, client):
        """Test setting a tag with list value."""
        entity_id = "source-123"
        tag_name = "quality"
        tag_value = ["hd", "4k"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import set_tag
        await set_tag(client, "source", entity_id, tag_name, tag_value)
        
        client._request.assert_called_once()
        call_args = client._request.call_args
        import json
        assert call_args[1]["data"] == json.dumps(tag_value)
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_set_tag_error(self, client):
        """Test setting a tag with error."""
        entity_id = "source-123"
        tag_name = "quality"
        tag_value = "hd"
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import set_tag
        with pytest.raises(TAMSAPIError) as exc_info:
            await set_tag(client, "source", entity_id, tag_name, tag_value)
        
        assert "Failed to set tag" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_tag_success(self, client):
        """Test deleting a tag."""
        entity_id = "source-123"
        tag_name = "quality"
        
        mock_response = MagicMock()
        mock_response.status_code = 204
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import delete_tag
        await delete_tag(client, "source", entity_id, tag_name)
        
        client._request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_tag_error(self, client):
        """Test deleting a tag with error."""
        entity_id = "source-123"
        tag_name = "quality"
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        client._request = AsyncMock(return_value=mock_response)
        
        from vasttamsclient.api.tags import delete_tag
        with pytest.raises(TAMSAPIError) as exc_info:
            await delete_tag(client, "source", entity_id, tag_name)
        
        assert "Failed to delete tag" in str(exc_info.value)


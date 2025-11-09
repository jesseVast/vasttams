"""
Tests for segment API methods.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from vasttamsclient.exceptions import TAMSAPIError


class TestSegmentAPI:
    """Tests for segment API methods."""
    
    @pytest.mark.asyncio
    async def test_create_segment_json_only(self, client):
        """Test creating a segment with JSON data only."""
        flow_id = "flow-123"
        segment_data = {"timerange": {"value": "[0:0_10:0)"}}
        mock_segment = {"id": "segment-123", "flow_id": flow_id, **segment_data}
        
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value=mock_segment)
        
        mock_post_context = MagicMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.post = MagicMock(return_value=mock_post_context)
        
        from vasttamsclient.api.segments import create_segment
        result = await create_segment(client, flow_id, segment_data)
        
        assert result == mock_segment
        client._session.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_segment_with_file(self, client, tmp_path):
        """Test creating a segment with file upload."""
        flow_id = "flow-123"
        segment_data = {"timerange": {"value": "[0:0_10:0)"}}
        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"fake video data")
        
        mock_segment = {"id": "segment-123", "flow_id": flow_id, **segment_data}
        
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value=mock_segment)
        
        mock_post_context = MagicMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.post = MagicMock(return_value=mock_post_context)
        
        from vasttamsclient.api.segments import create_segment
        result = await create_segment(client, flow_id, segment_data, file_path=str(test_file))
        
        assert result == mock_segment
        client._session.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_segment_file_not_found(self, client):
        """Test creating segment with non-existent file."""
        flow_id = "flow-123"
        segment_data = {"timerange": {"value": "[0:0_10:0)"}}
        
        from vasttamsclient.api.segments import create_segment
        with pytest.raises(TAMSAPIError) as exc_info:
            await create_segment(client, flow_id, segment_data, file_path="/nonexistent/file.mp4")
        
        assert "File not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_segment_error(self, client):
        """Test creating segment with server error."""
        flow_id = "flow-123"
        segment_data = {"timerange": {"value": "[0:0_10:0)"}}
        
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")
        
        mock_post_context = MagicMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.post = MagicMock(return_value=mock_post_context)
        
        from vasttamsclient.api.segments import create_segment
        with pytest.raises(TAMSAPIError) as exc_info:
            await create_segment(client, flow_id, segment_data)
        
        assert "Failed to create segment" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_segments_success(self, client):
        """Test listing segments successfully."""
        flow_id = "flow-123"
        mock_segments = [
            {"id": "segment-1", "flow_id": flow_id},
            {"id": "segment-2", "flow_id": flow_id}
        ]
        mock_response_data = {"data": mock_segments}
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.segments import list_segments
        result = await list_segments(client, flow_id)
        
        assert result == mock_segments
    
    @pytest.mark.asyncio
    async def test_list_segments_with_params(self, client):
        """Test listing segments with query parameters."""
        flow_id = "flow-123"
        query_params = {"limit": 10}
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": []})
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        from vasttamsclient.api.segments import list_segments
        await list_segments(client, flow_id, query_params=query_params)
        
        call_args = client._session.get.call_args
        assert call_args[1]["params"] == query_params
    
    @pytest.mark.asyncio
    async def test_delete_segments_success(self, client):
        """Test deleting segments successfully."""
        flow_id = "flow-123"
        
        mock_response = AsyncMock()
        mock_response.status = 204
        
        mock_delete_context = MagicMock()
        mock_delete_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_delete_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.delete = MagicMock(return_value=mock_delete_context)
        
        from vasttamsclient.api.segments import delete_segments
        await delete_segments(client, flow_id)
        
        client._session.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_segments_error(self, client):
        """Test deleting segments with error."""
        flow_id = "flow-123"
        
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")
        
        mock_delete_context = MagicMock()
        mock_delete_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_delete_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.delete = MagicMock(return_value=mock_delete_context)
        
        from vasttamsclient.api.segments import delete_segments
        with pytest.raises(TAMSAPIError) as exc_info:
            await delete_segments(client, flow_id)
        
        assert "Failed to delete segments" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_allocate_storage_success(self, client):
        """Test allocating storage successfully."""
        flow_id = "flow-123"
        mock_storage = {
            "media_objects": [{
                "object_id": "object-123",
                "put_url": {"url": "https://s3.example.com/upload"}
            }]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value=mock_storage)
        
        mock_post_context = MagicMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.post = MagicMock(return_value=mock_post_context)
        
        from vasttamsclient.api.segments import allocate_storage
        result = await allocate_storage(client, flow_id)
        
        assert result == mock_storage
    
    @pytest.mark.asyncio
    async def test_allocate_storage_with_params(self, client):
        """Test allocating storage with parameters."""
        flow_id = "flow-123"
        storage_id = "storage-123"
        label = "test-label"
        
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={"media_objects": []})
        
        mock_post_context = MagicMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.post = MagicMock(return_value=mock_post_context)
        
        from vasttamsclient.api.segments import allocate_storage
        await allocate_storage(client, flow_id, label=label, storage_id=storage_id, limit=5)
        
        call_args = client._session.post.call_args
        call_data = call_args[1]["json"]
        assert call_data["limit"] == 5
        assert call_data["label"] == label
        assert call_data["storage_id"] == storage_id
    
    @pytest.mark.asyncio
    async def test_upload_to_storage_with_data(self, client):
        """Test uploading data to storage."""
        presigned_url = "https://s3.example.com/upload"
        data = b"test data"
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        mock_put_context = MagicMock()
        mock_put_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_put_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.put = MagicMock(return_value=mock_put_context)
        
        from vasttamsclient.api.segments import upload_to_storage
        result = await upload_to_storage(client, presigned_url, data=data)
        
        assert result is True
        client._session.put.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_to_storage_with_file(self, client, tmp_path):
        """Test uploading file to storage."""
        presigned_url = "https://s3.example.com/upload"
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test file content")
        
        mock_response = AsyncMock()
        mock_response.status = 201
        
        mock_put_context = MagicMock()
        mock_put_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_put_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.put = MagicMock(return_value=mock_put_context)
        
        from vasttamsclient.api.segments import upload_to_storage
        result = await upload_to_storage(client, presigned_url, file_path=str(test_file))
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_upload_to_storage_file_not_found(self, client):
        """Test uploading non-existent file."""
        presigned_url = "https://s3.example.com/upload"
        
        from vasttamsclient.api.segments import upload_to_storage
        with pytest.raises(TAMSAPIError) as exc_info:
            await upload_to_storage(client, presigned_url, file_path="/nonexistent/file")
        
        assert "File not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_upload_to_storage_no_data_or_file(self, client):
        """Test uploading without data or file."""
        presigned_url = "https://s3.example.com/upload"
        
        from vasttamsclient.api.segments import upload_to_storage
        with pytest.raises(ValueError) as exc_info:
            await upload_to_storage(client, presigned_url)
        
        assert "Either data or file_path must be provided" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_upload_to_storage_error(self, client):
        """Test uploading with error."""
        presigned_url = "https://s3.example.com/upload"
        data = b"test data"
        
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Upload failed")
        
        mock_put_context = MagicMock()
        mock_put_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_put_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.put = MagicMock(return_value=mock_put_context)
        
        from vasttamsclient.api.segments import upload_to_storage
        with pytest.raises(TAMSAPIError) as exc_info:
            await upload_to_storage(client, presigned_url, data=data)
        
        assert "Failed to upload to storage" in str(exc_info.value)


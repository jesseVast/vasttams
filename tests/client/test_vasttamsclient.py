import pytest
import asyncio
from unittest.mock import Mock, patch
from vasttamsclient.client import TAMSClient
from vasttamsclient.exceptions import TAMSClientError


class TestTAMSClient:
    """Test TAMS client async/sync context handling"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TAMSClient("https://api.example.com", "testuser", "testpass")
        self.mock_response = Mock()
        self.mock_response.json.return_value = {"status": "success"}
        self.mock_response.raise_for_status.return_value = None
    
    @pytest.mark.asyncio
    @patch.object(TAMSClient, '_request')
    @patch.object(TAMSClient, '_get_headers')
    async def test_update_object_vector_async_success(self, mock_get_headers, mock_request):
        """Test async version in async context"""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"status": "success"})  # json() is sync, not async
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test-token"}
        
        result = await self.client.update_object_vector_async("test-obj", [1, 2, 3])
        assert result == {"status": "success"}
        mock_request.assert_called_once()
    
    @patch.object(TAMSClient, '_request')
    @patch.object(TAMSClient, '_get_headers')
    def test_update_object_vector_sync_success(self, mock_get_headers, mock_request):
        """Test sync version in sync context"""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"status": "success"})  # json() is sync, not async
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test-token"}
        
        result = self.client.update_object_vector("test-obj", [1, 2, 3])
        assert result == {"status": "success"}
        # Note: sync wrapper may not call _request directly if already in async context
    
    @pytest.mark.asyncio
    @patch.object(TAMSClient, '_request')
    @patch.object(TAMSClient, '_get_headers')
    async def test_update_object_vector_auto_detection_async(self, mock_get_headers, mock_request):
        """Test that sync wrapper always returns result even in async environment"""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"status": "success"})  # json() is sync, not async
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test-token"}

        # Sync wrapper should always return the actual result, not a coroutine
        result = self.client.update_object_vector("test-obj", [1, 2, 3])
        # Should be the actual result, not a coroutine
        assert not asyncio.iscoroutine(result)
        assert result == {"status": "success"}
    
    @patch.object(TAMSClient, '_request')
    @patch.object(TAMSClient, '_get_headers')
    def test_update_object_vector_auto_detection_sync(self, mock_get_headers, mock_request):
        """Test automatic context detection in sync environment"""
        from unittest.mock import AsyncMock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"status": "success"})  # json() is sync, not async
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test-token"}
        
        # This should work synchronously
        result = self.client.update_object_vector("test-obj", [1, 2, 3])
        assert result == {"status": "success"}
    
    @pytest.mark.asyncio
    @patch.object(TAMSClient, '_request')
    @patch.object(TAMSClient, '_get_headers')
    async def test_update_object_vector_async_error(self, mock_get_headers, mock_request):
        """Test async error handling"""
        from unittest.mock import AsyncMock
        from vasttamsclient.exceptions import TAMSAPIError
        mock_request.side_effect = TAMSAPIError("Async error", 500, "Error details")
        mock_get_headers.return_value = {"Authorization": "Bearer test-token"}
        
        with pytest.raises(TAMSClientError):
            await self.client.update_object_vector_async("test-obj", [1, 2, 3])
    
    @patch.object(TAMSClient, '_request')
    @patch.object(TAMSClient, '_get_headers')
    def test_update_object_vector_sync_error(self, mock_get_headers, mock_request):
        """Test sync error handling"""
        from unittest.mock import AsyncMock
        from vasttamsclient.exceptions import TAMSAPIError
        mock_request.side_effect = TAMSAPIError("Sync error", 500, "Error details")
        mock_get_headers.return_value = {"Authorization": "Bearer test-token"}
        
        with pytest.raises(TAMSClientError):
            self.client.update_object_vector("test-obj", [1, 2, 3])
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
    
    @patch('vasttamsclient.client.aiohttp.ClientSession.put')
    def test_update_object_vector_async_success(self, mock_put):
        """Test async version in async context"""
        mock_put.return_value.__aenter__.return_value = self.mock_response
        
        async def test_async():
            result = await self.client.update_object_vector_async("test-obj", {"vector": [1, 2, 3]})
            assert result == {"status": "success"}
            mock_put.assert_called_once()
        
        asyncio.run(test_async())
    
    @patch('vasttamsclient.client.requests.Session.put')
    def test_update_object_vector_sync_success(self, mock_put):
        """Test sync version in sync context"""
        mock_put.return_value = self.mock_response
        
        result = self.client.update_object_vector("test-obj", {"vector": [1, 2, 3]})
        assert result == {"status": "success"}
        mock_put.assert_called_once()
    
    @patch('vasttamsclient.client.aiohttp.ClientSession.put')
    def test_update_object_vector_auto_detection_async(self, mock_put):
        """Test that sync wrapper always returns result even in async environment"""
        mock_put.return_value.__aenter__.return_value = self.mock_response

        async def test_async_context():
            # Sync wrapper should always return the actual result, not a coroutine
            result = self.client.update_object_vector("test-obj", {"vector": [1, 2, 3]})
            # Should be the actual result, not a coroutine
            assert not asyncio.iscoroutine(result)
            assert result == {"status": "success"}

        asyncio.run(test_async_context())
    
    @patch('vasttamsclient.client.requests.Session.put')
    def test_update_object_vector_auto_detection_sync(self, mock_put):
        """Test automatic context detection in sync environment"""
        mock_put.return_value = self.mock_response
        
        # This should work synchronously
        result = self.client.update_object_vector("test-obj", {"vector": [1, 2, 3]})
        assert result == {"status": "success"}
        mock_put.assert_called_once()
    
    @patch('vasttamsclient.client.aiohttp.ClientSession.put')
    def test_update_object_vector_async_error(self, mock_put):
        """Test async error handling"""
        mock_put.return_value.__aenter__.side_effect = Exception("Async error")
        
        async def test_async_error():
            with pytest.raises(TAMSClientError):
                await self.client.update_object_vector_async("test-obj", {"vector": [1, 2, 3]})
        
        asyncio.run(test_async_error())
    
    @patch('vasttamsclient.client.requests.Session.put')
    def test_update_object_vector_sync_error(self, mock_put):
        """Test sync error handling"""
        mock_put.side_effect = Exception("Sync error")
        
        with pytest.raises(TAMSClientError):
            self.client.update_object_vector("test-obj", {"vector": [1, 2, 3]})
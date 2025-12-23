import pytest
import asyncio
from unittest.mock import Mock, patch
from vasttamsclient.client import VattamsClient
from vasttamsclient.exceptions import VattamsClientError


class TestVattamsClient:
    """Test Vattams client async/sync context handling"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = VattamsClient("https://api.example.com", "test-api-key")
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
        """Test automatic context detection in async environment"""
        mock_put.return_value.__aenter__.return_value = self.mock_response
        
        async def test_async_context():
            # This should return a coroutine in async context
            result = self.client.update_object_vector("test-obj", {"vector": [1, 2, 3]})
            # Should be a coroutine, not the actual result
            assert asyncio.iscoroutine(result)
            # Now await it to get the actual result
            final_result = await result
            assert final_result == {"status": "success"}
        
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
            with pytest.raises(VattamsClientError):
                await self.client.update_object_vector_async("test-obj", {"vector": [1, 2, 3]})
        
        asyncio.run(test_async_error())
    
    @patch('vasttamsclient.client.requests.Session.put')
    def test_update_object_vector_sync_error(self, mock_put):
        """Test sync error handling"""
        mock_put.side_effect = Exception("Sync error")
        
        with pytest.raises(VattamsClientError):
            self.client.update_object_vector("test-obj", {"vector": [1, 2, 3]})
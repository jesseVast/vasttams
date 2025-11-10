"""
Tests for deletion request API and domain objects
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from vasttamsclient.api.deletion_requests import get_deletion_requests, get_deletion_request
from vasttamsclient.domain.deletion_request import TAMSDeletionRequest
from vasttamsclient.exceptions import TAMSAPIError


class TestDeletionRequestAPI:
    """Test deletion request API functions"""
    
    @pytest.mark.asyncio
    async def test_get_deletion_requests(self, client):
        """Test getting all deletion requests."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {"id": "req1", "flow_id": "flow1", "status": "created"},
            {"id": "req2", "flow_id": "flow2", "status": "started"}
        ])
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        result = await get_deletion_requests(client)
        
        assert len(result) == 2
        assert result[0]["id"] == "req1"
        assert result[1]["id"] == "req2"
        client._session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_deletion_request(self, client):
        """Test getting a specific deletion request."""
        request_id = "req-123"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": request_id,
            "flow_id": "flow-123",
            "status": "started",
            "timerange_to_delete": {"value": "[0:0_100:0)"}
        })
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        result = await get_deletion_request(client, request_id)
        
        assert result is not None
        assert result["id"] == request_id
        assert result["status"] == "started"
        client._session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_deletion_request_not_found(self, client):
        """Test getting a non-existent deletion request."""
        request_id = "req-123"
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_get_context = MagicMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        
        client._session.get = MagicMock(return_value=mock_get_context)
        
        result = await get_deletion_request(client, request_id)
        
        assert result is None
        client._session.get.assert_called_once()


class TestTAMSDeletionRequest:
    """Test TAMSDeletionRequest domain object"""
    
    @pytest.mark.asyncio
    async def test_deletion_request_properties(self, client):
        """Test deletion request properties."""
        request_data = {
            "id": "req-123",
            "flow_id": "flow-123",
            "status": "started",
            "timerange_to_delete": {"value": "[0:0_100:0)"},
            "timerange_remaining": {"value": "[50:0_100:0)"},
            "delete_flow": False,
            "created": "2024-01-01T00:00:00Z",
            "updated": "2024-01-01T00:01:00Z",
            "error": None
        }
        
        request = TAMSDeletionRequest(client, "req-123", request_data)
        
        assert request.id == "req-123"
        assert request.flow_id == "flow-123"
        assert request.status == "started"
        assert request.timerange_to_delete == {"value": "[0:0_100:0)"}
        assert request.timerange_remaining == {"value": "[50:0_100:0)"}
        assert request.delete_flow is False
        assert request.is_in_progress() is True
        assert request.is_done() is False
        assert request.is_error() is False
    
    @pytest.mark.asyncio
    async def test_deletion_request_status_checks(self, client):
        """Test deletion request status check methods."""
        # Test done status
        request_done = TAMSDeletionRequest(client, "req-1", {
            "id": "req-1",
            "status": "done"
        })
        assert request_done.is_done() is True
        assert request_done.is_in_progress() is False
        
        # Test error status
        request_error = TAMSDeletionRequest(client, "req-2", {
            "id": "req-2",
            "status": "error",
            "error": {"message": "Deletion failed"}
        })
        assert request_error.is_error() is True
        assert request_error.error == {"message": "Deletion failed"}
        
        # Test in progress status
        request_started = TAMSDeletionRequest(client, "req-3", {
            "id": "req-3",
            "status": "started"
        })
        assert request_started.is_in_progress() is True
    
    @pytest.mark.asyncio
    async def test_deletion_request_refresh(self, client):
        """Test refreshing deletion request data."""
        request = TAMSDeletionRequest(client, "req-123", {
            "id": "req-123",
            "status": "created"
        })
        
        with patch('vasttamsclient.api.deletion_requests.get_deletion_request', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": "req-123",
                "status": "done",
                "flow_id": "flow-123"
            }
            
            await request.refresh()
            
            assert request.status == "done"
            mock_get.assert_called_once_with(client, "req-123")


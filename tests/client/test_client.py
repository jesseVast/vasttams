"""
Tests for TAMSClient.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSAuthenticationError, TAMSAPIError, TAMSConnectionError
from vasttamsclient.domain.source import TAMSSource
from vasttamsclient.domain.flow import TAMSFlow


class TestTAMSClientInit:
    """Tests for TAMSClient initialization."""
    
    def test_init(self, client):
        """Test client initialization."""
        assert client.server_url == "http://localhost:8000"
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client.timeout == 30
        assert client.verify_ssl is True
        assert client._closed is False
    
    def test_init_strips_trailing_slash(self):
        """Test that server_url trailing slash is stripped."""
        with patch('vasttamsclient.client.TokenManager'):
            with patch('vasttamsclient.client.HttpxTransport'):
                client = TAMSClient("http://localhost:8000/", "user", "pass")
                assert client.server_url == "http://localhost:8000"
    
    def test_init_custom_timeout(self):
        """Test client with custom timeout."""
        with patch('vasttamsclient.client.TokenManager'):
            with patch('vasttamsclient.client.HttpxTransport'):
                client = TAMSClient("http://localhost:8000", "user", "pass", timeout=60)
                assert client.timeout == 60
    
    def test_init_custom_verify_ssl(self):
        """Test client with custom SSL verification."""
        with patch('vasttamsclient.client.TokenManager'):
            with patch('vasttamsclient.client.HttpxTransport'):
                client = TAMSClient("http://localhost:8000", "user", "pass", verify_ssl=False)
                assert client.verify_ssl is False


class TestTAMSClientContextManager:
    """Tests for TAMSClient as async context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager_enter(self, client, mock_transport):
        """Test entering context manager."""
        async with client:
            assert client._transport is not None
            assert not client._closed
    
    @pytest.mark.asyncio
    async def test_context_manager_exit(self, client, mock_transport):
        """Test exiting context manager."""
        async with client:
            pass
        mock_transport.close.assert_called_once()
        assert client._closed


class TestTAMSClientSession:
    """Tests for TAMSClient header and close behaviour."""
    
    @pytest.mark.asyncio
    async def test_get_headers(self, client, mock_token_manager, mock_token):
        """Test getting headers with authentication token."""
        headers = await client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {mock_token}"
        assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_close(self, client, mock_transport):
        """Test closing client."""
        await client.close()
        mock_transport.close.assert_called_once()
        assert client._closed


class TestTAMSClientRequest:
    """Tests for TAMSClient HTTP requests."""
    
    @pytest.mark.asyncio
    async def test_request_success(self, client, mock_transport, mock_response):
        """Test successful HTTP request."""
        mock_transport.request.return_value = mock_response
        response = await client._request("GET", "http://localhost:8000/test")
        assert response == mock_response
        mock_transport.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_401_refreshes_token(self, client, mock_transport, mock_token_manager):
        """Test that 401 response triggers token refresh."""
        first_response = MagicMock()
        first_response.status_code = 401
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.json = MagicMock(return_value={"success": True})
        mock_transport.request.side_effect = [first_response, second_response]

        response = await client._request("GET", "http://localhost:8000/test")
        assert response.status_code == 200
        mock_token_manager.refresh_token.assert_called_once()
        assert mock_transport.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_request_401_after_refresh_raises_error(self, client, mock_transport, mock_token_manager):
        """Test that 401 after refresh raises authentication error."""
        response_401 = MagicMock()
        response_401.status_code = 401
        mock_transport.request.return_value = response_401

        with pytest.raises(TAMSAuthenticationError) as exc_info:
            await client._request("GET", "http://localhost:8000/test")
        assert "Authentication failed after token refresh" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_request_connection_error(self, client, mock_transport):
        """Test request with connection error."""
        mock_transport.request.side_effect = httpx.HTTPError("Connection failed")
        
        with pytest.raises(TAMSConnectionError) as exc_info:
            await client._request("GET", "http://localhost:8000/test")
        assert "Connection error" in str(exc_info.value)


class TestTAMSClientFactoryMethods:
    """Tests for TAMSClient factory methods."""
    
    def test_tams_source_factory(self, client):
        """Test TAMSSource factory method."""
        source = client.TAMSSource(
            format="urn:x-nmos:format:video",
            label="Test Source"
        )
        assert isinstance(source, TAMSSource)
        assert source._data["format"] == "urn:x-nmos:format:video"
        assert source._data["label"] == "Test Source"
        assert source._client == client
    
    def test_tams_flow_factory(self, client):
        """Test TAMSFlow factory method."""
        flow = client.TAMSFlow(
            source_id="source-123",
            format="urn:x-nmos:format:video",
            codec="video/h264",
            label="Test Flow"
        )
        assert isinstance(flow, TAMSFlow)
        assert flow._data["source_id"] == "source-123"
        assert flow._data["format"] == "urn:x-nmos:format:video"
        assert flow._data["codec"] == "video/h264"
        assert flow._data["label"] == "Test Flow"
        assert flow._client == client


class TestTAMSClientQueryMethods:
    """Tests for TAMSClient query methods."""
    
    @pytest.mark.asyncio
    async def test_get_source_success(self, client):
        """Test getting a source successfully."""
        source_data = {
            "id": "source-123",
            "format": "urn:x-nmos:format:video",
            "label": "Test Source"
        }
        
        with patch('vasttamsclient.api.sources.get_source', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = source_data
            source = await client.get_source("source-123")
            assert isinstance(source, TAMSSource)
            assert source.id == "source-123"
            assert source._data["label"] == "Test Source"
    
    @pytest.mark.asyncio
    async def test_get_source_not_found(self, client):
        """Test getting a non-existent source."""
        with patch('vasttamsclient.api.sources.get_source', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            source = await client.get_source("nonexistent")
            assert source is None
    
    @pytest.mark.asyncio
    async def test_get_flow_success(self, client):
        """Test getting a flow successfully."""
        flow_data = {
            "id": "flow-123",
            "source_id": "source-123",
            "format": "urn:x-nmos:format:video",
            "codec": "video/h264",
            "label": "Test Flow"
        }
        
        with patch('vasttamsclient.api.flows.get_flow', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = flow_data
            flow = await client.get_flow("flow-123")
            assert isinstance(flow, TAMSFlow)
            assert flow.id == "flow-123"
            # Flow data should be populated from the API response
            # When id is provided, flow_data is passed via **flow_data, so all fields should be in _data
            assert flow._data.get("source_id") == "source-123"
            assert flow._data.get("format") == "urn:x-nmos:format:video"
            assert flow._data.get("codec") == "video/h264"
            assert flow._data.get("label") == "Test Flow"
    
    @pytest.mark.asyncio
    async def test_list_sources(self, client):
        """Test listing sources."""
        sources_data = [
            {"id": "source-1", "format": "urn:x-nmos:format:video", "label": "Source 1"},
            {"id": "source-2", "format": "urn:x-nmos:format:video", "label": "Source 2"}
        ]
        
        with patch('vasttamsclient.api.sources.list_sources', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = sources_data
            sources = await client.list_sources()
            assert len(sources) == 2
            assert all(isinstance(s, TAMSSource) for s in sources)
            assert sources[0].id == "source-1"
            assert sources[1].id == "source-2"
    
    @pytest.mark.asyncio
    async def test_list_flows(self, client):
        """Test listing flows."""
        flows_data = [
            {"id": "flow-1", "source_id": "source-1", "format": "urn:x-nmos:format:video", "codec": "video/h264"},
            {"id": "flow-2", "source_id": "source-1", "format": "urn:x-nmos:format:video", "codec": "video/h264"}
        ]
        
        with patch('vasttamsclient.api.flows.list_flows', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = flows_data
            flows = await client.list_flows()
            assert len(flows) == 2
            assert all(isinstance(f, TAMSFlow) for f in flows)
            assert flows[0].id == "flow-1"
            assert flows[1].id == "flow-2"


class TestTAMSClientSyncWrappers:
    """Tests for TAMSClient synchronous wrappers."""
    
    def test_get_source_sync(self, client):
        """Test synchronous get_source wrapper."""
        with patch.object(client, 'get_source', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = TAMSSource(client, id="source-123", format="urn:x-nmos:format:video")
            result = client.get_source_sync("source-123")
            assert isinstance(result, TAMSSource)
            mock_get.assert_called_once_with("source-123")
    
    def test_list_sources_sync(self, client):
        """Test synchronous list_sources wrapper."""
        with patch.object(client, 'list_sources', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                TAMSSource(client, id="source-1", format="urn:x-nmos:format:video")
            ]
            result = client.list_sources_sync()
            assert len(result) == 1
            mock_list.assert_called_once()


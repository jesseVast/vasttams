"""
Pytest configuration for client tests.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

# Add src/client to path for imports (if not already added)
client_path = Path(__file__).parent.parent.parent / "src" / "client"
if str(client_path) not in sys.path:
    sys.path.insert(0, str(client_path))

from vasttamsclient import TAMSClient
from vasttamsclient.auth import TokenManager
from vasttamsclient.transport import HttpxTransport
from vasttamsclient.exceptions import (
    TAMSClientError,
    TAMSAuthenticationError,
    TAMSAPIError,
    TAMSConnectionError
)


@pytest.fixture
def mock_token():
    """Mock authentication token."""
    return "mock-access-token-12345"


@pytest.fixture
def mock_token_manager(mock_token):
    """Mock TokenManager."""
    manager = MagicMock(spec=TokenManager)
    manager.get_token = AsyncMock(return_value=mock_token)
    manager.refresh_token = AsyncMock(return_value=mock_token)
    manager.login = AsyncMock(return_value=mock_token)
    manager.clear_token = MagicMock()
    return manager


@pytest.fixture
def mock_transport():
    """Mock HttpxTransport."""
    transport = AsyncMock(spec=HttpxTransport)
    transport.close = AsyncMock()
    return transport


@pytest.fixture
def mock_session(mock_transport):
    """Alias for legacy tests expecting mock_session."""
    return mock_transport


@pytest.fixture
def mock_response():
    """Mock httpx Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json = MagicMock(return_value={"id": "test-id", "label": "Test"})
    response.text = ""
    response.headers = {}
    return response


@pytest.fixture
def client(mock_token_manager, mock_transport):
    """Create a TAMSClient instance with mocked dependencies."""
    with patch('vasttamsclient.client.TokenManager', return_value=mock_token_manager):
        with patch('vasttamsclient.client.HttpxTransport', return_value=mock_transport):
            client = TAMSClient(
                server_url="http://localhost:8000",
                username="testuser",
                password="testpass",
                timeout=30,
                transport=mock_transport
            )
            client._transport = mock_transport
            client._token_manager = mock_token_manager
            return client


@pytest.fixture
def server_url():
    """Test server URL."""
    return "http://localhost:8000"


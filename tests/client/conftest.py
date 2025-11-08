"""
Pytest configuration for client tests.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

# Add src/client to path for imports (if not already added)
client_path = Path(__file__).parent.parent.parent / "src" / "client"
if str(client_path) not in sys.path:
    sys.path.insert(0, str(client_path))

from vasttamsclient import TAMSClient
from vasttamsclient.auth import TokenManager
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
def mock_session():
    """Mock aiohttp ClientSession."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.closed = False
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_response():
    """Mock aiohttp ClientResponse."""
    response = AsyncMock(spec=aiohttp.ClientResponse)
    response.status = 200
    response.json = AsyncMock(return_value={"id": "test-id", "label": "Test"})
    response.text = AsyncMock(return_value="")
    response.headers = {}
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response


@pytest.fixture
def client(mock_token_manager, mock_session):
    """Create a TAMSClient instance with mocked dependencies."""
    with patch('vasttamsclient.client.TokenManager', return_value=mock_token_manager):
        with patch('vasttamsclient.client.aiohttp.ClientSession', return_value=mock_session):
            client = TAMSClient(
                server_url="http://localhost:8000",
                username="testuser",
                password="testpass"
            )
            client._session = mock_session
            client._token_manager = mock_token_manager
            return client


@pytest.fixture
def server_url():
    """Test server URL."""
    return "http://localhost:8000"


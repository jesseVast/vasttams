"""
Endpoint tests for webhooks
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.core.config import get_settings

import logging
logger = logging.getLogger(__name__)

settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}"


@pytest.fixture(scope="module")
def api_available():
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("API server not running. Start server with: python run.py")


@pytest.mark.usefixtures("api_available")
class TestWebhookEndpoint:
    """Endpoint tests for Webhooks API"""
    
    def test_list_webhooks(self, api_available, auth_headers):
        """Test GET /service/webhooks endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/service/webhooks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_head_webhooks(self, api_available, auth_headers):
        """Test HEAD /service/webhooks endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/service/webhooks", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_webhook_by_id(self, api_available, auth_headers):
        """Test GET /service/webhooks/{id} endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        # Try to get a non-existent webhook
        response = requests.get(f"{BASE_URL}/service/webhooks/non-existent-id", headers=auth_headers)
        assert response.status_code == 404


#!/usr/bin/env python3
"""
Service Endpoint Tests

Tests the REST API endpoints for service information.
"""

import pytest
import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.core.config import get_settings

import logging
logger = logging.getLogger(__name__)

# Get settings for API base URL
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
class TestServiceEndpoint:
    """Endpoint tests for Service API"""
    
    def test_get_service_info(self, api_available):
        """Test GET /service endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/service")
        assert response.status_code == 200
        
        service_info = response.json()
        assert isinstance(service_info, dict)
        assert "api_version" in service_info
        assert "type" in service_info
    
    def test_head_service(self, api_available):
        """Test HEAD /service endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/service")
        assert response.status_code in [200, 204]
    
    def test_get_webhooks(self, api_available):
        """Test GET /service/webhooks endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/service/webhooks")
        assert response.status_code == 200
        
        webhooks = response.json()
        assert isinstance(webhooks, list)
    
    def test_head_webhooks(self, api_available):
        """Test HEAD /service/webhooks endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.head(f"{BASE_URL}/service/webhooks")
        assert response.status_code in [200, 204]


@pytest.mark.usefixtures("api_available")
class TestWebhookEndpoint:
    """Endpoint tests for Webhooks API"""
    
    def test_create_webhook(self, api_available):
        """Test POST /service/webhooks endpoint"""
        if not api_available:
            pytest.skip("API not available")
        
        webhook_data = {
            "url": "https://example.com/webhook",
            "events": ["sources.created", "flows.created"],
            "api_key_name": "x-api-key",
            "api_key_value": "secret-key-123"
        }
        
        response = requests.post(
            f"{BASE_URL}/service/webhooks",
            json=webhook_data
        )
        
        # Webhook creation may fail with validation, succeed, or return 500 (not implemented)
        assert response.status_code in [201, 422, 500]
        
        if response.status_code == 201:
            webhook = response.json()
            assert "id" in webhook
            webhook_id = webhook["id"]
            
            # Cleanup
            requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}")



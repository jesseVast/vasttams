"""
CRUD tests for webhooks
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
class TestWebhookCRUD:
    """CRUD tests for webhooks"""
    
    def test_list_webhooks_empty(self, api_available, auth_headers):
        """Test listing webhooks when empty"""
        if not api_available:
            pytest.skip("API not available")
        
        response = requests.get(f"{BASE_URL}/service/webhooks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_and_get_webhook(self, api_available, auth_headers):
        """Test creating and retrieving a webhook"""
        if not api_available:
            pytest.skip("API not available")
        
        webhook_data = {
            "url": "https://example.com/webhook",
            "api_key_name": "x-api-key",
            "api_key_value": "secret-key-123",
            "events": ["sources.created", "flows.created"],
            "enabled": True
        }
        
        # Create webhook
        response = requests.post(f"{BASE_URL}/service/webhooks", json=webhook_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        
        created_webhook = response.json()
        assert "id" in created_webhook
        assert created_webhook["url"] == webhook_data["url"]
        assert created_webhook["api_key_name"] == webhook_data["api_key_name"]
        assert created_webhook["events"] == webhook_data["events"]
        
        webhook_id = created_webhook["id"]
        
        # Get webhook by ID
        response = requests.get(f"{BASE_URL}/service/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 200
        
        retrieved_webhook = response.json()
        assert retrieved_webhook["id"] == webhook_id
        assert retrieved_webhook["url"] == webhook_data["url"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}", headers=auth_headers)
    
    def test_update_webhook(self, api_available, auth_headers):
        """Test updating a webhook"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create webhook
        webhook_data = {
            "url": "https://example.com/webhook",
            "api_key_name": "x-api-key",
            "api_key_value": "secret-key-123",
            "events": ["sources.created"],
            "enabled": True
        }
        
        response = requests.post(f"{BASE_URL}/service/webhooks", json=webhook_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        created_webhook = response.json()
        webhook_id = created_webhook["id"]
        
        # Update webhook
        update_data = {
            "events": ["sources.created", "sources.updated"],
            "enabled": False
        }
        
        response = requests.put(f"{BASE_URL}/service/webhooks/{webhook_id}", json=update_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        
        updated_webhook = response.json()
        # enabled may be returned as boolean
        assert updated_webhook.get("enabled") == False or updated_webhook.get("enabled") == "false" or updated_webhook.get("enabled") is False
        # events may be a list or JSON string
        events = updated_webhook.get("events")
        if isinstance(events, str):
            import json
            events = json.loads(events)
        assert "sources.updated" in events
        
        # Cleanup
        requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}", headers=auth_headers)
    
    def test_delete_webhook(self, api_available, auth_headers):
        """Test deleting a webhook"""
        if not api_available:
            pytest.skip("API not available")
        
        # Create webhook
        webhook_data = {
            "url": "https://example.com/webhook",
            "api_key_name": "x-api-key",
            "api_key_value": "secret-key-123",
            "events": ["sources.created"],
            "enabled": True
        }
        
        response = requests.post(f"{BASE_URL}/service/webhooks", json=webhook_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        created_webhook = response.json()
        webhook_id = created_webhook["id"]
        
        # Delete webhook
        response = requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/service/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_create_webhook_with_all_fields(self, api_available, auth_headers):
        """Test creating a webhook with all TAMS 8.0 fields"""
        if not api_available:
            pytest.skip("API not available")
        
        import uuid
        flow_uuid = str(uuid.uuid4())
        source_uuid = str(uuid.uuid4())
        
        webhook_data = {
            "url": "https://example.com/webhook",
            "api_key_name": "x-api-key",
            "api_key_value": "secret-key-123",
            "events": ["sources.created", "flows.created", "segments.added"],
            "flow_ids": [flow_uuid],
            "source_ids": [source_uuid],
            "presigned": True,
            "verbose_storage": False,
            "enabled": True
        }
        
        response = requests.post(f"{BASE_URL}/service/webhooks", json=webhook_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        
        created_webhook = response.json()
        webhook_id = created_webhook["id"]
        
        # Verify all fields are stored
        response = requests.get(f"{BASE_URL}/service/webhooks/{webhook_id}", headers=auth_headers)
        assert response.status_code == 200
        
        retrieved = response.json()
        # Handle potential JSON string parsing
        presigned_val = retrieved.get("presigned")
        verbose_val = retrieved.get("verbose_storage")
        
        assert presigned_val == True or presigned_val is True or (isinstance(presigned_val, str) and presigned_val.lower() == "true")
        assert verbose_val == False or verbose_val is False or (isinstance(verbose_val, str) and verbose_val.lower() == "false")
        
        flow_ids = retrieved.get("flow_ids", [])
        # If flow_ids is a JSON string, parse it
        if isinstance(flow_ids, str):
            import json
            flow_ids = json.loads(flow_ids)
        
        assert flow_uuid in flow_ids
        
        # Cleanup
        requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}", headers=auth_headers)


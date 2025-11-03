#!/usr/bin/env python3
"""
Register a webhook for all events pointing to the test server
"""

import sys
import requests
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Add tests to path to use conftest helpers
tests_path = Path(__file__).parent
sys.path.insert(0, str(tests_path))

from vasttams.core.config import get_settings

settings = get_settings()
# Use localhost instead of 0.0.0.0 for connections
BASE_URL = f"http://localhost:{settings.port}"
WEBHOOK_SERVER_URL = "http://localhost:8080"

def get_auth_headers():
    """Get authentication headers"""
    try:
        base_url = f"http://localhost:{settings.port}"
        response = requests.post(
            f"{base_url}/auth/login",
            json={"username": "admin", "password": "vastdata"},
            timeout=5
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"   Login error: {e}")
        pass
    return {}

def main():
    # Get auth headers
    print("🔐 Getting authentication...")
    headers = get_auth_headers()
    
    if not headers or "Authorization" not in headers:
        print("❌ Failed to get authentication headers")
        print("   Make sure the TAMS API server is running on port 8000")
        return 1
    
    print("✅ Authentication successful")
    
    # All available events per TAMS 8.0 spec
    all_events = [
        "flows/created",
        "flows/updated",
        "flows/deleted",
        "flows/segments_added",
        "flows/segments_deleted",
        "sources/created",
        "sources/updated",
        "sources/deleted"
    ]
    
    # Register webhook
    print(f"\n📝 Registering webhook for all events to {WEBHOOK_SERVER_URL}...")
    webhook_data = {
        "url": WEBHOOK_SERVER_URL,
        "api_key_name": "x-api-key",
        "api_key_value": "test-webhook-key-123",
        "events": all_events
    }
    
    response = requests.post(
        f"{BASE_URL}/service/webhooks",
        json=webhook_data,
        headers=headers,
        timeout=15
    )
    
    if response.status_code in [200, 201]:
        webhook = response.json()
        print(f"✅ Webhook registered successfully!")
        print(f"   ID: {webhook.get('id')}")
        print(f"   URL: {webhook.get('url')}")
        print(f"   Events: {len(webhook.get('events', []))} events")
        print(f"\n📋 Registered events:")
        for event in webhook.get('events', []):
            print(f"   - {event}")
        return 0
    else:
        print(f"❌ Failed to register webhook: {response.status_code}")
        print(f"   Response: {response.text}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

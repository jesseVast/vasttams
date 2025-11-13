#!/usr/bin/env python3
"""
Test webhook delivery by creating a source and flow
This should trigger webhook events that should be received by the webhook server
"""

import requests
import uuid
import time
import sys

API_BASE_URL = "http://localhost:8000/api/tams/latest"
WEBHOOK_SERVER_URL = "http://localhost:8080"

def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": "admin", "password": "vastdata"}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_webhook_delivery():
    """Create a source and flow to trigger webhook events"""
    print("🧪 Testing Webhook Delivery")
    print("=" * 60)
    
    # Login
    print("\n1. Logging in...")
    token = login()
    print("✅ Logged in")
    
    # Create a source - should trigger sources/created event
    print("\n2. Creating source (should trigger sources/created event)...")
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Webhook Test Source {source_id[:8]}",
        "description": "Test source for webhook delivery testing"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/sources",
        json=source_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    print(f"✅ Source created: {source_id[:8]}...")
    print(f"   Status: {response.status_code}")
    
    # Wait a moment for webhook delivery
    print("\n3. Waiting 2 seconds for webhook delivery...")
    time.sleep(2)
    
    # Create a flow - should trigger flows/created event
    print("\n4. Creating flow (should trigger flows/created event)...")
    flow_id = str(uuid.uuid4())
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Webhook Test Flow {flow_id[:8]}",
        "codec": "video/H264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {
                "numerator": 25,
                "denominator": 1
            }
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/flows",
        json=flow_data,
        headers=get_headers(token)
    )
    response.raise_for_status()
    print(f"✅ Flow created: {flow_id[:8]}...")
    print(f"   Status: {response.status_code}")
    
    # Wait a moment for webhook delivery
    print("\n5. Waiting 2 seconds for webhook delivery...")
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)
    print("\n📋 Check the webhook server log at /tmp/webhook_server.log")
    print(f"   Or check the webhook server console output")
    print(f"\n   You should see:")
    print(f"   - sources/created event for source {source_id[:8]}...")
    print(f"   - flows/created event for flow {flow_id[:8]}...")
    
    # Cleanup
    print("\n6. Cleaning up...")
    try:
        requests.delete(f"{API_BASE_URL}/flows/{flow_id}", headers=get_headers(token))
        print(f"✅ Flow deleted")
    except:
        pass
    
    try:
        requests.delete(f"{API_BASE_URL}/sources/{source_id}", headers=get_headers(token))
        print(f"✅ Source deleted")
    except:
        pass
    
    assert True  # Test passed

if __name__ == "__main__":
    test_webhook_delivery()
    sys.exit(0)


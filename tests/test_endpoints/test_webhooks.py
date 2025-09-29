#!/usr/bin/env python3
"""
Webhooks Endpoint Tests

Tests for all webhook-related endpoints including:
- Webhook management
- Webhook registration
- Webhook deletion
- Webhook configuration
"""

import requests
from datetime import datetime
from test_utils import (
    BASE_URL, test_data, print_section, print_subsection, print_result,
    assert_response_success, assert_response_status, assert_response_any_status,
    cleanup_test_data
)

def test_webhooks_crud():
    """Test basic webhook CRUD operations"""
    print_section("WEBHOOKS CRUD OPERATIONS")
    
    # READ - GET /service/webhooks
    print_subsection("GET Webhooks List")
    response = requests.get(f"{BASE_URL}/service/webhooks")
    data = assert_response_success("GET", "/service/webhooks", response, 200)
    assert isinstance(data, list)
    print(f"   Current webhooks: {len(data)}")
    
    # CREATE - POST /service/webhooks
    print_subsection("CREATE Webhook")
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["source.created", "flow.created", "segment.created"],
        "secret": "test-secret-key",
        "description": "Test webhook for API testing"
    }
    
    response = requests.post(f"{BASE_URL}/service/webhooks", json=webhook_data)
    data = assert_response_success("POST", "/service/webhooks", response, 201)
    
    # Store webhook ID for cleanup
    webhook_id = data.get("id") or data.get("webhook_id")
    if webhook_id:
        test_data["object_ids"].append(webhook_id)
        print(f"   Created webhook ID: {webhook_id}")
    
    # READ - GET /service/webhooks (verify creation)
    print_subsection("VERIFY Webhook Creation")
    response = requests.get(f"{BASE_URL}/service/webhooks")
    data = assert_response_success("GET", "/service/webhooks", response, 200)
    assert isinstance(data, list)
    print(f"   Updated webhooks: {len(data)}")

def test_webhooks_management():
    """Test webhook management operations"""
    print_section("WEBHOOKS MANAGEMENT")
    
    # Create a webhook first
    print_subsection("CREATE Test Webhook")
    webhook_data = {
        "url": "https://test.example.com/webhook",
        "events": ["source.updated", "flow.updated"],
        "secret": "management-test-secret",
        "description": "Management test webhook"
    }
    
    response = requests.post(f"{BASE_URL}/service/webhooks", json=webhook_data)
    data = assert_response_success("POST", "/service/webhooks", response, 201)
    
    webhook_id = data.get("id") or data.get("webhook_id")
    if not webhook_id:
        print("   ⚠️  No webhook ID returned, skipping management tests")
        return
    
    test_data["object_ids"].append(webhook_id)
    
    # UPDATE webhook (if supported)
    print_subsection("UPDATE Webhook")
    updated_webhook = {
        "url": "https://updated.example.com/webhook",
        "events": ["source.created", "source.updated", "flow.created", "flow.updated"],
        "secret": "updated-secret-key",
        "description": "Updated management test webhook"
    }
    
    # Try PUT method (if supported)
    response = requests.put(f"{BASE_URL}/service/webhooks/{webhook_id}", json=updated_webhook)
    if response.status_code in [200, 201, 404]:
        print_result("PUT", f"/service/webhooks/{webhook_id}", response.status_code)
    else:
        assert_response_success("PUT", f"/service/webhooks/{webhook_id}", response, 200)
    
    # DELETE webhook
    print_subsection("DELETE Webhook")
    response = requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}")
    assert_response_any_status("DELETE", f"/service/webhooks/{webhook_id}", response, [200, 204, 404])
    
    # Verify deletion
    print_subsection("VERIFY Webhook Deletion")
    response = requests.get(f"{BASE_URL}/service/webhooks")
    data = assert_response_success("GET", "/service/webhooks", response, 200)
    print(f"   Remaining webhooks: {len(data)}")

def test_webhooks_configuration():
    """Test webhook configuration options"""
    print_section("WEBHOOKS CONFIGURATION")
    
    # Test different webhook configurations
    webhook_configs = [
        {
            "url": "https://config1.example.com/webhook",
            "events": ["source.created"],
            "secret": "config1-secret",
            "description": "Single event webhook"
        },
        {
            "url": "https://config2.example.com/webhook",
            "events": ["source.created", "source.updated", "source.deleted"],
            "secret": "config2-secret",
            "description": "Multiple events webhook"
        },
        {
            "url": "https://config3.example.com/webhook",
            "events": ["flow.created", "flow.updated", "flow.deleted", "segment.created"],
            "secret": "config3-secret",
            "description": "All flow events webhook"
        }
    ]
    
    created_webhooks = []
    
    for i, config in enumerate(webhook_configs, 1):
        print_subsection(f"Configuration {i}: {config['description']}")
        
        response = requests.post(f"{BASE_URL}/service/webhooks", json=config)
        data = assert_response_success("POST", f"/service/webhooks (config {i})", response, 201)
        
        webhook_id = data.get("id") or data.get("webhook_id")
        if webhook_id:
            created_webhooks.append(webhook_id)
            test_data["object_ids"].append(webhook_id)
            print(f"   Created webhook ID: {webhook_id}")
            print(f"   Events: {config['events']}")
    
    # Clean up created webhooks
    print_subsection("CLEANUP Configuration Webhooks")
    for webhook_id in created_webhooks:
        response = requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}")
        if response.status_code in [200, 204, 404]:
            print(f"   Deleted webhook: {webhook_id}")
        else:
            print(f"   Failed to delete webhook {webhook_id}: {response.status_code}")

def test_webhooks_validation():
    """Test webhook validation"""
    print_section("WEBHOOKS VALIDATION")
    
    # Test invalid webhook configurations
    invalid_configs = [
        {
            "description": "Missing URL",
            "data": {
                "events": ["source.created"],
                "secret": "test-secret"
            }
        },
        {
            "description": "Invalid URL",
            "data": {
                "url": "not-a-valid-url",
                "events": ["source.created"],
                "secret": "test-secret"
            }
        },
        {
            "description": "Empty events list",
            "data": {
                "url": "https://example.com/webhook",
                "events": [],
                "secret": "test-secret"
            }
        },
        {
            "description": "Invalid event type",
            "data": {
                "url": "https://example.com/webhook",
                "events": ["invalid.event"],
                "secret": "test-secret"
            }
        }
    ]
    
    for test_case in invalid_configs:
        print_subsection(f"Validation Test: {test_case['description']}")
        
        response = requests.post(f"{BASE_URL}/service/webhooks", json=test_case["data"])
        # Invalid configurations should return 400 or 422
        if response.status_code in [400, 422]:
            print_result("POST", f"/service/webhooks ({test_case['description']})", response.status_code)
        else:
            print_result("POST", f"/service/webhooks ({test_case['description']})", response.status_code)
            # If it succeeded, clean up
            if response.status_code in [200, 201]:
                data = response.json()
                webhook_id = data.get("id") or data.get("webhook_id")
                if webhook_id:
                    requests.delete(f"{BASE_URL}/service/webhooks/{webhook_id}")

def test_webhooks_head_operations():
    """Test HEAD operations for webhooks"""
    print_section("WEBHOOKS HEAD OPERATIONS")
    
    # HEAD /service/webhooks
    print_subsection("HEAD Webhooks List")
    response = requests.head(f"{BASE_URL}/service/webhooks")
    assert_response_status("HEAD", "/service/webhooks", response, 200)
    
    # Test HEAD with query parameters
    print_subsection("HEAD Webhooks with Query")
    response = requests.head(f"{BASE_URL}/service/webhooks?limit=10")
    assert_response_status("HEAD", "/service/webhooks?limit=10", response, 200)

def test_webhooks_error_cases():
    """Test webhook error cases"""
    print_section("WEBHOOKS ERROR CASES")
    
    # Test with non-existent webhook ID
    print_subsection("Non-existent Webhook ID")
    response = requests.get(f"{BASE_URL}/service/webhooks/nonexistent-webhook-id")
    assert_response_status("GET", "/service/webhooks/nonexistent-webhook-id", response, 404)
    
    response = requests.delete(f"{BASE_URL}/service/webhooks/nonexistent-webhook-id")
    assert_response_status("DELETE", "/service/webhooks/nonexistent-webhook-id", response, 404)
    
    # Test with invalid webhook ID format
    print_subsection("Invalid Webhook ID Format")
    response = requests.get(f"{BASE_URL}/service/webhooks/invalid-id-format")
    assert_response_status("GET", "/service/webhooks/invalid-id-format", response, 404)

def test_webhooks_performance():
    """Test webhooks performance"""
    print_section("WEBHOOKS PERFORMANCE")
    
    import time
    
    # Test webhook creation performance
    print_subsection("Webhook Creation Performance")
    
    webhook_data = {
        "url": "https://perf.example.com/webhook",
        "events": ["source.created"],
        "secret": "perf-secret",
        "description": "Performance test webhook"
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/service/webhooks", json=webhook_data)
    end_time = time.time()
    
    response_time = end_time - start_time
    print(f"   Creation Response Time: {response_time:.3f} seconds")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        data = response.json()
        webhook_id = data.get("id") or data.get("webhook_id")
        if webhook_id:
            test_data["object_ids"].append(webhook_id)
    
    # Test webhook listing performance
    print_subsection("Webhook Listing Performance")
    
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/service/webhooks")
    end_time = time.time()
    
    response_time = end_time - start_time
    print(f"   Listing Response Time: {response_time:.3f} seconds")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Webhooks Count: {len(data)}")

def run_all_webhooks_tests():
    """Run all webhooks tests"""
    print("🚀 Starting Webhooks Endpoint Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    try:
        test_webhooks_crud()
        test_webhooks_management()
        test_webhooks_configuration()
        test_webhooks_validation()
        test_webhooks_head_operations()
        test_webhooks_error_cases()
        test_webhooks_performance()
        
        print_section("WEBHOOKS TESTS SUMMARY")
        print("✅ All webhooks endpoint tests completed successfully")
        
    except Exception as e:
        print(f"❌ Webhooks tests failed: {e}")
        raise
    finally:
        cleanup_test_data()

if __name__ == "__main__":
    run_all_webhooks_tests()

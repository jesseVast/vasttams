#!/usr/bin/env python3
"""
Test script for tag-based flow filtering functionality.
This script tests the new tag filtering feature implemented for flows.
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on different port
HEADERS = {"Content-Type": "application/json"}

def test_tag_filtering():
    """Test tag-based flow filtering functionality"""
    print("🧪 Testing Tag-based Flow Filtering")
    print("=" * 50)
    
    # Test 1: Create a flow with tags
    print("\n1. Creating a test flow with tags...")
    flow_data = {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "source_id": "550e8400-e29b-41d4-a716-446655440000",
        "format": "urn:x-nmos:format:video",
        "codec": "video/mp4",
        "label": "Test Video Flow",
        "frame_width": 1920,
        "frame_height": 1080,
        "frame_rate": "25/1",
        "tags": {
            "environment": "production",
            "priority": "high",
            "department": "engineering"
        }
    }
    
    try:
        # Create the flow
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=HEADERS)
        if response.status_code == 201:
            print("✅ Flow created successfully")
        else:
            print(f"❌ Failed to create flow: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating flow: {e}")
        return False
    
    # Test 2: Test tag value filtering
    print("\n2. Testing tag value filtering...")
    test_cases = [
        ("tag.environment=production", "flows with environment=production"),
        ("tag.priority=high", "flows with priority=high"),
        ("tag.department=engineering", "flows with department=engineering"),
        ("tag.nonexistent=value", "flows with nonexistent tag"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/flows?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f"✅ {description}: {count} flows found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    # Test 3: Test tag existence filtering
    print("\n3. Testing tag existence filtering...")
    test_cases = [
        ("tag_exists.environment=true", "flows that have environment tag"),
        ("tag_exists.priority=true", "flows that have priority tag"),
        ("tag_exists.nonexistent=true", "flows that have nonexistent tag"),
        ("tag_exists.nonexistent=false", "flows that don't have nonexistent tag"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/flows?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f"✅ {description}: {count} flows found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    # Test 4: Test combined filtering
    print("\n4. Testing combined filtering...")
    test_cases = [
        ("tag.environment=production&format=urn:x-nmos:format:video", "production video flows"),
        ("tag_exists.priority=true&frame_width=1920", "priority flows with 1920 width"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/flows?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f"✅ {description}: {count} flows found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    # Test 5: Test multiple tag filters
    print("\n5. Testing multiple tag filters...")
    try:
        response = requests.get(f"{BASE_URL}/flows?tag.environment=production&tag.priority=high", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('data', []))
            print(f"✅ Multiple tag filters: {count} flows found")
        else:
            print(f"❌ Multiple tag filters: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error testing multiple tag filters: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Tag filtering tests completed!")
    return True

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    try:
        # Delete the test flow
        response = requests.delete(f"{BASE_URL}/flows/550e8400-e29b-41d4-a716-446655440001")
        if response.status_code == 200:
            print("✅ Test flow deleted successfully")
        else:
            print(f"⚠️  Could not delete test flow: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Error cleaning up: {e}")

if __name__ == "__main__":
    print("TAMS Tag Filtering Test")
    print("Make sure the TAMS server is running on http://localhost:8000")
    print()
    
    try:
        success = test_tag_filtering()
        cleanup_test_data()
        
        if success:
            print("\n✅ All tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        cleanup_test_data()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        cleanup_test_data()
        sys.exit(1)

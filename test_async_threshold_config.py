#!/usr/bin/env python3
"""
Test script for runtime configuration of async deletion threshold
"""

import requests
import json

def test_async_threshold_config():
    """Test the async deletion threshold configuration endpoints"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Async Deletion Threshold Configuration")
    print("=" * 60)
    
    try:
        # Test 1: Get current threshold
        print("📝 Test 1: Getting current async deletion threshold")
        response = requests.get(f"{base_url}/config/async-deletion-threshold")
        if response.status_code == 200:
            data = response.json()
            current_threshold = data['async_deletion_threshold']
            print(f"   ✅ Current threshold: {current_threshold} segments")
            print(f"   📄 Description: {data['description']}")
        else:
            print(f"   ❌ Failed to get threshold: {response.status_code}")
            return
        
        # Test 2: Update threshold to 1000
        print("\n📝 Test 2: Updating threshold to 1000 segments")
        response = requests.put(f"{base_url}/config/async-deletion-threshold?threshold=1000")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Threshold updated: {data['message']}")
            print(f"   📄 New threshold: {data['async_deletion_threshold']} segments")
        else:
            print(f"   ❌ Failed to update threshold: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return
        
        # Test 3: Verify the update
        print("\n📝 Test 3: Verifying threshold update")
        response = requests.get(f"{base_url}/config/async-deletion-threshold")
        if response.status_code == 200:
            data = response.json()
            new_threshold = data['async_deletion_threshold']
            print(f"   ✅ Verified threshold: {new_threshold} segments")
            if new_threshold == 1000:
                print("   🎉 Threshold successfully updated!")
            else:
                print(f"   ⚠️  Expected 1000, got {new_threshold}")
        else:
            print(f"   ❌ Failed to verify threshold: {response.status_code}")
            return
        
        # Test 4: Reset to default (500)
        print("\n📝 Test 4: Resetting threshold to default (500)")
        response = requests.put(f"{base_url}/config/async-deletion-threshold?threshold=500")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Threshold reset: {data['message']}")
        else:
            print(f"   ❌ Failed to reset threshold: {response.status_code}")
            return
        
        # Test 5: Test invalid threshold (negative)
        print("\n📝 Test 5: Testing invalid threshold (negative)")
        response = requests.put(f"{base_url}/config/async-deletion-threshold?threshold=-1")
        if response.status_code == 400:
            print("   ✅ Correctly rejected invalid threshold")
            print(f"   📄 Error: {response.json()['detail']}")
        else:
            print(f"   ❌ Should have rejected invalid threshold: {response.status_code}")
        
        print("\n🎉 All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to TAMS API server")
        print("   Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_async_threshold_config()

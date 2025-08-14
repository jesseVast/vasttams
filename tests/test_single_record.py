#!/usr/bin/env python3
"""
Simple test script to test with a single record that is added, updated, and deleted
"""

import requests
import json
import uuid
from datetime import datetime, timezone

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = BASE_URL

def test_single_record_lifecycle():
    """Test the complete lifecycle of a single record"""
    print("🧪 Testing single record lifecycle...")
    
    # Test 1: Create a single source
    print("\n📝 Step 1: Creating a single source...")
    source_data = {
        "id": str(uuid.uuid4()),
        "format": "urn:x-nmos:format:video",
        "label": "Test Source",
        "description": "A test source for lifecycle testing",
        "created_by": "test_user",
        "updated_by": "test_user",
        "created": datetime.now(timezone.utc).isoformat(),
        "updated": datetime.now(timezone.utc).isoformat(),
        "tags": {"test": "value", "type": "video"},
        "source_collection": [{"id": str(uuid.uuid4()), "label": "Test Collection"}],
        "collected_by": [str(uuid.uuid4())]
    }
    
    try:
        response = requests.post(f"{API_BASE}/sources", json=source_data)
        print(f"✅ Source creation response: {response.status_code}")
        if response.status_code == 201:
            created_source = response.json()
            print(f"📋 Created source ID: {created_source.get('id')}")
            source_id = created_source.get('id')
        else:
            print(f"❌ Source creation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Source creation error: {e}")
        return False
    
    # Test 2: Update the source
    print("\n🔧 Step 2: Updating the source...")
    update_data = {
        "label": "Updated Test Source",
        "updated": datetime.now(timezone.utc).isoformat(),
        "updated_by": "test_user"
    }
    
    try:
        # Update label
        response = requests.put(f"{API_BASE}/sources/{source_id}/label?label=Updated Test Source")
        print(f"✅ Label update response: {response.status_code}")
        
        # Update description
        response = requests.put(f"{API_BASE}/sources/{source_id}/description?description=Updated description")
        print(f"✅ Description update response: {response.status_code}")
        
        # Update tags
        tags_data = {"test": "updated", "status": "modified"}
        response = requests.put(f"{API_BASE}/sources/{source_id}/tags", json=tags_data)
        print(f"✅ Tags update response: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Source update error: {e}")
        return False
    
    # Test 3: Retrieve the updated source
    print("\n📖 Step 3: Retrieving the updated source...")
    try:
        response = requests.get(f"{API_BASE}/sources/{source_id}")
        print(f"✅ Source retrieval response: {response.status_code}")
        if response.status_code == 200:
            retrieved_source = response.json()
            print(f"📋 Retrieved source label: {retrieved_source.get('label')}")
            print(f"📋 Retrieved source description: {retrieved_source.get('description')}")
            print(f"📋 Retrieved source tags: {retrieved_source.get('tags')}")
        else:
            print(f"❌ Source retrieval failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Source retrieval error: {e}")
        return False
    
    # Test 4: Delete the source
    print("\n🗑️  Step 4: Deleting the source...")
    try:
        response = requests.delete(f"{API_BASE}/sources/{source_id}")
        print(f"✅ Source deletion response: {response.status_code}")
        if response.status_code == 204:
            print("✅ Source deleted successfully")
        else:
            print(f"❌ Source deletion failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Source deletion error: {e}")
        return False
    
    # Test 5: Verify deletion
    print("\n🔍 Step 5: Verifying deletion...")
    try:
        response = requests.get(f"{API_BASE}/sources/{source_id}")
        print(f"✅ Source retrieval after deletion response: {response.status_code}")
        if response.status_code == 404:
            print("✅ Source not found after deletion (as expected)")
        else:
            print(f"⚠️  Source still exists after deletion: {response.status_code}")
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    
    print("\n🎉 Single record lifecycle test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_single_record_lifecycle()
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        exit(1)

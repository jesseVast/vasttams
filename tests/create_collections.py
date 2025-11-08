#!/usr/bin/env python3
"""
Create Flow and Source Collections from test_data_resources.json

This script reads test_data_resources.json and creates:
1. Flow collections - grouping flows together
2. Source collections - grouping sources together
"""

import requests
import json
from pathlib import Path
from typing import Dict, List

# Configuration
API_BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "vastdata"

# Path to test data resources
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESOURCES_FILE = PROJECT_ROOT / "test_data_resources.json"


def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_headers(token):
    """Get authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def create_flow_collection(token: str, flow_id: str, collection_items: List[Dict]) -> bool:
    """
    Create/update flow collection for a flow
    
    Args:
        token: Authentication token
        flow_id: Flow ID to set collection on
        collection_items: List of collection items with 'id' and 'role'
    
    Returns:
        True if successful
    """
    response = requests.put(
        f"{API_BASE_URL}/flows/{flow_id}/flow_collection",
        json=collection_items,
        headers=get_headers(token)
    )
    if response.status_code != 201:
        print(f"   ❌ Error {response.status_code}: {response.text}")
        response.raise_for_status()
    return True


def create_source_collection(token: str, source_id: str, collection_items: List[Dict]) -> bool:
    """
    Create/update source collection for a source
    
    Note: Source collections are typically read-only and inferred from flow collections,
    but we'll try to set them if the API supports it.
    
    Args:
        token: Authentication token
        source_id: Source ID to set collection on
        collection_items: List of collection items with 'id' and 'role'
    
    Returns:
        True if successful
    """
    # Check if source collection endpoint exists
    # Based on TAMS spec, source_collection might be read-only
    # Try PUT endpoint if it exists
    response = requests.put(
        f"{API_BASE_URL}/sources/{source_id}/source_collection",
        json=collection_items,
        headers=get_headers(token)
    )
    if response.status_code == 404:
        print(f"   ⚠️  Source collection endpoint not available (source_collection is read-only, inferred from flow collections)")
        return False
    response.raise_for_status()
    return True


def main():
    """Create collections from test_data_resources.json"""
    print("📦 Creating Flow and Source Collections\n")
    print("=" * 60)
    
    # Load test data resources
    if not RESOURCES_FILE.exists():
        print(f"❌ Error: {RESOURCES_FILE} not found")
        return
    
    with open(RESOURCES_FILE, 'r') as f:
        resources = json.load(f)
    
    sources = resources.get("sources", [])
    flows = resources.get("flows", [])
    
    print(f"📊 Found {len(sources)} sources and {len(flows)} flows")
    
    try:
        # 1. Login
        print("\n1. Logging in...")
        token = login()
        print("✅ Logged in successfully")
        
        # 2. Create Flow Collections
        print("\n2. Creating Flow Collections...")
        
        # Group flows by type (video vs audio)
        video_flows = [f for f in flows if "Video" in f.get("label", "")]
        audio_flows = [f for f in flows if "Audio" in f.get("label", "")]
        
        # Create a collection flow that collects all video flows
        if len(video_flows) >= 2:
            # Use the first video flow as the "collection" flow
            collection_flow_id = video_flows[0]["id"]
            collection_items = [
                {
                    "id": flow["id"],
                    "role": "video" if "Video" in flow.get("label", "") else "unknown"
                }
                for flow in video_flows[1:]  # Collect the other video flows
            ]
            
            print(f"   Creating flow collection on {collection_flow_id[:8]}...")
            print(f"   Collecting {len(collection_items)} flows:")
            for item in collection_items:
                print(f"      - {item['id'][:8]}... (role: {item['role']})")
            
            create_flow_collection(token, collection_flow_id, collection_items)
            print(f"   ✅ Flow collection created")
        
        # Create a multi-essence flow collection (video + audio)
        if len(video_flows) >= 1 and len(audio_flows) >= 1:
            # Use the first video flow as the collection flow
            collection_flow_id = video_flows[0]["id"]
            collection_items = []
            
            # Add other video flows
            for flow in video_flows[1:]:
                collection_items.append({
                    "id": flow["id"],
                    "role": "video"
                })
            
            # Add audio flows
            for flow in audio_flows:
                collection_items.append({
                    "id": flow["id"],
                    "role": "audio"
                })
            
            if collection_items:
                print(f"\n   Creating multi-essence flow collection on {collection_flow_id[:8]}...")
                print(f"   Collecting {len(collection_items)} flows:")
                for item in collection_items:
                    print(f"      - {item['id'][:8]}... (role: {item['role']})")
                
                create_flow_collection(token, collection_flow_id, collection_items)
                print(f"   ✅ Multi-essence flow collection created")
        
        # 3. Create Source Collections
        print("\n3. Creating Source Collections...")
        
        if len(sources) >= 2:
            # Try to create a source collection
            # Note: Source collections are typically read-only and inferred from flow collections
            collection_source_id = sources[0]
            collection_items = [
                {
                    "id": source_id,
                    "role": "source"
                }
                for source_id in sources[1:]
            ]
            
            print(f"   Attempting to create source collection on {collection_source_id[:8]}...")
            print(f"   Collecting {len(collection_items)} sources:")
            for item in collection_items:
                print(f"      - {item['id'][:8]}... (role: {item['role']})")
            
            if create_source_collection(token, collection_source_id, collection_items):
                print(f"   ✅ Source collection created")
            else:
                print(f"   ℹ️  Source collections are read-only (inferred from flow collections)")
        
        print("\n" + "=" * 60)
        print("✅ Collection Creation Completed!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  📹 Flow Collections: Created on flow {video_flows[0]['id'][:8] if video_flows else 'N/A'}...")
        print(f"  📊 Source Collections: {'Created' if len(sources) >= 2 else 'Not created (read-only)'}")
        print(f"\nNote: Source collections are typically read-only and inferred from flow collections")
        print(f"      per TAMS 8.0 specification.")
        
    except Exception as e:
        print(f"\n❌ Collection creation failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()


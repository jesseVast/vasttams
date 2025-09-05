#!/usr/bin/env python3
"""
Test script for tag-based filtering functionality for sources and segments.
This script tests the new tag filtering feature implemented for sources and segments.
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on different port
HEADERS = {"Content-Type": "application/json"}

def test_sources_tag_filtering():
    """Test tag-based source filtering functionality"""
    print("🧪 Testing Sources Tag-based Filtering")
    print("=" * 50)
    
    # Test 1: Create a source with tags
    print("\n1. Creating a test source with tags...")
    source_data = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "format": "urn:x-nmos:format:video",
        "label": "Test Video Source",
        "description": "Test source for tag filtering",
        "tags": {
            "environment": "production",
            "priority": "high",
            "department": "engineering"
        }
    }
    
    try:
        # Create the source
        response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=HEADERS)
        if response.status_code == 201:
            print("✅ Source created successfully")
        else:
            print(f"❌ Failed to create source: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating source: {e}")
        return False
    
    # Test 2: Test source tag value filtering
    print("\n2. Testing source tag value filtering...")
    test_cases = [
        ("tag.environment=production", "sources with environment=production"),
        ("tag.priority=high", "sources with priority=high"),
        ("tag.department=engineering", "sources with department=engineering"),
        ("tag.nonexistent=value", "sources with nonexistent tag"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/sources?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f"✅ {description}: {count} sources found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    # Test 3: Test source tag existence filtering
    print("\n3. Testing source tag existence filtering...")
    test_cases = [
        ("tag_exists.environment=true", "sources that have environment tag"),
        ("tag_exists.priority=true", "sources that have priority tag"),
        ("tag_exists.nonexistent=true", "sources that have nonexistent tag"),
        ("tag_exists.nonexistent=false", "sources that don't have nonexistent tag"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/sources?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f"✅ {description}: {count} sources found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    # Test 4: Test combined source filtering
    print("\n4. Testing combined source filtering...")
    test_cases = [
        ("tag.environment=production&format=urn:x-nmos:format:video", "production video sources"),
        ("tag_exists.priority=true&label=Test Video Source", "priority sources with specific label"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/sources?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f"✅ {description}: {count} sources found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    return True

def test_segments_tag_filtering():
    """Test tag-based segment filtering functionality"""
    print("\n🧪 Testing Segments Tag-based Filtering")
    print("=" * 50)
    
    # First create a flow to have segments
    print("\n1. Creating a test flow...")
    flow_data = {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "source_id": "550e8400-e29b-41d4-a716-446655440000",
        "format": "urn:x-nmos:format:video",
        "codec": "video/mp4",
        "label": "Test Video Flow",
        "frame_width": 1920,
        "frame_height": 1080,
        "frame_rate": "25/1"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=HEADERS)
        if response.status_code == 201:
            print("✅ Flow created successfully")
        else:
            print(f"❌ Failed to create flow: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating flow: {e}")
        return False
    
    # Create segments with tags
    print("\n2. Creating test segments with tags...")
    segments_data = [
        {
            "object_id": "seg_001",
            "timerange": "[0:0_10:0)",
            "sample_offset": 0,
            "sample_count": 250,
            "key_frame_count": 10
        },
        {
            "object_id": "seg_002", 
            "timerange": "[10:0_20:0)",
            "sample_offset": 250,
            "sample_count": 250,
            "key_frame_count": 10
        }
    ]
    
    flow_id = "550e8400-e29b-41d4-a716-446655440001"
    
    for i, segment_data in enumerate(segments_data):
        try:
            response = requests.post(f"{BASE_URL}/flows/{flow_id}/segments", json=segment_data, headers=HEADERS)
            if response.status_code == 201:
                print(f"✅ Segment {i+1} created successfully")
                
                # Add tags to the segment
                segment_id = segment_data["object_id"]
                tags = {
                    "environment": "production" if i == 0 else "staging",
                    "priority": "high" if i == 0 else "medium",
                    "quality": "hd" if i == 0 else "sd"
                }
                
                for tag_name, tag_value in tags.items():
                    tag_response = requests.put(
                        f"{BASE_URL}/flows/{flow_id}/segments/{segment_id}/tags/{tag_name}",
                        data=tag_value,
                        headers={"Content-Type": "text/plain"}
                    )
                    if tag_response.status_code == 200:
                        print(f"  ✅ Added tag {tag_name}={tag_value}")
                    else:
                        print(f"  ⚠️  Failed to add tag {tag_name}: {tag_response.status_code}")
            else:
                print(f"❌ Failed to create segment {i+1}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error creating segment {i+1}: {e}")
    
    # Test 3: Test segment tag value filtering
    print("\n3. Testing segment tag value filtering...")
    test_cases = [
        ("tag.environment=production", "segments with environment=production"),
        ("tag.priority=high", "segments with priority=high"),
        ("tag.quality=hd", "segments with quality=hd"),
        ("tag.nonexistent=value", "segments with nonexistent tag"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data)
                print(f"✅ {description}: {count} segments found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    # Test 4: Test segment tag existence filtering
    print("\n4. Testing segment tag existence filtering...")
    test_cases = [
        ("tag_exists.environment=true", "segments that have environment tag"),
        ("tag_exists.priority=true", "segments that have priority tag"),
        ("tag_exists.nonexistent=true", "segments that have nonexistent tag"),
        ("tag_exists.nonexistent=false", "segments that don't have nonexistent tag"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data)
                print(f"✅ {description}: {count} segments found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    # Test 5: Test combined segment filtering
    print("\n5. Testing combined segment filtering...")
    test_cases = [
        ("tag.environment=production&timerange=[0:0_15:0)", "production segments in time range"),
        ("tag_exists.priority=true&timerange=[0:0_15:0)", "priority segments in time range"),
    ]
    
    for query, description in test_cases:
        try:
            response = requests.get(f"{BASE_URL}/flows/{flow_id}/segments?{query}", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                count = len(data)
                print(f"✅ {description}: {count} segments found")
            else:
                print(f"❌ {description}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")
    
    return True

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    try:
        # Delete the test flow (this will also delete segments)
        response = requests.delete(f"{BASE_URL}/flows/550e8400-e29b-41d4-a716-446655440001")
        if response.status_code == 200:
            print("✅ Test flow deleted successfully")
        else:
            print(f"⚠️  Could not delete test flow: {response.status_code}")
        
        # Delete the test source
        response = requests.delete(f"{BASE_URL}/sources/550e8400-e29b-41d4-a716-446655440000")
        if response.status_code == 200:
            print("✅ Test source deleted successfully")
        else:
            print(f"⚠️  Could not delete test source: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Error cleaning up: {e}")

def main():
    """Main test function"""
    print("TAMS Sources and Segments Tag Filtering Test")
    print("Make sure the TAMS server is running on http://localhost:8000")
    print()
    
    try:
        # Test sources tag filtering
        sources_success = test_sources_tag_filtering()
        
        # Test segments tag filtering
        segments_success = test_segments_tag_filtering()
        
        # Clean up
        cleanup_test_data()
        
        if sources_success and segments_success:
            print("\n" + "=" * 50)
            print("🎉 All tests completed successfully!")
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

if __name__ == "__main__":
    main()

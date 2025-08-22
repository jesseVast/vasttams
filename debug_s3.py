#!/usr/bin/env python3
"""
Debug S3 bucket contents - check if objects are actually being stored
"""
import requests
import json

def check_s3_bucket():
    """Check what's in the S3 bucket"""
    print("🔍 Debugging S3 Bucket Contents")
    print("=" * 50)
    
    # Get S3 store status from our diagnostic endpoint
    try:
        print("📊 Checking diagnostic info...")
        response = requests.get("http://localhost:8000/diagnostics/health")
        if response.status_code == 200:
            health_data = response.json()
            for test in health_data.get('connection_tests', []):
                if test['test_name'] == 's3_connection':
                    print(f"   S3 Status: {test['status']}")
                    print(f"   Details: {test.get('details', {})}")
                    break
        else:
            print(f"   Failed to get diagnostics: {response.status_code}")
    except Exception as e:
        print(f"   Error checking diagnostics: {e}")
    
    # Try to list segments via the API
    try:
        print("\n📋 Checking segments via API...")
        response = requests.get("http://localhost:8000/flows/d2e3f4a5-6b7c-4d8e-9f0a-1b2c3d4e5f6a/segments")
        if response.status_code == 200:
            segments = response.json()
            print(f"   Found {len(segments)} segments in API")
            for segment in segments:
                print(f"   - Segment: {segment.get('object_id', 'N/A')}")
                print(f"     Size: {segment.get('size', 0)} bytes")
                print(f"     Timerange: {segment.get('timerange', 'N/A')}")
        else:
            print(f"   Failed to get segments: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Error checking segments: {e}")
    
    # Check objects via API
    try:
        print("\n📦 Checking objects via API...")
        response = requests.get("http://localhost:8000/objects")
        if response.status_code == 200:
            objects = response.json()
            print(f"   Found {len(objects)} objects in API")
            for obj in objects:
                print(f"   - Object: {obj.get('id', 'N/A')}")
                print(f"     Size: {obj.get('size', 0)} bytes")
        else:
            print(f"   Failed to get objects: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Error checking objects: {e}")

if __name__ == "__main__":
    check_s3_bucket()

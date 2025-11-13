#!/usr/bin/env python3
"""
Test script to verify object lifecycle per TAMS API specification.

Workflow:
1. Create source, flow
2. Allocate storage and get presigned URL
3. Upload object to S3
4. Create segment referencing the object
5. Verify object cannot be deleted (409) while segment exists
6. Delete segment
7. Verify object is automatically deleted (per TAMS spec: unreferenced objects are deleted)

Per TAMS 8.0 spec: "Media Objects that are no longer referenced by any Segments will be deleted."
"""

import requests
import uuid
import json
import sys
import logging
from pathlib import Path

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.core.config import get_settings

# Get settings for API base URL
settings = get_settings()
BASE_URL = f"http://{settings.host}:{settings.port}/api/tams/latest"

def get_auth_headers():
    """Get authentication headers with JWT token"""
    import jwt
    from datetime import datetime, timezone, timedelta
    
    # Try to load cached token first
    import json
    import os
    import tempfile
    
    cache_dir = os.path.join(tempfile.gettempdir(), "vasttams_test_cache")
    cache_path = os.path.join(cache_dir, "auth_token.json")
    
    token = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                token = cache_data.get("token")
                # Check if token is still valid
                if token:
                    try:
                        decoded = jwt.decode(token, options={"verify_signature": False})
                        exp = decoded.get("exp")
                        if exp:
                            exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
                            now = datetime.now(timezone.utc)
                            if exp_time <= (now + timedelta(minutes=5)):
                                token = None  # Token expired or expiring soon
                    except:
                        token = None
        except:
            pass
    
    # If no valid cached token, authenticate
    if not token:
        print("Authenticating...")
        auth_data = {
            "username": "admin",
            "password": "admin"
        }
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json=auth_data)
            if response.status_code == 200:
                token = response.json().get("access_token")
                # Cache the token
                os.makedirs(cache_dir, exist_ok=True)
                with open(cache_path, 'w') as f:
                    json.dump({"token": token, "cached_at": datetime.now(timezone.utc).isoformat()}, f)
            else:
                print(f"Authentication failed: {response.status_code} - {response.text}")
                return {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
        except Exception as e:
            print(f"Authentication error: {e}")
            return {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
    
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

def print_response(label, response):
    """Print response details"""
    print(f"\n{label}:")
    print(f"  Status: {response.status_code}")
    print(f"  Headers: {dict(response.headers)}")
    try:
        response_json = response.json()
        print(f"  Response: {json.dumps(response_json, indent=2)}")
        return response_json
    except:
        print(f"  Response: {response.text}")
        return None

def main():
    print("=" * 80)
    print("Object Lifecycle Test")
    print("=" * 80)
    
    auth_headers = get_auth_headers()
    
    # Step 1: Create Source
    print("\n[1] Creating Source...")
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video"
    }
    response = requests.post(f"{BASE_URL}/sources", json=source_data, headers=auth_headers)
    print_response("Create Source", response)
    if response.status_code not in [200, 201]:
        print(f"ERROR: Failed to create source")
        return
    print(f"✓ Source created: {source_id}")
    
    # Step 2: Create Flow
    print("\n[2] Creating Flow...")
    flow_id = str(uuid.uuid4())
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "format": "urn:x-nmos:format:video",
        "codec": "video/H264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {"numerator": 25, "denominator": 1}
        }
    }
    response = requests.post(f"{BASE_URL}/flows", json=flow_data, headers=auth_headers)
    print_response("Create Flow", response)
    if response.status_code not in [200, 201]:
        print(f"ERROR: Failed to create flow")
        return
    print(f"✓ Flow created: {flow_id}")
    
    # Step 3: Get presigned URL via POST /flows/{flowId}/storage (allocates storage and returns presigned URL)
    print("\n[3] Getting presigned URL via POST /flows/{flowId}/storage...")
    
    # Get default storage backend ID (required for storage allocation)
    try:
        storage_backends_response = requests.get(f"{BASE_URL}/service/storage-backends", headers=auth_headers)
        if storage_backends_response.status_code == 200:
            backends = storage_backends_response.json()
            if isinstance(backends, dict) and "data" in backends:
                backends = backends["data"]
            if not backends:
                print(f"ERROR: No storage backends available")
                return
            default_backend = next((b for b in backends if b.get("default_storage") is True), None)
            storage_id = (default_backend or backends[0]).get("id")
            print(f"✓ Using storage backend: {storage_id}")
        else:
            print(f"ERROR: Failed to get storage backends: {storage_backends_response.status_code}")
            return
    except Exception as e:
        print(f"ERROR: Failed to get storage backend: {e}")
        return
    
    # Request storage allocation with limit and storage_id (matching TAMS API spec)
    # TAMS spec: POST /flows/{flowId}/storage accepts limit, object_ids, and storage_id (no label)
    storage_data = {
        "limit": 1,  # Request only 1 presigned URL
        "storage_id": storage_id
    }
    response = requests.post(f"{BASE_URL}/flows/{flow_id}/storage", json=storage_data, headers=auth_headers)
    storage_result = print_response("Get Presigned URL (via storage)", response)
    if response.status_code not in [200, 201]:
        print(f"ERROR: Failed to get presigned URL")
        return
    
    # Extract object_id, PUT URL, content-type, and storage path from response (matching ingest_test_data.py)
    try:
        media_object = storage_result["media_objects"][0]
        object_id = media_object["object_id"]
        put_url_obj = media_object["put_url"]
        presigned_url = put_url_obj["url"]
        # Extract content-type from put_url (required for S3 upload header - must match signature)
        content_type = put_url_obj.get("content-type", "application/octet-stream")
        storage_path = media_object["metadata"].get("storage_path", "N/A")
        print(f"✓ Object allocated: {object_id}")
        print(f"✓ Storage path: {storage_path}")
        print(f"✓ Presigned URL received")
        print(f"✓ Content-Type: {content_type}")
    except Exception as e:
        print(f"ERROR: Failed to parse storage response: {e}")
        print(f"Response: {storage_result}")
        return
    
    # Step 4: Upload object to S3 using the presigned PUT URL (matching ingest_test_data.py workflow)
    print("\n[4] Uploading Object to S3 using presigned PUT URL...")
    logger.debug(f"Uploading object {object_id} to S3 using PUT URL")
    # Create a small test file (1KB of zeros) - in real usage this would be actual media content
    test_data = b'\x00' * 1024
    try:
        # Set Content-Type header - required when presigned URL includes content-type in signature
        # This must match the content-type from the put_url response
        headers = {"Content-Type": content_type}
        upload_response = requests.put(presigned_url, data=test_data, headers=headers)
        upload_response.raise_for_status()  # Raise exception for non-2xx status codes
        print(f"✓ Object uploaded to S3 successfully (status: {upload_response.status_code})")
        logger.debug(f"Object uploaded successfully")
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Object upload failed with status {e.response.status_code}")
        print(f"  Response: {e.response.text}")
        logger.error(f"Object upload failed: {e.response.status_code} - {e.response.text}")
        return
    except Exception as e:
        print(f"ERROR: Failed to upload object to S3: {e}")
        logger.error(f"Object upload exception: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Verify object is accessible after upload
    print("\n[5] Verifying Object is accessible after upload...")
    logger.debug(f"Attempting to GET object {object_id} after upload")
    response = requests.get(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
    obj_data = print_response("GET Object (after upload)", response)
    if response.status_code == 200:
        print(f"✓ Object is accessible via GET")
        print(f"  Object details:")
        print(f"    ID: {obj_data.get('id')}")
        print(f"    Referenced by flows: {obj_data.get('referenced_by_flows', [])}")
        print(f"    First referenced by flow: {obj_data.get('first_referenced_by_flow')}")
        print(f"    Size: {obj_data.get('size')}")
        logger.debug(f"Object retrieved successfully: {obj_data}")
    elif response.status_code == 404:
        print(f"✗ Object NOT found via GET (404)")
        logger.warning(f"Object {object_id} not found after upload")
        return
    else:
        print(f"✗ Unexpected status: {response.status_code}")
        logger.error(f"Unexpected status code {response.status_code} when getting object")
        return
    
    # Step 6: Create a Segment referencing the object (object must exist in S3 first)
    print("\n[6] Creating Segment referencing the object (object is now in S3)...")
    segment_data = {
        "object_id": object_id,
        "timerange": {"value": "[0:0_60:0)"},
        "sample_offset": 0,
        "sample_count": 1500
    }
    logger.debug(f"Creating segment for object {object_id} with data: {segment_data}")
    response = requests.post(f"{BASE_URL}/flows/{flow_id}/segments", json=segment_data, headers=auth_headers)
    segment_result = print_response("Create Segment", response)
    if response.status_code not in [200, 201]:
        print(f"ERROR: Failed to create segment")
        logger.error(f"Segment creation failed: {response.status_code} - {response.text}")
        return
    else:
        print(f"✓ Segment created successfully")
        logger.debug(f"Segment created successfully: {segment_result}")
    
    # Step 7: Verify object is still accessible after segment creation
    print("\n[7] Verifying Object is still accessible after segment creation...")
    response = requests.get(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
    obj_data = print_response("GET Object (after segment creation)", response)
    if response.status_code == 200:
        print(f"✓ Object is accessible via GET")
        print(f"  Referenced by flows: {obj_data.get('referenced_by_flows', [])}")
        print(f"  First referenced by flow: {obj_data.get('first_referenced_by_flow')}")
        logger.debug(f"Object retrieved successfully: {obj_data}")
    elif response.status_code == 404:
        print(f"✗ Object NOT found via GET (404)")
        logger.warning(f"Object {object_id} not found after segment creation")
        return
    else:
        print(f"✗ Unexpected status: {response.status_code}")
        logger.error(f"Unexpected status code {response.status_code} when getting object")
        return
    
    # Step 8: Try to DELETE the object (should fail - segment still references it)
    print("\n[8] Attempting to DELETE the object (should fail - segment references it)...")
    logger.debug(f"Attempting to DELETE object {object_id} (should be blocked by segment)")
    response = requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
    delete_result = print_response("DELETE Object (with segment)", response)
    if response.status_code in [200, 204]:
        print(f"⚠ Object deleted (unexpected - should be blocked by segment)")
        logger.warning(f"Object deleted unexpectedly - segment should have blocked deletion")
    elif response.status_code == 409:
        print(f"✓ Object deletion blocked (409 Conflict - referenced by segment)")
        print(f"  This is expected - object is referenced by segment")
        logger.info(f"Object deletion correctly blocked: {delete_result.get('detail') if delete_result else 'N/A'}")
    elif response.status_code == 404:
        print(f"✗ Object not found for deletion (404)")
        logger.warning(f"Object {object_id} not found when attempting deletion")
        return
    else:
        print(f"✗ Unexpected status: {response.status_code}")
        logger.error(f"Unexpected status code {response.status_code} when deleting object")
        return
    
    # Step 9: Delete Segment (must delete before object can be deleted)
    print("\n[9] Deleting Segment (required before object deletion)...")
    logger.debug(f"Deleting segment for flow {flow_id}")
    response = requests.delete(f"{BASE_URL}/flows/{flow_id}/segments?timerange=[0:0_60:0)", headers=auth_headers)
    delete_seg_result = print_response("DELETE Segment", response)
    if response.status_code in [200, 204]:
        print(f"✓ Segment deleted successfully")
        logger.debug(f"Segment deleted successfully")
    else:
        print(f"ERROR: Failed to delete segment: {response.status_code}")
        logger.error(f"Segment deletion failed: {response.status_code}")
        return
    
    # Step 10: Verify object is deleted after segment deletion (TAMS spec behavior)
    print("\n[10] Verifying Object is deleted after segment deletion (TAMS spec behavior)...")
    print("  Per TAMS spec: 'Media Objects that are no longer referenced by any Segments will be deleted.'")
    response = requests.get(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
    obj_data = print_response("GET Object (after segment deletion)", response)
    if response.status_code == 404:
        print(f"✓ Object deleted after segment deletion (404)")
        print(f"  This is expected per TAMS spec - unreferenced objects are automatically deleted")
        logger.info(f"Object {object_id} deleted after segment deletion (expected per TAMS spec)")
    elif response.status_code == 200:
        print(f"⚠ Object still exists after segment deletion (200)")
        print(f"  This may indicate the object is referenced by other segments or flows")
        print(f"  Referenced by flows: {obj_data.get('referenced_by_flows', [])}")
        logger.debug(f"Object still exists: {obj_data}")
        # If object still exists, we can try to delete it manually
        print(f"\n  Attempting manual deletion of object...")
        delete_response = requests.delete(f"{BASE_URL}/objects/{object_id}", headers=auth_headers)
        if delete_response.status_code in [200, 204]:
            print(f"  ✓ Object deleted manually")
        elif delete_response.status_code == 409:
            print(f"  ⚠ Object deletion blocked (409) - still referenced")
        else:
            print(f"  ⚠ Unexpected deletion status: {delete_response.status_code}")
    else:
        print(f"✗ Unexpected status: {response.status_code}")
        logger.error(f"Unexpected status code {response.status_code} when getting object")
        return
    
    # Step 11: Cleanup - Delete Flow
    print("\n[11] Cleaning up - Deleting Flow...")
    response = requests.delete(f"{BASE_URL}/flows/{flow_id}", headers=auth_headers)
    print_response("DELETE Flow", response)
    if response.status_code in [200, 204]:
        print(f"✓ Flow deleted")
    else:
        print(f"⚠ Flow deletion: {response.status_code}")
    
    # Step 12: Cleanup - Delete Source
    print("\n[12] Cleaning up - Deleting Source...")
    response = requests.delete(f"{BASE_URL}/sources/{source_id}", headers=auth_headers)
    print_response("DELETE Source", response)
    if response.status_code in [200, 204]:
        print(f"✓ Source deleted")
    else:
        print(f"⚠ Source deletion: {response.status_code}")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print(f"Make sure the server is running at {BASE_URL}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


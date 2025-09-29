#!/usr/bin/env python3
"""
Shared utilities for TAMS API endpoint testing
"""

import requests
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Test data storage
test_data = {
    "source_id": None,
    "flow_id": None,
    "object_ids": [],
    "segment_ids": [],
    "collection_ids": []
}

def generate_uuid():
    """Generate a UUID4 string"""
    return str(uuid.uuid4())

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")

def print_result(operation, endpoint, status_code, data=None, error=None):
    """Print formatted test result"""
    status_emoji = "✅" if 200 <= status_code < 300 else "❌"
    print(f"{status_emoji} {operation} {endpoint}: {status_code}")
    
    if error:
        print(f"   Error: {error}")
    elif data and isinstance(data, dict):
        if 'id' in data:
            print(f"   ID: {data['id']}")
        if 'object_id' in data:
            print(f"   Object ID: {data['object_id']}")
        if 'storage_path' in data:
            print(f"   Storage Path: {data['storage_path']}")
        if 'get_urls' in data and data['get_urls']:
            print(f"   get_urls: {len(data['get_urls'])} URLs generated")
    elif data and isinstance(data, list):
        print(f"   Count: {len(data)} items")

def assert_response_success(operation, endpoint, response, expected_status=200):
    """Assert that a response is successful and print result"""
    status_code = response.status_code
    success = 200 <= status_code < 300
    
    if success:
        print_result(operation, endpoint, status_code, response.json() if response.content else None)
    else:
        error_text = response.text if response.content else "No response content"
        print_result(operation, endpoint, status_code, error=error_text)
    
    assert success, f"{operation} {endpoint} failed with status {status_code}: {response.text if response.content else 'No response content'}"
    return response.json() if response.content else None

def assert_response_status(operation, endpoint, response, expected_status):
    """Assert that a response has the expected status code"""
    status_code = response.status_code
    success = status_code == expected_status
    
    if success:
        print_result(operation, endpoint, status_code, response.json() if response.content else None)
    else:
        error_text = response.text if response.content else "No response content"
        print_result(operation, endpoint, status_code, error=error_text)
    
    assert success, f"{operation} {endpoint} expected status {expected_status}, got {status_code}: {response.text if response.content else 'No response content'}"
    return response.json() if response.content else None

def assert_response_any_status(operation, endpoint, response, expected_statuses):
    """Assert that a response has one of the expected status codes"""
    status_code = response.status_code
    success = status_code in expected_statuses
    
    if success:
        print_result(operation, endpoint, status_code, response.json() if response.content else None)
    else:
        error_text = response.text if response.content else "No response content"
        print_result(operation, endpoint, status_code, error=error_text)
    
    assert success, f"{operation} {endpoint} expected status in {expected_statuses}, got {status_code}: {response.text if response.content else 'No response content'}"
    return response.json() if response.content else None

def create_test_source():
    """Create a test source and return its ID"""
    source_id = generate_uuid()
    source_data = {
        "id": source_id,
        "format": "urn:x-nmos:format:video",
        "label": f"Test Source {source_id[:8]}",
        "description": "Test source for API testing"
    }
    
    response = requests.post(f"{BASE_URL}/sources", json=source_data)
    data = assert_response_success("POST", "/sources", response, 201)
    return data["id"]

def create_test_flow(source_id: str):
    """Create a test flow and return its ID"""
    flow_id = generate_uuid()
    flow_data = {
        "id": flow_id,
        "source_id": source_id,
        "label": f"Test Flow {flow_id[:8]}",
        "description": "Test flow for API testing",
        "format": "urn:x-nmos:format:video",
        "codec": "video/H264",
        "essence_parameters": {
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": {"numerator": 25, "denominator": 1}
        }
    }
    
    response = requests.post(f"{BASE_URL}/flows", json=flow_data)
    data = assert_response_success("POST", "/flows", response, 201)
    return data["id"]

def cleanup_test_data():
    """Clean up test data"""
    # Delete flows first (due to dependencies)
    if test_data.get("flow_id"):
        try:
            response = requests.delete(f"{BASE_URL}/flows/{test_data['flow_id']}?cascade=true")
            if response.status_code in [200, 404]:
                print(f"   🧹 Cleaned up flow: {test_data['flow_id']}")
        except Exception as e:
            print(f"   ⚠️  Failed to cleanup flow: {e}")
    
    # Delete sources
    if test_data.get("source_id"):
        try:
            response = requests.delete(f"{BASE_URL}/sources/{test_data['source_id']}")
            if response.status_code in [200, 404]:
                print(f"   🧹 Cleaned up source: {test_data['source_id']}")
        except Exception as e:
            print(f"   ⚠️  Failed to cleanup source: {e}")
    
    # Reset test data
    test_data.update({
        "source_id": None,
        "flow_id": None,
        "object_ids": [],
        "segment_ids": [],
        "collection_ids": []
    })

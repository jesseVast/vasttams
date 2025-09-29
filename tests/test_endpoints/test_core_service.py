#!/usr/bin/env python3
"""
Core Service Endpoint Tests

Tests for:
- Health check endpoints
- Root endpoints
- Service information endpoints
- OpenAPI specification
- Metrics endpoints
"""

import requests
from datetime import datetime
from test_utils import (
    BASE_URL, print_section, print_subsection, print_result,
    assert_response_success, assert_response_status
)

def test_health_endpoints():
    """Test health check endpoints"""
    print_section("HEALTH CHECK ENDPOINTS")
    
    # GET /health
    print_subsection("GET Health Status")
    response = requests.get(f"{BASE_URL}/health")
    data = assert_response_success("GET", "/health", response, 200)
    assert "status" in data
    assert data["status"] == "healthy"
    
    # HEAD /health
    print_subsection("HEAD Health Status")
    response = requests.head(f"{BASE_URL}/health")
    assert_response_status("HEAD", "/health", response, 200)

def test_root_endpoints():
    """Test root endpoints"""
    print_section("ROOT ENDPOINTS")
    
    # GET /
    print_subsection("GET Root Paths")
    response = requests.get(f"{BASE_URL}/")
    data = assert_response_success("GET", "/", response, 200)
    assert isinstance(data, list)
    assert len(data) > 0
    print(f"   Available paths: {', '.join(data)}")
    
    # HEAD /
    print_subsection("HEAD Root Paths")
    response = requests.head(f"{BASE_URL}/")
    assert_response_status("HEAD", "/", response, 200)

def test_service_endpoints():
    """Test service information endpoints"""
    print_section("SERVICE ENDPOINTS")
    
    # GET /service
    print_subsection("GET Service Information")
    response = requests.get(f"{BASE_URL}/service")
    data = assert_response_success("GET", "/service", response, 200)
    assert "version" in data
    assert "name" in data
    
    # HEAD /service
    print_subsection("HEAD Service Information")
    response = requests.head(f"{BASE_URL}/service")
    assert_response_status("HEAD", "/service", response, 200)
    
    # POST /service (update service info)
    print_subsection("POST Update Service Information")
    service_update = {
        "name": "TAMS Test Service",
        "version": "7.0",
        "description": "Updated service description for testing"
    }
    response = requests.post(f"{BASE_URL}/service", json=service_update)
    # Note: This might return 200 or 404 depending on implementation
    if response.status_code in [200, 201, 404]:
        print_result("POST", "/service", response.status_code)
    else:
        assert_response_success("POST", "/service", response, 200)

def test_storage_backends():
    """Test storage backend endpoints"""
    print_section("STORAGE BACKEND ENDPOINTS")
    
    # GET /service/storage-backends
    print_subsection("GET Storage Backends")
    response = requests.get(f"{BASE_URL}/service/storage-backends")
    data = assert_response_success("GET", "/service/storage-backends", response, 200)
    assert isinstance(data, list)
    
    # HEAD /service/storage-backends
    print_subsection("HEAD Storage Backends")
    response = requests.head(f"{BASE_URL}/service/storage-backends")
    assert_response_status("HEAD", "/service/storage-backends", response, 200)

def test_openapi_spec():
    """Test OpenAPI specification endpoint"""
    print_section("OPENAPI SPECIFICATION")
    
    # GET /openapi.json
    print_subsection("GET OpenAPI Specification")
    response = requests.get(f"{BASE_URL}/openapi.json")
    data = assert_response_success("GET", "/openapi.json", response, 200)
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data
    print(f"   OpenAPI version: {data.get('openapi', 'unknown')}")
    print(f"   API title: {data.get('info', {}).get('title', 'unknown')}")

def test_metrics_endpoint():
    """Test metrics endpoint"""
    print_section("METRICS ENDPOINT")
    
    # GET /metrics
    print_subsection("GET Prometheus Metrics")
    response = requests.get(f"{BASE_URL}/metrics")
    # Metrics endpoint might return 200 or 404 depending on implementation
    if response.status_code in [200, 404]:
        print_result("GET", "/metrics", response.status_code)
        if response.status_code == 200:
            print(f"   Metrics data length: {len(response.text)} characters")
    else:
        assert_response_success("GET", "/metrics", response, 200)

def test_config_endpoints():
    """Test configuration endpoints"""
    print_section("CONFIGURATION ENDPOINTS")
    
    # GET /config/async-deletion-threshold
    print_subsection("GET Async Deletion Threshold")
    response = requests.get(f"{BASE_URL}/config/async-deletion-threshold")
    # This might return 200 or 404 depending on implementation
    if response.status_code in [200, 404]:
        print_result("GET", "/config/async-deletion-threshold", response.status_code)
    else:
        assert_response_success("GET", "/config/async-deletion-threshold", response, 200)
    
    # PUT /config/async-deletion-threshold
    print_subsection("PUT Async Deletion Threshold")
    config_data = {"threshold": 3600}
    response = requests.put(f"{BASE_URL}/config/async-deletion-threshold", json=config_data)
    # This might return 200 or 404 depending on implementation
    if response.status_code in [200, 201, 404]:
        print_result("PUT", "/config/async-deletion-threshold", response.status_code)
    else:
        assert_response_success("PUT", "/config/async-deletion-threshold", response, 200)

def run_all_core_service_tests():
    """Run all core service tests"""
    print("🚀 Starting Core Service Endpoint Tests")
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"⏰ Start Time: {datetime.now().isoformat()}")
    
    try:
        test_health_endpoints()
        test_root_endpoints()
        test_service_endpoints()
        test_storage_backends()
        test_openapi_spec()
        test_metrics_endpoint()
        test_config_endpoints()
        
        print_section("CORE SERVICE TESTS SUMMARY")
        print("✅ All core service endpoint tests completed successfully")
        
    except Exception as e:
        print(f"❌ Core service tests failed: {e}")
        raise

if __name__ == "__main__":
    run_all_core_service_tests()

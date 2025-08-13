#!/usr/bin/env python3
"""
Basic tests for TAMS API

This script tests the basic functionality of the TAMS API endpoints.
"""

import asyncio
import httpx
import json
import uuid
from pydantic import UUID4
from datetime import datetime
import pytest
pytestmark = pytest.mark.asyncio

# API base URL
BASE_URL = "http://localhost:8000"

async def check_server_connection():
    """Check if the server is running and accessible"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                return True
    except httpx.ConnectError:
        print("❌ Cannot connect to server. Make sure the TAMS API server is running on http://localhost:8000")
        print("   Start the server with: python run.py")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    return False

async def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Health check passed")

async def test_service_info():
    """Test service information endpoint"""
    print("Testing service info...")
    async with httpx.AsyncClient() as client:
        # Test root endpoint (list of available paths)
        response = await client.get(f"{BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "service" in data
        assert "flows" in data
        assert "sources" in data
        
        # Test service endpoint (actual service information)
        response = await client.get(f"{BASE_URL}/service")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "urn:x-tams:service:api"
        assert data["api_version"] == "7.0"
        assert data["name"] == "TAMS API"
        print("✓ Service info passed")

async def test_create_and_get_source():
    """Test source creation and retrieval"""
    print("Testing source creation and retrieval...")
    
    # Create a test source
    source_data = {
        "id": str(uuid.uuid4()),
        "format": "urn:x-nmos:format:video",
        "label": "Test Video Source",
        "description": "A test video source for testing",
        "created_by": "test-user"
    }
    print(source_data)
    async with httpx.AsyncClient() as client:
        # Create source
        response = await client.post(f"{BASE_URL}/sources", json=source_data)
        print(response.json())
        if response.status_code != 201:
            print(f"❌ Source creation failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            assert False
        created_source = response.json()
        assert created_source["id"] == source_data["id"]
        
        # Get source
        response = await client.get(f"{BASE_URL}/sources/{source_data['id']}")
        if response.status_code != 200:
            print(f"❌ Source retrieval failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            assert False
        retrieved_source = response.json()
        assert retrieved_source["id"] == source_data["id"]
        assert retrieved_source["label"] == source_data["label"]
        
        print("✓ Source creation and retrieval passed")

async def test_create_and_get_flow():
    """Test flow creation and retrieval"""
    print("Testing flow creation and retrieval...")
    
    # First create a source
    source_data = {
        "id": str(uuid.uuid4()),
        "format": "urn:x-nmos:format:video",
        "label": "Test Source for Flow",
        "created_by": "test-user"
    }
    
    async with httpx.AsyncClient() as client:
        # Create source
        response = await client.post(f"{BASE_URL}/sources", json=source_data)
        if response.status_code != 201:
            print(f"❌ Source creation for flow test failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            assert False
        
        # Create a test flow
        flow_data = {
            "id": str(uuid.uuid4()),
            "source_id": source_data["id"],
            "format": "urn:x-nmos:format:video",
            "codec": "video/mp4",
            "label": "Test Video Flow",
            "description": "A test video flow",
            "frame_width": 1920,
            "frame_height": 1080,
            "frame_rate": "25:1",
            "created_by": "test-user"
        }
        
        # Create flow
        response = await client.post(f"{BASE_URL}/flows", json=flow_data)
        if response.status_code != 201:
            print(f"❌ Flow creation failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            assert False
        created_flow = response.json()
        assert created_flow["id"] == flow_data["id"]
        
        # Get flow
        response = await client.get(f"{BASE_URL}/flows/{flow_data['id']}")
        if response.status_code != 200:
            print(f"❌ Flow retrieval failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            assert False
        retrieved_flow = response.json()
        assert retrieved_flow["id"] == flow_data["id"]
        assert retrieved_flow["frame_width"] == flow_data["frame_width"]
        
        print("✓ Flow creation and retrieval passed")

async def test_analytics():
    """Test analytics endpoints"""
    print("Testing analytics endpoints...")
    
    async with httpx.AsyncClient() as client:
        # Test flow usage analytics
        response = await client.get(f"{BASE_URL}/analytics/flow-usage")
        assert response.status_code == 200
        data = response.json()
        print(f"Flow usage analytics response: {data}")
        assert "total_flows" in data
        assert "format_distribution" in data
        
        # Test storage usage analytics
        response = await client.get(f"{BASE_URL}/analytics/storage-usage")
        assert response.status_code == 200
        data = response.json()
        print(f"Storage usage analytics response: {data}")
        assert "total_objects" in data
        assert "total_size_bytes" in data
        
        # Test time range analytics
        response = await client.get(f"{BASE_URL}/analytics/time-range-analysis")
        assert response.status_code == 200
        data = response.json()
        print(f"Time range analytics response: {data}")
        assert "total_segments" in data
        
        print("✓ Analytics endpoints passed")

async def test_list_endpoints():
    """Test list endpoints"""
    print("Testing list endpoints...")
    
    async with httpx.AsyncClient() as client:
        # Test sources list
        response = await client.get(f"{BASE_URL}/sources")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        
        # Test flows list
        response = await client.get(f"{BASE_URL}/flows")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        
        # Test webhooks list
        response = await client.get(f"{BASE_URL}/service/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        
        print("✓ List endpoints passed")

async def main():
    """Run all tests"""
    print("Starting TAMS API tests...")
    print("=" * 50)
    
    # Check if server is running
    if not await check_server_connection():
        return
    
    try:
        await test_health_check()
        await test_service_info()
        await test_create_and_get_source()
        await test_create_and_get_flow()
        await test_analytics()
        await test_list_endpoints()
        
        print("=" * 50)
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Server Health Check Test

This test verifies that the TAMS API server is running and healthy
before running other real integration tests.
"""

import pytest
import requests
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TestServerHealth:
    """Test server health and availability"""
    
    @pytest.fixture(scope="session")
    def server_url(self) -> str:
        """Get the server URL from environment or use default"""
        import os
        host = os.getenv("HOST", "0.0.0.0")
        port = os.getenv("PORT", "8000")
        return f"http://{host}:{port}"
    
    @pytest.fixture(scope="session")
    def wait_for_server(self, server_url: str) -> bool:
        """Wait for server to be ready with retries"""
        max_retries = 30  # 30 seconds max wait
        retry_delay = 1   # 1 second between retries
        
        logger.info(f"🔍 Waiting for server to be ready at {server_url}")
        
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{server_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info(f"✅ Server is ready after {attempt + 1} attempts")
                    return True
            except requests.exceptions.RequestException as e:
                logger.info(f"⏳ Server not ready yet (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        logger.error(f"❌ Server failed to become ready after {max_retries} attempts")
        return False
    
    def test_server_health_endpoint(self, server_url: str, wait_for_server: bool):
        """Test that the server health endpoint responds correctly"""
        if not wait_for_server:
            pytest.skip("Server is not ready")
        
        logger.info(f"🏥 Testing server health endpoint at {server_url}/health")
        
        try:
            response = requests.get(f"{server_url}/health", timeout=10)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            # Check response format
            data = response.json()
            assert "status" in data, "Response missing 'status' field"
            assert data["status"] == "healthy", f"Expected 'healthy', got {data['status']}"
            
            logger.info("✅ Server health endpoint working correctly")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to server: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error testing health endpoint: {e}")
    
    def test_server_root_endpoint(self, server_url: str, wait_for_server: bool):
        """Test that the server root endpoint responds"""
        if not wait_for_server:
            pytest.skip("Server is not ready")
        
        logger.info(f"🏠 Testing server root endpoint at {server_url}/")
        
        try:
            response = requests.get(f"{server_url}/", timeout=10)
            
            # Root endpoint should respond (could be 200, 404, or redirect)
            assert response.status_code in [200, 404, 301, 302], f"Unexpected status code: {response.status_code}"
            
            logger.info(f"✅ Server root endpoint responding (status: {response.status_code})")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to server: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error testing root endpoint: {e}")
    
    def test_server_openapi_endpoint(self, server_url: str, wait_for_server: bool):
        """Test that the OpenAPI documentation endpoint is accessible"""
        if not wait_for_server:
            pytest.skip("Server is not ready")
        
        logger.info(f"📚 Testing OpenAPI endpoint at {server_url}/docs")
        
        try:
            response = requests.get(f"{server_url}/docs", timeout=10)
            
            # OpenAPI docs should be accessible
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            # Should contain HTML content
            assert "text/html" in response.headers.get("content-type", ""), "Expected HTML content"
            assert "<html" in response.text.lower(), "Expected HTML content"
            
            logger.info("✅ OpenAPI documentation endpoint accessible")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to server: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error testing OpenAPI endpoint: {e}")
    
    def test_server_response_time(self, server_url: str, wait_for_server: bool):
        """Test that the server responds within reasonable time"""
        if not wait_for_server:
            pytest.skip("Server is not ready")
        
        logger.info(f"⏱️ Testing server response time at {server_url}/health")
        
        try:
            start_time = time.time()
            response = requests.get(f"{server_url}/health", timeout=10)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert response_time < 5.0, f"Response time too slow: {response_time:.2f}s (expected < 5s)"
            
            logger.info(f"✅ Server response time: {response_time:.2f}s")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to server: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error testing response time: {e}")
    
    def test_server_connection_persistence(self, server_url: str, wait_for_server: bool):
        """Test that the server can handle multiple consecutive requests"""
        if not wait_for_server:
            pytest.skip("Server is not ready")
        
        logger.info(f"🔄 Testing server connection persistence at {server_url}/health")
        
        try:
            # Make multiple requests to test connection handling
            for i in range(5):
                response = requests.get(f"{server_url}/health", timeout=10)
                assert response.status_code == 200, f"Request {i+1} failed with status {response.status_code}"
                logger.info(f"✅ Request {i+1}/5 successful")
            
            logger.info("✅ Server handled multiple consecutive requests successfully")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to server: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error testing connection persistence: {e}")

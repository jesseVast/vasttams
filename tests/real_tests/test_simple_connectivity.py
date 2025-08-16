#!/usr/bin/env python3
"""
Simple Connectivity Test for Real Tests

This test verifies basic connectivity to external services
without complex database operations.
"""

import pytest
import requests
import os

# Import real environment configuration
import tests.real_env

class TestSimpleConnectivity:
    """Test basic connectivity to external services"""
    
    def test_vast_endpoint_reachable(self):
        """Test that VAST endpoint is reachable"""
        vast_endpoint = os.getenv("TAMS_VAST_ENDPOINT")
        assert vast_endpoint, "TAMS_VAST_ENDPOINT not set"
        
        print(f"Testing VAST connectivity to {vast_endpoint}")
        
        try:
            response = requests.get(vast_endpoint, timeout=10)
            print(f"VAST response status: {response.status_code}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("✅ VAST endpoint is reachable")
        except Exception as e:
            pytest.fail(f"Failed to connect to VAST: {e}")
    
    def test_s3_endpoint_reachable(self):
        """Test that S3 endpoint is reachable"""
        s3_endpoint = os.getenv("TAMS_S3_ENDPOINT_URL")
        assert s3_endpoint, "TAMS_S3_ENDPOINT_URL not set"
        
        print(f"Testing S3 connectivity to {s3_endpoint}")
        
        try:
            response = requests.get(s3_endpoint, timeout=10)
            print(f"S3 response status: {response.status_code}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("✅ S3 endpoint is reachable")
        except Exception as e:
            pytest.fail(f"Failed to connect to S3: {e}")
    
    def test_environment_variables_set(self):
        """Test that all required environment variables are set"""
        required_vars = [
            "TAMS_VAST_ENDPOINT",
            "TAMS_VAST_ACCESS_KEY",
            "TAMS_VAST_SECRET_KEY",
            "TAMS_S3_ENDPOINT_URL",
            "TAMS_S3_ACCESS_KEY_ID",
            "TAMS_S3_SECRET_ACCESS_KEY"
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            assert value, f"Environment variable {var} not set"
            print(f"✅ {var}: {value[:20]}...")
        
        print("✅ All required environment variables are set")

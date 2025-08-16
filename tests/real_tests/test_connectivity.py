#!/usr/bin/env python3
"""
Connectivity Test for Real Tests

This test verifies that we can connect to the required external services
(VAST database and S3 storage) before running other real tests.
"""

import pytest
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TestServiceConnectivity:
    """Test connectivity to external services"""
    
    @pytest.fixture(scope="session", autouse=True)
    def setup_environment(self):
        """Set up environment variables for 172.x.x.x services"""
        import os
        
        # Set VAST Database settings (from docker-compose.yml)
        os.environ["VAST_ENDPOINT"] = "http://172.200.204.90"
        os.environ["VAST_ACCESS_KEY"] = "SRSPW0DQT9T70Y787U68"
        os.environ["VAST_SECRET_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
        os.environ["VAST_BUCKET"] = "jthaloor-db"
        os.environ["VAST_SCHEMA"] = "tams7"
        
        # Set S3 settings (from docker-compose.yml)
        os.environ["S3_ENDPOINT_URL"] = "http://172.200.204.91"
        os.environ["S3_ACCESS_KEY_ID"] = "SRSPW0DQT9T70Y787U68"
        os.environ["S3_SECRET_ACCESS_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
        os.environ["S3_BUCKET_NAME"] = "jthaloor-s3"
        os.environ["S3_USE_SSL"] = "false"
        
        # Set server settings
        os.environ["HOST"] = "0.0.0.0"
        os.environ["PORT"] = "8000"
        os.environ["LOG_LEVEL"] = "INFO"
        
        print("🔧 Test environment configured with 172.x.x.x services:")
        print(f"   VAST: {os.environ['VAST_ENDPOINT']}")
        print(f"   S3: {os.environ['S3_ENDPOINT_URL']}")
        print(f"   Server: {os.environ['HOST']}:{os.environ['PORT']}")
    
    @pytest.fixture(scope="session")
    def vast_endpoint(self) -> str:
        """Get VAST endpoint from environment"""
        import os
        # Set environment variables if not already set
        if not os.getenv("VAST_ENDPOINT"):
            os.environ["VAST_ENDPOINT"] = "http://172.200.204.90"
        return os.getenv("VAST_ENDPOINT", "http://172.200.204.90")
    
    @pytest.fixture(scope="session")
    def s3_endpoint(self) -> str:
        """Get S3 endpoint from environment"""
        import os
        # Set environment variables if not already set
        if not os.getenv("S3_ENDPOINT_URL"):
            os.environ["S3_ENDPOINT_URL"] = "http://172.200.204.91"
        return os.getenv("S3_ENDPOINT_URL", "http://172.200.204.91")
    
    def test_vast_connectivity(self, vast_endpoint: str):
        """Test that we can reach the VAST database endpoint"""
        logger.info(f"🔍 Testing VAST connectivity to {vast_endpoint}")
        
        try:
            # Try to connect to the VAST endpoint
            # We'll just check if the endpoint responds
            response = requests.get(vast_endpoint, timeout=10)
            
            # Any response means the endpoint is reachable
            logger.info(f"✅ VAST endpoint reachable (status: {response.status_code})")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"❌ Cannot reach VAST endpoint {vast_endpoint}: {e}")
    
    def test_s3_connectivity(self, s3_endpoint: str):
        """Test that we can reach the S3 storage endpoint"""
        logger.info(f"🔍 Testing S3 connectivity to {s3_endpoint}")
        
        try:
            # Try to connect to the S3 endpoint
            response = requests.get(s3_endpoint, timeout=10)
            
            # Any response means the endpoint is reachable
            logger.info(f"✅ S3 endpoint reachable (status: {response.status_code})")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"❌ Cannot reach S3 endpoint {s3_endpoint}: {e}")
    
    def test_vast_credentials(self, vast_endpoint: str):
        """Test that VAST credentials are properly configured"""
        import os
        
        access_key = os.getenv("VAST_ACCESS_KEY")
        secret_key = os.getenv("VAST_SECRET_KEY")
        bucket = os.getenv("VAST_BUCKET")
        schema = os.getenv("VAST_SCHEMA")
        
        logger.info("🔑 Testing VAST credentials configuration")
        
        # Check that all required credentials are set
        assert access_key, "VAST_ACCESS_KEY not set"
        assert secret_key, "VAST_SECRET_KEY not set"
        assert bucket, "VAST_BUCKET not set"
        assert schema, "VAST_SCHEMA not set"
        
        logger.info(f"✅ VAST credentials configured:")
        logger.info(f"   Access Key: {access_key[:8]}...")
        logger.info(f"   Bucket: {bucket}")
        logger.info(f"   Schema: {schema}")
    
    def test_s3_credentials(self, s3_endpoint: str):
        """Test that S3 credentials are properly configured"""
        import os
        
        access_key = os.getenv("S3_ACCESS_KEY_ID")
        secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
        bucket = os.getenv("S3_BUCKET_NAME")
        
        logger.info("🔑 Testing S3 credentials configuration")
        
        # Check that all required credentials are set
        assert access_key, "S3_ACCESS_KEY_ID not set"
        assert secret_key, "S3_SECRET_ACCESS_KEY not set"
        assert bucket, "S3_BUCKET_NAME not set"
        
        logger.info(f"✅ S3 credentials configured:")
        logger.info(f"   Access Key: {access_key[:8]}...")
        logger.info(f"   Bucket: {bucket}")
    
    def test_environment_variables(self):
        """Test that all required environment variables are set"""
        import os
        
        required_vars = [
            "VAST_ENDPOINT",
            "VAST_ACCESS_KEY", 
            "VAST_SECRET_KEY",
            "VAST_BUCKET",
            "VAST_SCHEMA",
            "S3_ENDPOINT_URL",
            "S3_ACCESS_KEY_ID",
            "S3_SECRET_ACCESS_KEY",
            "S3_BUCKET_NAME"
        ]
        
        logger.info("🔧 Testing environment variable configuration")
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            pytest.fail(f"❌ Missing environment variables: {missing_vars}")
        
        logger.info("✅ All required environment variables are set")
        
        # Log the configuration
        logger.info("📋 Current configuration:")
        logger.info(f"   VAST: {os.getenv('VAST_ENDPOINT')}")
        logger.info(f"   S3: {os.getenv('S3_ENDPOINT_URL')}")
        logger.info(f"   Server: {os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}")

#!/usr/bin/env python3
"""
Test Configuration for Real Tests

This module sets up the correct environment variables for testing
with the available 172.x.x.x services.
"""

import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables for 172.x.x.x services"""
    
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
    
    yield
    
    # Cleanup (optional)
    print("🧹 Test environment cleanup complete")

# Also set environment variables at module import time for immediate availability
def _setup_environment_immediately():
    """Set up environment variables immediately when module is imported"""
    # Set VAST Database settings (from docker-compose.yml)
    os.environ["VAST_ENDPOINT"] = "http://172.200.204.90"
    os.environ["VAST_ACCESS_KEY"] = "SRSPW0DQT9T70Y787U68"
    os.environ["VAST_SECRET_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    os.environ["VAST_BUCKET"] = "jthaloor-db"
    os.environ["VAST_SCHEMA"] = "tams7"
    os.environ["S3_ENDPOINT_URL"] = "http://172.200.204.91"
    os.environ["S3_ACCESS_KEY_ID"] = "SRSPW0DQT9T70Y787U68"
    os.environ["S3_SECRET_ACCESS_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    os.environ["S3_BUCKET_NAME"] = "jthaloor-s3"
    os.environ["S3_USE_SSL"] = "false"
    os.environ["HOST"] = "0.0.0.0"
    os.environ["PORT"] = "8000"

# Set environment variables immediately
_setup_environment_immediately()

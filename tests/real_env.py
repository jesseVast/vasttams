#!/usr/bin/env python3
"""
Real Environment Configuration for TAMS Tests

This file sets the correct environment variables for testing with
the available 172.x.x.x services.
"""

import os

def setup_real_environment():
    """Set up environment variables for real testing"""
    
    # Set VAST Database settings (from docker-compose.yml)
    # Note: Application uses TAMS_ prefix for environment variables
    os.environ["TAMS_VAST_ENDPOINT"] = "http://172.200.204.90"
    os.environ["TAMS_VAST_ACCESS_KEY"] = "SRSPW0DQT9T70Y787U68"
    os.environ["TAMS_VAST_SECRET_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    os.environ["TAMS_VAST_BUCKET"] = "jthaloor-db"
    os.environ["TAMS_VAST_SCHEMA"] = "tams7"
    
    # Set S3 settings (from docker-compose.yml)
    os.environ["TAMS_S3_ENDPOINT_URL"] = "http://172.200.204.91"
    os.environ["TAMS_S3_ACCESS_KEY_ID"] = "SRSPW0DQT9T70Y787U68"
    os.environ["TAMS_S3_SECRET_ACCESS_KEY"] = "WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr"
    os.environ["TAMS_S3_BUCKET_NAME"] = "jthaloor-s3"
    os.environ["TAMS_S3_USE_SSL"] = "false"
    
    # Set server settings
    os.environ["HOST"] = "0.0.0.0"
    os.environ["PORT"] = "8000"
    os.environ["LOG_LEVEL"] = "INFO"
    
    print("🔧 Real environment configured:")
    print(f"   VAST: {os.environ['TAMS_VAST_ENDPOINT']}")
    print(f"   S3: {os.environ['TAMS_S3_ENDPOINT_URL']}")
    print(f"   Server: {os.environ['HOST']}:{os.environ['PORT']}")

# Set environment variables immediately when imported
setup_real_environment()

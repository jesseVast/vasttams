#!/usr/bin/env python3
"""
Simple script to test VAST database connection and get version information.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.vastdbmanager import VastDBManager
from app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_vast_connection():
    """Test VAST database connection and get version information."""
    
    try:
        # Get settings
        settings = get_settings()
        
        print("🔍 Testing VAST Database Connection")
        print("=" * 50)
        print(f"Endpoint: {settings.vast_endpoint}")
        print(f"Bucket: {settings.vast_bucket}")
        print(f"Schema: {settings.vast_schema}")
        print(f"Access Key: {settings.vast_access_key[:8]}...")
        print(f"Secret Key: {settings.vast_secret_key[:8]}...")
        print()
        
        # Initialize connection
        print("📡 Initializing VAST DB Manager...")
        db_manager = VastDBManager(
            endpoints=settings.vast_endpoint,
            auto_connect=True
        )
        print("✅ VAST DB Manager initialized successfully")
        
        # Test basic operations
        print("\n📊 Testing basic operations...")
        
        # List schemas
        try:
            schemas = db_manager.list_schemas()
            print(f"✅ Found schemas: {schemas}")
        except Exception as e:
            print(f"❌ Failed to list schemas: {e}")
        
        # List tables
        try:
            tables = db_manager.list_tables()
            print(f"✅ Found {len(tables)} tables: {tables}")
        except Exception as e:
            print(f"❌ Failed to list tables: {e}")
        
        # Get table stats for first table if exists
        if tables:
            try:
                first_table = tables[0]
                stats = db_manager.get_table_stats(first_table)
                print(f"✅ Table stats for {first_table}:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
            except Exception as e:
                print(f"❌ Failed to get table stats: {e}")
        
        # Test version information
        print("\n🔍 Getting version information...")
        try:
            # Try to get version from vastdb
            import vastdb
            print(f"✅ VAST DB Python client version: {vastdb.__version__}")
        except Exception as e:
            print(f"❌ Failed to get VAST DB client version: {e}")
        
        # Close connection
        print("\n🔒 Closing connection...")
        db_manager.close()
        print("✅ Connection closed successfully")
        
        print("\n🎉 Database connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if VAST database is running")
        print("2. Verify the endpoint URL is correct")
        print("3. Check network connectivity")
        print("4. Verify credentials are correct")
        print("5. Check if the bucket and schema exist")
        return False


def test_s3_connection():
    """Test S3 connection for flow segment storage."""
    
    try:
        from app.storage.s3_store import S3Store
        from app.core.config import get_settings
        
        settings = get_settings()
        
        print("\n🔍 Testing S3 Connection")
        print("=" * 30)
        print(f"Endpoint: {settings.s3_endpoint_url}")
        print(f"Bucket: {settings.s3_bucket_name}")
        print(f"Access Key: {settings.s3_access_key_id[:8]}...")
        print()
        
        # Initialize S3 store
        print("📡 Initializing S3 Store...")
        s3_store = S3Store(
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            bucket_name=settings.s3_bucket_name,
            use_ssl=settings.s3_use_ssl
        )
        print("✅ S3 Store initialized successfully")
        
        # Test bucket operations
        print("\n📊 Testing S3 operations...")
        
        # List objects (should work even if bucket is empty)
        try:
            objects = s3_store.list_objects()
            print(f"✅ Found {len(objects)} objects in bucket")
        except Exception as e:
            print(f"❌ Failed to list objects: {e}")
        
        print("✅ S3 connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ S3 connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if S3 service is running")
        print("2. Verify the endpoint URL is correct")
        print("3. Check network connectivity")
        print("4. Verify credentials are correct")
        print("5. Check if the bucket exists")
        return False


def main():
    """Main function to run all connection tests."""
    
    print("🚀 TAMS Database Connection Test")
    print("=" * 40)
    print()
    
    # Test VAST database connection
    vast_success = test_vast_connection()
    
    # Test S3 connection
    s3_success = test_s3_connection()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    print(f"VAST Database: {'✅ PASS' if vast_success else '❌ FAIL'}")
    print(f"S3 Storage: {'✅ PASS' if s3_success else '❌ FAIL'}")
    
    if vast_success and s3_success:
        print("\n🎉 All tests passed! Database connections are working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
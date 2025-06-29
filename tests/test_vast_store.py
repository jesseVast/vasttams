#!/usr/bin/env python3
"""
Test script for the new VAST store implementation using vastdbmanager
"""

import asyncio
import logging
from datetime import datetime
from app.vast_store import VASTStore
from app.models import Source, Tags, CollectionItem
from app.models import ContentFormat
from pydantic import UUID4
import uuid
from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_vast_store():
    """Test the VAST store implementation"""
    
    print("Testing VAST Store with vastdbmanager...")
    
    try:
        settings = get_settings()
        # Initialize VAST store
        store = VASTStore(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema
        )
        
        print("✓ VAST Store initialized successfully")
        
        # Test table listing
        tables = store.list_tables()
        print(f"✓ Tables in schema: {tables}")
        
        # Test schema listing
        schemas = store.list_schemas()
        print(f"✓ Schemas in bucket: {schemas}")
        
        # Test creating a source
        source = Source(
            id=uuid.uuid4(),
            format="urn:x-nmos:format:video",
            label="Test Camera",
            description="Test camera source",
            tags=Tags({"test": "true", "environment": "development"}),
            created_by="test_user",
            updated_by="test_user"
        )
        
        success = await store.create_source(source)
        if success:
            print("✓ Source created successfully")
        else:
            print("✗ Failed to create source")
            return
        
        # Test retrieving the source
        retrieved_source = await store.get_source(str(source.id))
        if retrieved_source:
            print(f"✓ Source retrieved: {retrieved_source.label}")
        else:
            print("✗ Failed to retrieve source")
        
        # Test listing sources
        sources = await store.list_sources(limit=10)
        print(f"✓ Listed {len(sources)} sources")
        
        # Test analytics
        analytics = await store.analytics_query("flow_usage")
        print(f"✓ Flow usage analytics: {analytics}")
        
        storage_analytics = await store.analytics_query("storage_usage")
        print(f"✓ Storage usage analytics: {storage_analytics}")
        
        catalog_summary = await store.analytics_query("catalog_summary")
        print(f"✓ Catalog summary: {catalog_summary}")
        
        # Test table stats
        for table_name in store.list_tables():
            stats = store.get_table_stats(table_name)
            print(f"✓ Table stats for {table_name}: {stats}")
        
        print("\n🎉 All tests passed! VAST store is working correctly.")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        logger.exception("Test failed")
    
    finally:
        # Cleanup
        if 'store' in locals():
            await store.close()
            print("✓ VAST store closed")

if __name__ == "__main__":
    asyncio.run(test_vast_store()) 
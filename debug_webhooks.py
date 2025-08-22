#!/usr/bin/env python3
"""
Debug script to test webhook functionality
"""

import asyncio
import json
from app.storage.vast_store import VASTStore
from app.models.models import WebhookPost
from app.core.config import get_settings

async def debug_webhooks():
    """Debug webhook creation and listing"""
    print("🔍 Starting webhook debug...")
    
    # Get settings
    settings = get_settings()
    print(f"Settings: {settings}")
    
    # Create store
    store = VASTStore(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket
    )
    
    try:
        # Test 1: List webhooks before creation
        print("\n📋 Test 1: Listing webhooks before creation...")
        webhooks_before = await store.list_webhooks()
        print(f"Webhooks before: {len(webhooks_before)}")
        for wh in webhooks_before:
            print(f"  - {wh.url}")
        
        # Test 2: Create a webhook
        print("\n➕ Test 2: Creating webhook...")
        webhook_data = WebhookPost(
            url="https://debug.example.com/webhook",
            api_key_name="Debug-API-Key",
            api_key_value="debug-secret",
            events=["flow.created"],
            owner_id="debug-owner",
            created_by="debug-creator"
        )
        
        print(f"Webhook data: {webhook_data.model_dump()}")
        
        # Create the webhook
        success = await store.create_webhook(webhook_data)
        print(f"Create result: {success}")
        
        # Test 3: List webhooks after creation
        print("\n📋 Test 3: Listing webhooks after creation...")
        webhooks_after = await store.list_webhooks()
        print(f"Webhooks after: {len(webhooks_after)}")
        for wh in webhooks_after:
            print(f"  - {wh.url}")
        
        # Test 4: Direct database query
        print("\n🔍 Test 4: Direct database query...")
        try:
            results = store.db_manager.select('webhooks')
            print(f"Direct query results: {results}")
            print(f"Results type: {type(results)}")
            if results:
                print(f"Results length: {len(results)}")
                if isinstance(results, dict):
                    print(f"Keys: {list(results.keys())}")
                    if 'url' in results:
                        print(f"URLs: {results['url']}")
        except Exception as e:
            print(f"Direct query error: {e}")
        
        # Test 5: Check if table exists
        print("\n📊 Test 5: Checking table existence...")
        try:
            # Try to get table info
            connection = store.db_manager.connection_manager.get_connection()
            bucket = store.db_manager.connection_manager.get_bucket()
            schema_name = store.db_manager.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                
                # Check if webhooks table exists
                try:
                    table = schema_obj.table('webhooks')
                    stats = table.get_stats()
                    print(f"Webhooks table exists with stats: {stats}")
                except Exception as table_e:
                    print(f"Webhooks table error: {table_e}")
                    
        except Exception as e:
            print(f"Table check error: {e}")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close the store
        store.close()

if __name__ == "__main__":
    asyncio.run(debug_webhooks())

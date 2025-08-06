#!/usr/bin/env python3
"""
Script to drop all existing tables and recreate them with the updated schema.
This is needed to add the new webhook ownership fields for TAMS API v6.0 compliance.
"""

import asyncio
import logging
from app.vast_store import VASTStore
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def drop_and_recreate_tables():
    """Drop all existing tables and recreate them with updated schema."""
    try:
        # Get settings
        settings = get_settings()
        
        # Create store instance
        store = VASTStore(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema,
            s3_endpoint_url=settings.s3_endpoint_url,
            s3_access_key_id=settings.s3_access_key_id,
            s3_secret_access_key=settings.s3_secret_access_key,
            s3_bucket_name=settings.s3_bucket_name,
            s3_use_ssl=settings.s3_use_ssl
        )
        
        logger.info("🔧 Starting table recreation process...")
        
        # List existing tables
        existing_tables = store.list_tables()
        logger.info(f"📋 Existing tables: {existing_tables}")
        
        # Drop all existing tables
        for table_name in existing_tables:
            try:
                logger.info(f"🗑️  Dropping table: {table_name}")
                store.db_manager.drop_table(table_name)
                logger.info(f"✅ Dropped table: {table_name}")
            except Exception as e:
                logger.warning(f"⚠️  Could not drop table {table_name}: {e}")
        
        # Recreate tables with updated schema
        logger.info("🔨 Recreating tables with updated schema...")
        store._setup_tams_tables()
        
        # Verify tables were created
        new_tables = store.list_tables()
        logger.info(f"📋 New tables: {new_tables}")
        
        # Verify webhook table has ownership fields
        try:
            webhook_schema = store.db_manager.get_table_schema('webhooks')
            logger.info(f"🔍 Webhook table schema: {webhook_schema}")
            
            # Check for ownership fields
            schema_fields = [field.name for field in webhook_schema]
            ownership_fields = ['owner_id', 'created_by']
            
            for field in ownership_fields:
                if field in schema_fields:
                    logger.info(f"✅ Ownership field '{field}' found in webhook table")
                else:
                    logger.error(f"❌ Ownership field '{field}' missing from webhook table")
                    
        except Exception as e:
            logger.error(f"❌ Could not verify webhook table schema: {e}")
        
        logger.info("🎉 Table recreation completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to recreate tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(drop_and_recreate_tables()) 
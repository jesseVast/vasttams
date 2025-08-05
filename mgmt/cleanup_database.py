#!/usr/bin/env python3
"""
Database cleanup script for TAMS API.

This script deletes all tables from the VAST database to allow for
a clean slate when recreating tables with updated schemas.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import get_settings
from app.vast_store import VASTStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def cleanup_database():
    """Delete all tables from the VAST database."""
    logger.info("🧹 Starting database cleanup...")
    
    settings = get_settings()
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
    
    try:
        # Get current tables
        tables = store.list_tables()
        logger.info(f"Found {len(tables)} tables: {tables}")
        
        if not tables:
            logger.info("✅ No tables found to delete")
            return True
        
        # Tables to delete (in order to handle dependencies)
        tables_to_delete = [
            'deletion_requests',  # Delete first (no dependencies)
            'webhooks',          # Delete first (no dependencies)
            'segments',          # Delete before flows (depends on flows)
            'objects',           # Delete before flows (may reference flows)
            'flows',             # Delete before sources (depends on sources)
            'sources'            # Delete last (base table)
        ]
        
        deleted_tables = []
        failed_tables = []
        
        for table_name in tables_to_delete:
            if table_name in tables:
                try:
                    logger.info(f"🗑️ Deleting table '{table_name}'...")
                    
                    # Delete the table
                    store.db_manager.drop_table(table_name)
                    
                    logger.info(f"✅ Successfully deleted table '{table_name}'")
                    deleted_tables.append(table_name)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to delete table '{table_name}': {e}")
                    failed_tables.append(table_name)
            else:
                logger.info(f"ℹ️ Table '{table_name}' not found, skipping")
        
        # Verify deletion
        remaining_tables = store.list_tables()
        logger.info(f"Remaining tables after cleanup: {remaining_tables}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 CLEANUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Tables found initially: {len(tables)}")
        logger.info(f"Tables successfully deleted: {len(deleted_tables)}")
        logger.info(f"Tables that failed to delete: {len(failed_tables)}")
        logger.info(f"Tables remaining: {len(remaining_tables)}")
        
        if deleted_tables:
            logger.info(f"✅ Successfully deleted: {deleted_tables}")
        
        if failed_tables:
            logger.error(f"❌ Failed to delete: {failed_tables}")
        
        if remaining_tables:
            logger.warning(f"⚠️ Tables still remaining: {remaining_tables}")
        else:
            logger.info("🎉 All tables successfully deleted!")
        
        return len(failed_tables) == 0 and len(remaining_tables) == 0
        
    except Exception as e:
        logger.error(f"❌ Database cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    logger.info("🚀 TAMS Database Cleanup Tool")
    logger.info("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("../app") or not os.path.exists("../tests"):
        logger.error("❌ Please run this script from the mgmt directory")
        return 1
    
    # Confirm before proceeding
    logger.warning("⚠️ WARNING: This will delete ALL tables from the VAST database!")
    logger.warning("⚠️ This action cannot be undone!")
    logger.warning("⚠️ All data will be permanently lost!")
    
    try:
        response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            logger.info("❌ Cleanup cancelled by user")
            return 0
    except KeyboardInterrupt:
        logger.info("\n❌ Cleanup cancelled by user")
        return 0
    
    logger.info("🔄 Proceeding with database cleanup...")
    
    try:
        success = await cleanup_database()
        if success:
            logger.info("\n✅ Database cleanup completed successfully!")
            logger.info("🎉 All tables have been deleted")
            return 0
        else:
            logger.error("\n❌ Database cleanup failed!")
            logger.error("⚠️ Some tables may still exist")
            return 1
    except Exception as e:
        logger.error(f"\n❌ Cleanup failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Cleanup interrupted by user")
        sys.exit(1) 
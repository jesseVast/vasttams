#!/usr/bin/env python3
"""
Final database cleanup script for TAMS API.

This script deletes all tables from the VAST database without recreating them.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import get_settings
from app.vastdbmanager import VastDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def cleanup_database():
    """Delete all tables from the VAST database."""
    logger.info("🧹 Starting final database cleanup...")
    
    settings = get_settings()
    
    # Use VastDBManager directly to avoid table recreation
    db_manager = VastDBManager(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema
    )
    
    try:
        # Get current tables
        tables = db_manager.list_tables()
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
                    db_manager.drop_table(table_name)
                    
                    logger.info(f"✅ Successfully deleted table '{table_name}'")
                    deleted_tables.append(table_name)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to delete table '{table_name}': {e}")
                    failed_tables.append(table_name)
            else:
                logger.info(f"ℹ️ Table '{table_name}' not found, skipping")
        
        # Verify deletion
        remaining_tables = db_manager.list_tables()
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
    finally:
        # Close the database connection
        db_manager.close()

async def main():
    """Main function."""
    logger.info("🚀 TAMS Final Database Cleanup Tool")
    logger.info("=" * 60)
    logger.warning("⚠️ This will delete ALL tables from the VAST database!")
    logger.warning("⚠️ All data will be permanently lost!")
    logger.warning("⚠️ Tables will NOT be recreated automatically!")
    
    try:
        success = await cleanup_database()
        if success:
            logger.info("\n✅ Database cleanup completed successfully!")
            logger.info("🎉 All tables have been deleted")
            logger.info("📝 Note: Tables will need to be recreated manually or via VASTStore initialization")
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
#!/usr/bin/env python3
"""
Simple database cleanup script for TAMS API.

This script deletes all tables from the VAST database using direct VAST connection.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import get_settings
import vastdb

# Configure logging
# Configure logging based on environment
env = os.getenv("ENVIRONMENT", "production")
log_level = logging.DEBUG if env == "development" else logging.INFO
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" if env == "production" else "%(asctime)s - %(levelname)s - %(message)s"

logging.basicConfig(level=log_level, format=log_format)
logger = logging.getLogger(__name__)

async def cleanup_database():
    """Delete all tables from the VAST database."""
    logger.info("🧹 Starting simple database cleanup...")
    
    settings = get_settings()
    
    logger.info("VAST Endpoint: %s", settings.vast_endpoint)
    logger.info("VAST Bucket: %s", settings.vast_bucket)
    logger.info("VAST Schema: %s", settings.vast_schema)
    
    try:
        # Connect to VAST directly
        logger.info("🔌 Connecting to VAST database...")
        connection = vastdb.connect(
            endpoint=settings.vast_endpoint,
            access=settings.vast_access_key,
            secret=settings.vast_secret_key,
            timeout=30
        )
        
        logger.info("✅ Connected to VAST database")
        
        # Get current tables
        with connection.transaction() as tx:
            bucket = tx.bucket(settings.vast_bucket)
            schema = bucket.schema(settings.vast_schema)
            
            # List existing tables
            tables = list(schema.tables())
            table_names = [t.name for t in tables]
            
            logger.info("Found %d tables: %s", len(table_names), table_names)
            
            if not table_names:
                logger.info("✅ No tables found to delete")
                return True
            
            # Tables to delete (in order to handle dependencies)
            tables_to_delete = [
                'deletion_requests',  # Delete first (no dependencies)
                'webhooks',          # Delete first (no dependencies)
                'segments',          # Delete before flows (depends on flows)
                'objects',           # Delete before flows (may reference flows)
                'flows',             # Delete before sources (depends on sources)
                'sources',           # Delete last (base table)
                'users',             # Auth tables
                'api_tokens',        # Auth tables
                'refresh_tokens',    # Auth tables
                'auth_logs',        # Auth tables
                'test_simple_table' # Test table
            ]
            
            deleted_tables = []
            failed_tables = []
            
            for table_name in tables_to_delete:
                if table_name in table_names:
                    try:
                        logger.info(f"🗑️ Deleting table '{table_name}'...")
                        
                        # Delete the table directly
                        table = schema.table(table_name)
                        table.drop()
                        
                        logger.info(f"✅ Successfully deleted table '{table_name}'")
                        deleted_tables.append(table_name)
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to delete table '{table_name}': {e}")
                        failed_tables.append(table_name)
                else:
                    logger.info(f"ℹ️ Table '{table_name}' not found, skipping")
            
            # Verify deletion
            remaining_tables = list(schema.tables())
            remaining_names = [t.name for t in remaining_tables]
            logger.info(f"Remaining tables after cleanup: {remaining_names}")
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("📊 CLEANUP SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Tables found initially: {len(table_names)}")
            logger.info(f"Tables successfully deleted: {len(deleted_tables)}")
            logger.info(f"Tables that failed to delete: {len(failed_tables)}")
            logger.info(f"Tables remaining: {len(remaining_names)}")
            
            if deleted_tables:
                logger.info(f"✅ Successfully deleted: {deleted_tables}")
            
            if failed_tables:
                logger.error(f"❌ Failed to delete: {failed_tables}")
            
            if remaining_names:
                logger.warning(f"⚠️ Tables still remaining: {remaining_names}")
            else:
                logger.info("🎉 All tables successfully deleted!")
            
            return len(failed_tables) == 0 and len(remaining_names) == 0
            
    except Exception as e:
        logger.error(f"❌ Database cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    logger.info("🚀 TAMS Simple Database Cleanup Tool")
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

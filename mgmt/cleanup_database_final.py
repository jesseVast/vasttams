#!/Users/jesse.thaloor/Developer/python/bbctams/bin/python
"""
Final database cleanup script for TAMS API.

This script deletes all tables from the VAST database without recreating them.
It follows the proper deletion order to handle table dependencies correctly.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Tuple

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import get_settings
from app.vastdbmanager import VastDBManager

# Constants
DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Table deletion order (handles dependencies)
# Tables are deleted in reverse dependency order
TABLES_DELETION_ORDER = [
    'deletion_requests',  # Delete first (no dependencies)
    'webhooks',          # Delete first (no dependencies)
    'segment_tags',      # Delete before segments (depends on segments)
    'segments',          # Delete before flows (depends on flows)
    'objects',           # Delete before flows (may reference flows)
    'flows',             # Delete before sources (depends on sources)
    'sources'            # Delete last (base table)
]

# Configure logging
logging.basicConfig(
    level=DEFAULT_LOG_LEVEL,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

async def cleanup_database() -> bool:
    """
    Delete all tables from the VAST database.
    
    This function deletes all TAMS tables in the correct order to handle
    dependencies. It uses VastDBManager directly to avoid table recreation.
    
    Returns:
        bool: True if cleanup was successful, False otherwise
        
    Raises:
        Exception: If database connection or cleanup fails
    """
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
        
        deleted_tables, failed_tables = await _delete_tables_in_order(
            db_manager, tables
        )
        
        # Verify deletion
        remaining_tables = db_manager.list_tables()
        logger.info(f"Remaining tables after cleanup: {remaining_tables}")
        
        # Generate summary
        success = _log_cleanup_summary(
            tables, deleted_tables, failed_tables, remaining_tables
        )
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Database cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Close the database connection
        db_manager.close()


async def _delete_tables_in_order(
    db_manager: VastDBManager, 
    existing_tables: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Delete tables in the correct dependency order.
    
    Args:
        db_manager: VastDBManager instance for database operations
        existing_tables: List of existing table names
        
    Returns:
        Tuple[List[str], List[str]]: (deleted_tables, failed_tables)
    """
    deleted_tables = []
    failed_tables = []
    
    for table_name in TABLES_DELETION_ORDER:
        if table_name in existing_tables:
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
    
    return deleted_tables, failed_tables


def _log_cleanup_summary(
    initial_tables: List[str],
    deleted_tables: List[str], 
    failed_tables: List[str],
    remaining_tables: List[str]
) -> bool:
    """
    Log the cleanup summary and return success status.
    
    Args:
        initial_tables: Tables found initially
        deleted_tables: Tables successfully deleted
        failed_tables: Tables that failed to delete
        remaining_tables: Tables remaining after cleanup
        
    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Tables found initially: {len(initial_tables)}")
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

async def main() -> int:
    """
    Main function to execute the database cleanup process.
    
    This function orchestrates the complete database cleanup process,
    including warnings, execution, and result reporting.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
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
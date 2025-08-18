#!/usr/bin/env python3
"""
Simple database cleanup script for TAMS API.

This script deletes all tables from the VAST database using direct VAST connection.
Requires manual confirmation or -y flag for safety.
"""

import asyncio
import logging
import sys
import os
import argparse
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import get_settings
import vastdb

# Configure logging
# Configure logging based on environment
env = os.getenv("ENVIRONMENT", "production")
log_level = logging.DEBUG if env == "development" else logging.INFO
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" if env == "production" else "%(asctime)s - %(levelname)s - %(message)s"

logging.basicConfig(level=log_level, format=log_format)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TAMS Database Cleanup Tool - Deletes ALL tables from VAST database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This script will delete ALL tables and data permanently!
⚠️  Use with extreme caution in production environments!

Examples:
  python cleanup_database.py                    # Interactive confirmation required
  python cleanup_database.py -y                 # Skip confirmation (dangerous!)
  python cleanup_database.py --yes              # Skip confirmation (dangerous!)
  python cleanup_database.py --help             # Show this help message
        """
    )
    
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompt (dangerous!)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting (safe)'
    )
    
    return parser.parse_args()

def get_user_confirmation():
    """Get manual confirmation from user."""
    print("\n" + "=" * 80)
    print("🚨 DANGEROUS OPERATION - DATABASE CLEANUP")
    print("=" * 80)
    print("⚠️  This script will:")
    print("   • Delete ALL tables from the VAST database")
    print("   • Permanently remove ALL data")
    print("   • NOT recreate tables automatically")
    print("   • Require manual table recreation")
    print()
    print("⚠️  This action is IRREVERSIBLE!")
    print("⚠️  All data will be PERMANENTLY LOST!")
    print()
    
    while True:
        response = input("Are you absolutely sure you want to continue? Type 'YES' to confirm: ").strip()
        if response == "YES":
            print("✅ Confirmation received. Proceeding with database cleanup...")
            return True
        elif response.lower() in ['no', 'n', 'cancel', 'abort', 'quit', 'exit']:
            print("❌ Cleanup cancelled by user.")
            return False
        else:
            print("❌ Invalid response. Please type 'YES' to confirm or 'no' to cancel.")

async def cleanup_database(dry_run=False):
    """Delete all tables from the VAST database."""
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No tables will actually be deleted")
    
    logger.info("🧹 Starting database cleanup...")
    
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
            
            # Get all tables dynamically and delete them
            # We'll try to delete all tables found in the schema
            tables_to_delete = table_names
            
            deleted_tables = []
            failed_tables = []
            
            for table_name in tables_to_delete:
                if table_name in table_names:
                    try:
                        if dry_run:
                            logger.info(f"🔍 [DRY RUN] Would delete table '{table_name}'")
                            deleted_tables.append(table_name)
                        else:
                            logger.info(f"🗑️ Deleting table '{table_name}'...")
                            
                            # Delete the table directly
                            table = schema.table(table_name)
                            table.drop()
                            
                            logger.info(f"✅ Successfully deleted table '{table_name}'")
                            deleted_tables.append(table_name)
                        
                    except Exception as e:
                        if dry_run:
                            logger.warning(f"🔍 [DRY RUN] Would fail to delete table '{table_name}': {e}")
                            failed_tables.append(table_name)
                        else:
                            logger.error(f"❌ Failed to delete table '{table_name}': {e}")
                            failed_tables.append(table_name)
                else:
                    logger.info(f"ℹ️ Table '{table_name}' not found, skipping")
            
            # Verify deletion
            if not dry_run:
                remaining_tables = list(schema.tables())
                remaining_names = [t.name for t in remaining_tables]
                logger.info(f"Remaining tables after cleanup: {remaining_names}")
            else:
                remaining_names = []
                logger.info("🔍 [DRY RUN] No actual deletion performed")
            
            # Summary
            logger.info("\n" + "=" * 60)
            if dry_run:
                logger.info("📊 DRY RUN SUMMARY - No tables were actually deleted")
            else:
                logger.info("📊 CLEANUP SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Tables found initially: {len(table_names)}")
            logger.info(f"Tables successfully deleted: {len(deleted_tables)}")
            logger.info(f"Tables that failed to delete: {len(failed_tables)}")
            logger.info(f"Tables remaining: {len(remaining_names)}")
            
            if deleted_tables:
                if dry_run:
                    logger.info(f"🔍 [DRY RUN] Would have deleted: {deleted_tables}")
                else:
                    logger.info(f"✅ Successfully deleted: {deleted_tables}")
            
            if failed_tables:
                if dry_run:
                    logger.warning(f"🔍 [DRY RUN] Would have failed to delete: {failed_tables}")
                else:
                    logger.error(f"❌ Failed to delete: {failed_tables}")
            
            if remaining_names:
                if dry_run:
                    logger.info(f"🔍 [DRY RUN] Tables would remain: {remaining_names}")
                else:
                    logger.warning(f"⚠️ Tables still remaining: {remaining_names}")
            else:
                if dry_run:
                    logger.info("🔍 [DRY RUN] All tables would be deleted!")
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
    args = parse_arguments()
    
    logger.info("🚀 TAMS Database Cleanup Tool")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE ENABLED - No tables will actually be deleted")
        logger.info("🔍 This is safe to run to see what would happen")
    else:
        logger.warning("⚠️ This will delete ALL tables from the VAST database!")
        logger.warning("⚠️ All data will be permanently lost!")
        logger.warning("⚠️ Tables will NOT be recreated automatically!")
        
        # Require confirmation unless -y flag is used
        if not args.yes:
            if not get_user_confirmation():
                return 1
        else:
            logger.warning("⚠️ Auto-confirmation enabled with -y flag")
            logger.warning("⚠️ Proceeding without manual confirmation...")
    
    try:
        success = await cleanup_database(dry_run=args.dry_run)
        if success:
            if args.dry_run:
                logger.info("\n🔍 [DRY RUN] Database cleanup simulation completed successfully!")
                logger.info("🔍 No actual changes were made to the database")
            else:
                logger.info("\n✅ Database cleanup completed successfully!")
                logger.info("🎉 All tables have been deleted")
                logger.info("📝 Note: Tables will need to be recreated manually or via VASTStore initialization")
            return 0
        else:
            if args.dry_run:
                logger.warning("\n🔍 [DRY RUN] Database cleanup simulation completed with warnings")
                logger.warning("🔍 Some tables would have failed to delete")
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

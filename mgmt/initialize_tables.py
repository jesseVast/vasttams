#!/usr/bin/env python3
"""
TAMS Table Initialization Script

This script initializes all TAMS database tables based on the Pydantic models.
It creates tables with proper schemas and projections for optimal performance.

Usage:
    python initialize_tables.py [--force] [--verify] [--info]

Options:
    --force     Force recreation of existing tables
    --verify    Only verify that tables exist (don't create)
    --info      Show detailed table information
"""

import sys
import os
import asyncio
import logging
import argparse
from pathlib import Path

# Add the src directory to the path so we can import vasttams modules
root_dir = os.path.abspath(str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(root_dir) / "src"))
sys.path.insert(0, root_dir)

# Change to root directory so config/config.json is found
os.chdir(root_dir)

from vasttams.core.config import get_settings
from vasttams.core.dependencies import get_vast_db
from vasttams.common.storage.table_initializer import TAMSTableInitializer

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def initialize_tables(force_recreate: bool = False):
    """Initialize all TAMS tables"""
    logger.info("🚀 Starting TAMS table initialization...")
    
    try:
        # Get database connection
        vast_db = get_vast_db()
        if not vast_db:
            logger.error("❌ Failed to get VAST database connection")
            return False
        
        # Create table initializer
        initializer = TAMSTableInitializer(vast_db)
        
        # Initialize all tables
        results = await initializer.initialize_all_tables(force_recreate=force_recreate)
        
        # Report results
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"📊 Initialization Results: {successful}/{total} tables successful")
        
        if successful == total:
            logger.info("🎉 All TAMS tables initialized successfully!")
            return True
        else:
            failed_tables = [name for name, success in results.items() if not success]
            logger.error(f"❌ Failed tables: {failed_tables}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Critical error during table initialization: {e}")
        return False


async def verify_tables():
    """Verify that all required tables exist"""
    logger.info("🔍 Verifying TAMS tables...")
    
    try:
        # Get database connection
        vast_db = get_vast_db()
        if not vast_db:
            logger.error("❌ Failed to get VAST database connection")
            return False
        
        # Create table initializer
        initializer = TAMSTableInitializer(vast_db)
        
        # Verify tables
        results = await initializer.verify_tables_exist()
        
        # Report results
        existing = sum(1 for exists in results.values() if exists)
        total = len(results)
        
        logger.info(f"📊 Verification Results: {existing}/{total} tables exist")
        
        if existing == total:
            logger.info("✅ All required TAMS tables exist!")
            return True
        else:
            missing_tables = [name for name, exists in results.items() if not exists]
            logger.warning(f"⚠️ Missing tables: {missing_tables}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Error during table verification: {e}")
        return False


async def show_table_info():
    """Show detailed information about all tables"""
    logger.info("📋 Getting TAMS table information...")
    
    try:
        # Get database connection
        vast_db = get_vast_db()
        if not vast_db:
            logger.error("❌ Failed to get VAST database connection")
            return False
        
        # Create table initializer
        initializer = TAMSTableInitializer(vast_db)
        
        # Get table info
        table_info = await initializer.get_table_info()
        
        # Display information
        logger.info("=" * 80)
        logger.info("TAMS TABLE INFORMATION")
        logger.info("=" * 80)
        
        for table_name, info in table_info.items():
            logger.info(f"\n📊 Table: {table_name}")
            logger.info("-" * 40)
            
            if info.get("exists", False):
                stats = info.get("stats", {})
                projections = info.get("projections", [])
                schema_fields = info.get("schema_fields", 0)
                
                logger.info(f"  Status: ✅ EXISTS")
                logger.info(f"  Schema Fields: {schema_fields}")
                logger.info(f"  Total Rows: {stats.get('total_rows', 'Unknown')}")
                logger.info(f"  Projections: {len(projections)}")
                
                if projections:
                    for proj in projections:
                        logger.info(f"    - {proj}")
                else:
                    logger.info("    - None")
            else:
                error = info.get("error", "Unknown error")
                logger.info(f"  Status: ❌ MISSING")
                logger.info(f"  Error: {error}")
        
        logger.info("\n" + "=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"💥 Error getting table information: {e}")
        return False


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="TAMS Table Initialization Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python initialize_tables.py                    # Initialize tables (default)
  python initialize_tables.py --force           # Force recreation of existing tables
  python initialize_tables.py --verify          # Only verify tables exist
  python initialize_tables.py --info            # Show detailed table information
        """
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recreation of existing tables (WARNING: This will delete existing data!)'
    )
    
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Only verify that tables exist (don\'t create)'
    )
    
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show detailed table information'
    )
    
    return parser.parse_args()


async def main():
    """Main function"""
    args = parse_arguments()
    
    # Show configuration
    settings = get_settings()
    logger.info("🔧 Configuration:")
    logger.info(f"  VAST Endpoint: {settings.vast_endpoint}")
    logger.info(f"  VAST Bucket: {settings.vast_bucket}")
    logger.info(f"  VAST Schema: {settings.vast_schema}")
    logger.info(f"  Enable Projections: {settings.enable_table_projections}")
    logger.info("")
    
    try:
        if args.info:
            success = await show_table_info()
        elif args.verify:
            success = await verify_tables()
        else:
            if args.force:
                logger.warning("⚠️ FORCE MODE: Existing tables will be recreated!")
                logger.warning("⚠️ This will DELETE existing data!")
            
            success = await initialize_tables(force_recreate=args.force)
        
        if success:
            logger.info("✅ Operation completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Operation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

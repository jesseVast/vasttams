#!/usr/bin/env python3
"""
Table Projections Management Script for TAMS

This script creates and manages table projections for improved query performance.
Projections are automatically created based on the configuration in src/vasttams/core/config.py.

NOTE: This script is deprecated as projections are now managed automatically.
For TAMS 8.0, projections should be defined in the schema modules and created
automatically during table initialization.

Usage:
    python create_table_projections.py [--status]

Options:
    --status     Show current projection status
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import vasttams modules
root_dir = os.path.abspath(str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(root_dir) / "src" / "server"))
sys.path.insert(0, root_dir)

# Change to root directory so config/config.yaml is found
# In container, config is at /etc/tams/config.yaml, in dev it's at config/config.yaml
# The Settings class handles this automatically
os.chdir(root_dir)

from vasttamsserver.core.config import get_settings
from vasttamsserver.common.storage.schemas import get_table_projections
from vastdbmanager import VastDBManager
from vastdbmanager.model import VastDBManagerConfig
from vastdbmanager.core import VastDBConnectionConfig
from vastdbmanager.trino import TrinoConfig

import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_vast_db():
    """Get configured VastDBManager instance"""
    try:
        settings = get_settings()
        
        # Build VastDBConnectionConfig
        vector_support = bool(settings.vast_vector_endpoint)
        vastdb_config = VastDBConnectionConfig(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema,
            vector_support=vector_support
        )
        
        # Build TrinoConfig if Trino is enabled
        trino_config = None
        if settings.vaststore_enable_trino:
            trino_config = TrinoConfig(
                host=settings.trino_host,
                port=settings.trino_port,
                user=settings.trino_user,
                catalog=settings.trino_catalog,
                bucket=settings.vast_bucket,
                schema=settings.vast_schema
            )
        
        # Build VastDBManagerConfig
        manager_config = VastDBManagerConfig(
            vastdb_config=vastdb_config,
            trino_config=trino_config,
            enable_trino=settings.vaststore_enable_trino,
            auto_connect=True
        )
        
        db_manager = VastDBManager(manager_config)
        return db_manager
    except Exception as e:
        logger.error("Failed to create VastDBManager: %s", e)
        return None

def show_status():
    """Show current projection status for all tables"""
    logger.info("DEPRECATED: Table projections are now managed automatically")
    logger.info("This script is kept for informational purposes only")
    logger.info("")
    
    db_manager = get_vast_db()
    if not db_manager:
        logger.error("No VastDBManager available")
        return False
    
    try:
        settings = get_settings()
        logger.info("Table Projections Status")
        logger.info("=" * 50)
        logger.info("Configuration: ENABLE_TABLE_PROJECTIONS = %s", settings.enable_table_projections)
        logger.info("")
        
        # Get projection definitions from schemas
        table_projections = get_table_projections()
        
        for table_name in table_projections.keys():
            try:
                existing_projections = db_manager.get_table_projections(table_name)
                logger.info("Table: %s", table_name)
                if existing_projections:
                    for proj in existing_projections:
                        logger.info("  ✅ %s", proj)
                else:
                    logger.info("  ❌ No projections")
                logger.info("")
            except Exception as e:
                logger.error("Failed to get projections for table %s: %s", table_name, e)
        
        return True
        
    except Exception as e:
        logger.error("Failed to get projection status: %s", e)
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Show table projection status (DEPRECATED - projections are automatic)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_table_projections.py --status          # Show current status

Note: Projections are now created automatically during table initialization.
This script is kept for informational purposes only.
        """
    )
    
    parser.add_argument(
        '--status', 
        action='store_true', 
        help='Show current projection status'
    )
    
    args = parser.parse_args()
    
    if args.status:
        success = show_status()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        logger.warning("NOTE: This script is deprecated. Projections are now automatic.")
        sys.exit(0)

if __name__ == "__main__":
    main()

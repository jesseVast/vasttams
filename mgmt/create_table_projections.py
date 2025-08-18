#!/usr/bin/env python3
"""
Table Projections Management Script for TAMS

This script creates and manages table projections for improved query performance.
Projections are automatically created based on the configuration in app/core/config.py.

Usage:
    python create_table_projections.py [--enable] [--disable] [--status] [--force]

Options:
    --enable     Enable table projections (default)
    --disable    Disable table projections
    --status     Show current projection status
    --force      Force recreation of existing projections
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.storage.vast_store import VASTStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Projection definitions based on TODO list
TABLE_PROJECTIONS = {
    'sources': [
        ('id',),  # Primary key projection
    ],
    'flows': [
        ('id',),  # Primary key projection
        ('id', 'source_id'),  # Composite key for source-based queries
        ('id', 'start_time', 'end_time'),  # Time range projection
    ],
    'segments': [
        ('id',),  # Primary key projection
        ('id', 'flow_id'),  # Composite projection for flow-based queries
        ('id', 'flow_id', 'object_id'),  # Composite key for segment queries
        ('id', 'object_id'),  # Composite projection for object-based queries
        ('id', 'start_time', 'end_time'),  # Time range projection
    ],
    'objects': [
        ('id',),  # Primary key projection
    ],
    'flow_object_references': [
        ('object_id',),  # Primary key projection
        ('object_id', 'flow_id'),  # Composite key for object-flow queries
        ('flow_id', 'object_id'),  # Composite key for flow-object queries
    ]
}

def get_vast_store():
    """Get configured VAST store instance"""
    try:
        settings = get_settings()
        store = VASTStore(
            endpoint=settings.vast_endpoint,
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema
        )
        return store
    except Exception as e:
        logger.error("Failed to create VAST store: %s", e)
        return None

def create_projections(store, force=False):
    """Create table projections for improved query performance"""
    if not store:
        logger.error("No VAST store available")
        return False
    
    try:
        # Check if projections are enabled in config
        settings = get_settings()
        if not settings.enable_table_projections:
            logger.warning("Table projections are disabled in configuration. Set ENABLE_TABLE_PROJECTIONS=true to enable.")
            return False
        
        logger.info("Creating table projections for improved query performance...")
        
        success_count = 0
        total_count = 0
        
        for table_name, projections in TABLE_PROJECTIONS.items():
            logger.info("Processing table: %s", table_name)
            
            for i, projection_columns in enumerate(projections):
                total_count += 1
                projection_name = f"{table_name}_{'_'.join(projection_columns)}_proj"
                
                try:
                    # Check if projection already exists
                    existing_projections = store.db_manager.get_table_projections(table_name)
                    
                    if projection_name in existing_projections:
                        if force:
                            logger.info("Recreating existing projection: %s", projection_name)
                            # Note: VAST doesn't support dropping projections, so we'll skip
                            logger.warning("Cannot drop existing projection %s (VAST limitation)", projection_name)
                            continue
                        else:
                            logger.info("Projection %s already exists, skipping", projection_name)
                            success_count += 1
                            continue
                    
                    # Create the projection
                    logger.info("Creating projection %s with columns: %s", projection_name, projection_columns)
                    store.db_manager.add_projection(table_name, projection_name, list(projection_columns))
                    success_count += 1
                    logger.info("Successfully created projection: %s", projection_name)
                    
                except Exception as e:
                    logger.error("Failed to create projection %s: %s", projection_name, e)
                    continue
        
        logger.info("Projection creation complete: %d/%d successful", success_count, total_count)
        return success_count > 0
        
    except Exception as e:
        logger.error("Failed to create projections: %s", e)
        return False

def disable_projections(store):
    """Disable table projections by dropping existing projections"""
    if not store:
        logger.error("No VAST store available")
        return False
    
    try:
        logger.info("Disabling table projections by dropping existing projections...")
        
        success_count = 0
        total_count = 0
        
        for table_name in TABLE_PROJECTIONS.keys():
            try:
                existing_projections = store.db_manager.get_table_projections(table_name)
                if existing_projections:
                    logger.info("Table: %s - Found %d projections to drop", table_name, len(existing_projections))
                    
                    for proj_name in existing_projections:
                        total_count += 1
                        try:
                            # Get the projection object and drop it
                            logger.info("Dropping projection: %s", proj_name)
                            store.db_manager.drop_projection(table_name, proj_name)
                            success_count += 1
                            logger.info("Successfully dropped projection: %s", proj_name)
                        except Exception as e:
                            logger.error("Failed to drop projection %s: %s", proj_name, e)
                            continue
                else:
                    logger.info("Table: %s - No projections to drop", table_name)
                    
            except Exception as e:
                logger.error("Failed to get projections for table %s: %s", table_name, e)
                continue
        
        logger.info("Projection disabling complete: %d/%d projections dropped", success_count, total_count)
        
        if success_count > 0:
            logger.info("Projections have been disabled. Set ENABLE_TABLE_PROJECTIONS=false in configuration to prevent new projections from being created.")
        else:
            logger.info("No projections were found to drop.")
        
        return True
        
    except Exception as e:
        logger.error("Failed to disable projections: %s", e)
        return False

def show_status(store):
    """Show current projection status for all tables"""
    if not store:
        logger.error("No VAST store available")
        return False
    
    try:
        settings = get_settings()
        logger.info("Table Projections Status")
        logger.info("=" * 50)
        logger.info("Configuration: ENABLE_TABLE_PROJECTIONS = %s", settings.enable_table_projections)
        logger.info("")
        
        for table_name in TABLE_PROJECTIONS.keys():
            try:
                existing_projections = store.db_manager.get_table_projections(table_name)
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
        description="Manage table projections for TAMS database performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_table_projections.py                    # Create projections (default)
  python create_table_projections.py --enable          # Enable and create projections
  python create_table_projections.py --disable         # Disable projections
  python create_table_projections.py --status          # Show current status
  python create_table_projections.py --force           # Force recreation of projections
        """
    )
    
    parser.add_argument(
        '--enable', 
        action='store_true', 
        help='Enable table projections (default)'
    )
    parser.add_argument(
        '--disable', 
        action='store_true', 
        help='Disable table projections'
    )
    parser.add_argument(
        '--status', 
        action='store_true', 
        help='Show current projection status'
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Force recreation of existing projections'
    )
    
    args = parser.parse_args()
    
    # Default action is to enable projections
    if not any([args.enable, args.disable, args.status]):
        args.enable = True
    
    # Get VAST store
    store = get_vast_store()
    if not store:
        sys.exit(1)
    
    try:
        if args.status:
            success = show_status(store)
        elif args.disable:
            success = disable_projections(store)
        else:  # enable (default)
            success = create_projections(store, force=args.force)
        
        if success:
            logger.info("Operation completed successfully")
            sys.exit(0)
        else:
            logger.error("Operation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()

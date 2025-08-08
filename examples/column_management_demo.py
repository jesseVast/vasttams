#!/usr/bin/env python3
"""
Column Management Demo

This script demonstrates practical usage of the column management methods
for VAST Database tables in the TAMS system.

Example scenarios:
1. Adding new columns to existing tables
2. Renaming columns for better naming conventions
3. Dropping unused columns
4. Schema evolution for TAMS tables
"""

import logging
import sys
import os
import pyarrow as pa
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.storage.vast_store import VASTStore
from app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_column_management():
    """Demonstrate column management operations on TAMS tables."""
    logger.info("Starting Column Management Demo")
    
    # Get settings
    settings = get_settings()
    
    # Create VAST store instance
    store = VASTStore(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema
    )
    
    try:
        # Demo 1: List existing tables and their columns
        logger.info("\n" + "="*60)
        logger.info("DEMO 1: List existing tables and columns")
        logger.info("="*60)
        
        tables = store.list_tables()
        logger.info(f"Available tables: {tables}")
        
        for table_name in tables[:3]:  # Show first 3 tables
            columns = store.list_table_columns(table_name)
            logger.info(f"Table '{table_name}' columns: {columns}")
        
        # Demo 2: Add new columns to an existing table
        logger.info("\n" + "="*60)
        logger.info("DEMO 2: Add new columns to existing table")
        logger.info("="*60)
        
        if 'sources' in tables:
            table_name = 'sources'
            logger.info(f"Adding new columns to '{table_name}' table")
            
            # Show current columns
            current_columns = store.list_table_columns(table_name)
            logger.info(f"Current columns: {current_columns}")
            
            # Add new columns for enhanced metadata
            new_columns = pa.schema([
                ('location', pa.string()),           # Geographic location
                ('device_type', pa.string()),        # Type of device
                ('last_maintenance', pa.timestamp('us')),  # Last maintenance date
                ('health_status', pa.string())       # Device health status
            ])
            
            success = store.add_columns(table_name, new_columns)
            if success:
                logger.info("✓ Successfully added new columns")
                
                # Show updated columns
                updated_columns = store.list_table_columns(table_name)
                logger.info(f"Updated columns: {updated_columns}")
            else:
                logger.warning("⚠ Failed to add columns (they might already exist)")
        
        # Demo 3: Rename columns for better naming conventions
        logger.info("\n" + "="*60)
        logger.info("DEMO 3: Rename columns for better naming")
        logger.info("="*60)
        
        if 'flows' in tables:
            table_name = 'flows'
            logger.info(f"Renaming columns in '{table_name}' table")
            
            # Check if we have columns to rename
            columns = store.list_table_columns(table_name)
            logger.info(f"Current columns: {columns}")
            
            # Example: Rename 'frame_width' to 'width' if it exists
            if 'frame_width' in columns:
                success = store.rename_column(table_name, 'frame_width', 'width')
                if success:
                    logger.info("✓ Successfully renamed 'frame_width' to 'width'")
                else:
                    logger.warning("⚠ Failed to rename column")
            
            # Example: Rename 'frame_height' to 'height' if it exists
            if 'frame_height' in columns:
                success = store.rename_column(table_name, 'frame_height', 'height')
                if success:
                    logger.info("✓ Successfully renamed 'frame_height' to 'height'")
                else:
                    logger.warning("⚠ Failed to rename column")
        
        # Demo 4: Get detailed column information
        logger.info("\n" + "="*60)
        logger.info("DEMO 4: Get detailed column information")
        logger.info("="*60)
        
        if 'segments' in tables:
            table_name = 'segments'
            logger.info(f"Getting column details for '{table_name}' table")
            
            columns = store.list_table_columns(table_name)
            for column_name in columns[:5]:  # Show first 5 columns
                column_info = store.get_column_info(table_name, column_name)
                if column_info:
                    logger.info(f"Column '{column_name}': {column_info}")
        
        # Demo 5: Schema evolution example
        logger.info("\n" + "="*60)
        logger.info("DEMO 5: Schema evolution example")
        logger.info("="*60)
        
        logger.info("Example: Adding analytics columns to segments table")
        
        if 'segments' in tables:
            table_name = 'segments'
            
            # Add analytics-related columns
            analytics_columns = pa.schema([
                ('access_count', pa.int32()),        # Number of times accessed
                ('last_accessed', pa.timestamp('us')),  # Last access time
                ('compression_ratio', pa.float64()), # Data compression ratio
                ('storage_tier', pa.string())        # Storage tier (hot/cold)
            ])
            
            success = store.add_columns(table_name, analytics_columns)
            if success:
                logger.info("✓ Added analytics columns for better performance tracking")
                
                # Show the new columns
                updated_columns = store.list_table_columns(table_name)
                new_columns = [col for col in updated_columns if col in ['access_count', 'last_accessed', 'compression_ratio', 'storage_tier']]
                logger.info(f"New analytics columns: {new_columns}")
            else:
                logger.info("ℹ Analytics columns might already exist")
        
        logger.info("\n" + "="*60)
        logger.info("Column Management Demo Completed Successfully!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        # Cleanup
        try:
            store.close()
            logger.info("✓ Closed VAST store connection")
        except Exception as e:
            logger.warning(f"⚠ Connection close error: {e}")


def demo_schema_migration():
    """Demonstrate a complete schema migration scenario."""
    logger.info("\n" + "="*60)
    logger.info("SCHEMA MIGRATION DEMO")
    logger.info("="*60)
    
    # Get settings
    settings = get_settings()
    
    # Create VAST store instance
    store = VASTStore(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema
    )
    
    try:
        logger.info("Example: Migrating from v1.0 to v2.0 schema")
        
        # Step 1: Add new columns for v2.0 features
        logger.info("Step 1: Adding v2.0 columns")
        
        if 'flows' in store.list_tables():
            v2_columns = pa.schema([
                ('version', pa.string()),           # Schema version
                ('compatibility_mode', pa.bool_()), # Backward compatibility flag
                ('encryption_enabled', pa.bool_()), # Encryption status
                ('replication_factor', pa.int32())  # Replication factor
            ])
            
            success = store.add_columns('flows', v2_columns)
            if success:
                logger.info("✓ Added v2.0 columns to flows table")
        
        # Step 2: Rename deprecated columns
        logger.info("Step 2: Renaming deprecated columns")
        
        # Example: Rename old column names to new ones
        rename_mappings = [
            ('old_column_name', 'new_column_name'),
            ('deprecated_field', 'current_field')
        ]
        
        for old_name, new_name in rename_mappings:
            if store.column_exists('flows', old_name):
                success = store.rename_column('flows', old_name, new_name)
                if success:
                    logger.info(f"✓ Renamed '{old_name}' to '{new_name}'")
        
        # Step 3: Drop obsolete columns
        logger.info("Step 3: Dropping obsolete columns")
        
        obsolete_columns = ['legacy_field', 'unused_column']
        
        for column_name in obsolete_columns:
            if store.column_exists('flows', column_name):
                drop_schema = pa.schema([(column_name, pa.string())])  # Type doesn't matter for drop
                success = store.drop_column('flows', drop_schema)
                if success:
                    logger.info(f"✓ Dropped obsolete column '{column_name}'")
        
        logger.info("✓ Schema migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Schema migration demo failed: {e}")
        raise
    finally:
        try:
            store.close()
        except Exception as e:
            logger.warning(f"⚠ Connection close error: {e}")


def main():
    """Main function to run the demos."""
    logger.info("VAST Database Column Management Demo")
    logger.info("This demo shows practical usage of column management methods")
    
    try:
        # Run basic column management demo
        demo_column_management()
        
        # Run schema migration demo
        demo_schema_migration()
        
        logger.info("\n🎉 All demos completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

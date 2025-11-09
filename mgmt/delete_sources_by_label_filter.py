#!/usr/bin/env python3
"""
Delete sources where label does not start with a specified prefix (cascade delete)

This script will:
1. Get all sources
2. Filter sources where label doesn't start with the specified prefix (or is null/empty)
3. Cascade delete each source (which will also delete dependent flows and segments)

Usage:
    python delete_sources_by_label_filter.py <label_prefix>
    
Example:
    python delete_sources_by_label_filter.py "Test"
    python delete_sources_by_label_filter.py "Production"
"""

import sys
import os
import asyncio
import json
import argparse
from pathlib import Path

# Add the src directory to the path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(root_dir, 'src', 'server'))
sys.path.insert(0, root_dir)

# Change to root directory so config/config.json is found
# In container, config is at /etc/tams/config.json, in dev it's at config/config.json
# The Settings class handles this automatically
os.chdir(root_dir)

from vasttamsserver.core.dependencies import get_vast_db, get_s3_client
from vasttamsserver.core.config import get_settings
from vasttamsserver.common.storage.main_service import TAMSStorageService
import logging

# Logging is already initialized at startup (via simple_logging module import)
logger = logging.getLogger(__name__)

async def delete_sources_by_label_filter(label_prefix: str, negate: bool = False):
    """Delete sources based on label prefix filter
    
    Args:
        label_prefix: Label prefix to filter by
        negate: If True, delete sources that DON'T start with prefix (all except X). If False, delete sources that START with prefix.
    """
    try:
        # Initialize services
        settings = get_settings()
        vast_db = get_vast_db()
        s3_client = get_s3_client()
        storage_service = TAMSStorageService(vast_db, s3_client)
        
        # Get all sources
        filter_desc = "NOT starting with (all except)" if negate else "starting with"
        logger.info(f"Fetching all sources (filtering by label prefix: '{label_prefix}', negate={negate})...")
        print(f"Fetching all sources (filtering: label {filter_desc} '{label_prefix}')...")
        from vasttamsserver.common.filters import SourceFilters
        filters = SourceFilters()
        sources = await storage_service.get_sources(filters)
        
        logger.info(f"Found {len(sources)} total sources")
        print(f"Found {len(sources)} total sources")
        
        # Filter sources based on negate flag
        sources_to_delete = []
        sources_to_keep = []
        for source in sources:
            label = source.label or ""
            matches = label.startswith(label_prefix)
            
            if negate:
                # Negate mode: delete sources that DON'T start with prefix (all except X)
                if matches:
                    sources_to_keep.append(source)
                else:
                    sources_to_delete.append(source)
            else:
                # Normal mode: delete sources that START with prefix
                if matches:
                    sources_to_delete.append(source)
                else:
                    sources_to_keep.append(source)
        
        filter_desc_delete = f"label doesn't start with '{label_prefix}' (all except)" if negate else f"label starts with '{label_prefix}'"
        filter_desc_keep = f"label starts with '{label_prefix}'" if negate else f"label doesn't start with '{label_prefix}'"
        
        logger.info(f"Found {len(sources_to_delete)} sources to delete ({filter_desc_delete})")
        logger.info(f"Will keep {len(sources_to_keep)} sources ({filter_desc_keep})")
        print(f"\nFound {len(sources_to_delete)} sources to delete ({filter_desc_delete})")
        print(f"Will keep {len(sources_to_keep)} sources ({filter_desc_keep})")
        
        if not sources_to_delete:
            logger.info("No sources to delete. Exiting.")
            print("\nNo sources to delete. Exiting.")
            return
        
        # Show preview
        print("\nSources to be deleted:")
        for i, source in enumerate(sources_to_delete[:10], 1):
            print(f"  {i}. {source.id} - label: '{source.label or '(no label)'}'")
        if len(sources_to_delete) > 10:
            print(f"  ... and {len(sources_to_delete) - 10} more")
        
        # Confirm deletion
        filter_desc = f"label doesn't start with '{label_prefix}' (all except)" if negate else f"label starts with '{label_prefix}'"
        print(f"\n⚠️  WARNING: This will cascade delete {len(sources_to_delete)} sources")
        print(f"   ({filter_desc})")
        print("   (including all their flows and segments)")
        response = input("\nType 'yes' to confirm deletion: ")
        
        if response.lower() != 'yes':
            print("Deletion cancelled.")
            return
        
        # Delete sources with cascade
        print(f"\nDeleting {len(sources_to_delete)} sources...")
        deleted_count = 0
        failed_count = 0
        
        for i, source in enumerate(sources_to_delete, 1):
            try:
                logger.info(f"[{i}/{len(sources_to_delete)}] Deleting source {source.id} (label: '{source.label or '(no label)'}')")
                print(f"[{i}/{len(sources_to_delete)}] Deleting source {source.id} (label: '{source.label or '(no label)'}')...", end=" ")
                success = await storage_service.delete_source(source.id, cascade=True)
                if success:
                    logger.info(f"Successfully deleted source {source.id}")
                    print("✓")
                    deleted_count += 1
                else:
                    logger.warning(f"Source {source.id} not found for deletion")
                    print("✗ (not found)")
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to delete source {source.id}: {e}", exc_info=True)
                print(f"✗ Error: {e}")
                failed_count += 1
        
        filter_desc_keep = f"label starts with '{label_prefix}'" if negate else f"label doesn't start with '{label_prefix}'"
        logger.info(f"Deletion complete! Deleted: {deleted_count}, Failed: {failed_count}, Kept: {len(sources_to_keep)}")
        print(f"\n✅ Deletion complete!")
        print(f"   Deleted: {deleted_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Kept: {len(sources_to_keep)} ({filter_desc_keep})")
        
    except Exception as e:
        logger.error(f"Script error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Delete sources by label prefix filter (cascade delete)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete all sources starting with "Test" (default behavior)
  %(prog)s "Test"
  
  # Delete all sources NOT starting with "Test" (all except "Test", using --negate)
  %(prog)s "Test" --negate
  
  # Delete all sources NOT starting with "Production" (all except "Production")
  %(prog)s "Production" --negate
  
  # Delete all sources starting with "Temp"
  %(prog)s "Temp"
        """
    )
    parser.add_argument(
        "label_prefix",
        type=str,
        help="Label prefix to filter by"
    )
    parser.add_argument(
        "-n", "--negate",
        action="store_true",
        help="Negate the filter: delete all sources EXCEPT those starting with prefix (all except X)"
    )
    
    args = parser.parse_args()
    
    if not args.label_prefix:
        print("Error: label_prefix argument is required", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    asyncio.run(delete_sources_by_label_filter(args.label_prefix, args.negate))


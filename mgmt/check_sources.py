#!/usr/bin/env python3
"""
Simple script to check sources table directly.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

async def check_sources():
    """Check sources table directly."""
    try:
        from app.storage.vastdbmanager.core import VastDBManager
        from app.core.config import get_settings
        
        settings = get_settings()
        db_manager = VastDBManager(endpoints=settings.vast_endpoint, auto_connect=True)
        
        print('🔍 Directly querying sources table:')
        
        # Try to get actual source records
        try:
            sources_data = db_manager.query_with_predicates('sources')
            if sources_data:
                print(f'✅ Found sources data:')
                print(f'   Data type: {type(sources_data)}')
                print(f'   Keys: {list(sources_data.keys()) if isinstance(sources_data, dict) else "Not a dict"}')
                if isinstance(sources_data, dict):
                    for key, value in sources_data.items():
                        if key != '$row_id':  # Skip internal row IDs
                            print(f'   {key}: {len(value) if hasattr(value, "__len__") else "No length"} values')
                            if hasattr(value, "__len__") and len(value) > 0:
                                print(f'     First few values: {value[:3]}')
            else:
                print('❌ No sources data returned')
        except Exception as e:
            print(f'❌ Error querying sources: {e}')
        
        # Also check table stats for comparison
        print('\n📊 Table stats (for comparison):')
        try:
            stats = db_manager.get_table_stats('sources')
            print(f'   Total rows reported: {stats.get("total_rows", 0)}')
        except Exception as e:
            print(f'   Error getting stats: {e}')
        
        db_manager.close()
        
    except Exception as e:
        print(f'❌ Failed to check sources: {e}')

if __name__ == "__main__":
    asyncio.run(check_sources())

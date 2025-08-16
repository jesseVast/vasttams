#!/usr/bin/env python3
"""
Debug script to test source retrieval step by step.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

async def debug_sources():
    """Debug source retrieval step by step."""
    try:
        from app.storage.vast_store import VASTStore
        from app.core.config import get_settings
        
        settings = get_settings()
        store = VASTStore()
        
        print('🔍 Debugging source retrieval step by step:')
        
        # Test 1: Check if we can create ibis predicates
        print('\n1. Testing ibis predicate creation:')
        try:
            from ibis import _
            print('   ✅ Ibis import successful')
            
            # Test basic predicate
            predicate = (_.id == "550e8400-e29b-41d4-a716-446655440000")
            print(f'   ✅ Created predicate: {predicate}')
            print(f'   ✅ Predicate type: {type(predicate)}')
            
        except Exception as e:
            print(f'   ❌ Ibis predicate creation failed: {e}')
            return
        
        # Test 2: Test soft delete predicate
        print('\n2. Testing soft delete predicate:')
        try:
            soft_delete_predicate = store._add_soft_delete_predicate(predicate)
            print(f'   ✅ Soft delete predicate: {soft_delete_predicate}')
            print(f'   ✅ Combined predicate type: {type(soft_delete_predicate)}')
        except Exception as e:
            print(f'   ❌ Soft delete predicate failed: {e}')
            return
        
        # Test 3: Test database query directly
        print('\n3. Testing database query:')
        try:
            results = store.db_manager.select('sources', predicate=soft_delete_predicate, output_by_row=True)
            print(f'   ✅ Query results: {results}')
            print(f'   ✅ Results type: {type(results)}')
            if results:
                if isinstance(results, list):
                    print(f'   ✅ Found {len(results)} results')
                elif isinstance(results, dict):
                    print(f'   ✅ Found {len(results)} columns')
            else:
                print('   ⚠️  No results returned')
        except Exception as e:
            print(f'   ❌ Database query failed: {e}')
            return
        
        print('\n✅ Debug completed')
        
    except Exception as e:
        print(f'❌ Failed to debug sources: {e}')

if __name__ == "__main__":
    asyncio.run(debug_sources())

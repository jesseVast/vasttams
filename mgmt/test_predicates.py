#!/usr/bin/env python3
"""
Test script to debug predicate combination issues.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_predicate_combination():
    """Test predicate combination logic."""
    try:
        from app.storage.vast_store import VASTStore
        from app.core.config import get_settings
        
        settings = get_settings()
        store = VASTStore()
        
        print('🔍 Testing predicate combination logic:')
        
        # Test 1: No filters
        print('\n1. Testing no filters:')
        predicate = None
        soft_delete_predicate = store._add_soft_delete_predicate(predicate)
        print(f'   Original predicate: {predicate}')
        print(f'   After soft delete: {soft_delete_predicate}')
        
        # Test 2: Dictionary predicate
        print('\n2. Testing dictionary predicate:')
        predicate = {'label': 'Test Source'}
        soft_delete_predicate = store._add_soft_delete_predicate(predicate)
        print(f'   Original predicate: {predicate}')
        print(f'   After soft delete: {soft_delete_predicate}')
        
        # Test 3: Ibis predicate
        print('\n3. Testing ibis predicate:')
        try:
            from ibis import _ as ibis_
            predicate = (ibis_.label == 'Test Source')
            soft_delete_predicate = store._add_soft_delete_predicate(predicate)
            print(f'   Original predicate: {predicate}')
            print(f'   After soft delete: {soft_delete_predicate}')
        except Exception as e:
            print(f'   Error with ibis predicate: {e}')
        
        print('\n✅ Predicate tests completed')
        
    except Exception as e:
        print(f'❌ Failed to test predicates: {e}')

if __name__ == "__main__":
    test_predicate_combination()

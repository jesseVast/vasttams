#!/usr/bin/env python3
"""
Test script to debug ibis predicate evaluation.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ibis_predicates():
    """Test ibis predicate creation and evaluation."""
    try:
        print('🔍 Testing ibis predicate creation:')
        
        # Test 1: Basic ibis import
        try:
            from ibis import _ as ibis_
            print('✅ Ibis import successful')
        except Exception as e:
            print(f'❌ Ibis import failed: {e}')
            return
        
        # Test 2: Create basic predicates
        try:
            # Test source ID predicate
            source_id = "550e8400-e29b-41d4-a716-446655440000"
            predicate = (ibis_.id == source_id)
            print(f'✅ Created source ID predicate: {predicate}')
            
            # Test soft delete predicate
            soft_delete_predicate = (ibis_.deleted.isnull() | (ibis_.deleted == False))
            print(f'✅ Created soft delete predicate: {soft_delete_predicate}')
            
            # Test combined predicate
            combined_predicate = predicate & soft_delete_predicate
            print(f'✅ Created combined predicate: {combined_predicate}')
            
        except Exception as e:
            print(f'❌ Predicate creation failed: {e}')
            return
        
        print('\n✅ All ibis predicate tests passed')
        
    except Exception as e:
        print(f'❌ Failed to test ibis predicates: {e}')

if __name__ == "__main__":
    test_ibis_predicates()

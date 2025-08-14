#!/usr/bin/env python3
"""
Minimal test script to see the raw output of query_with_predicates
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.storage.vastdbmanager.core import VastDBManager
from app.config import get_settings
from ibis import _ as ibis_

def test_raw_query():
    """Test query_with_predicates to see raw output"""
    try:
        # Get settings
        settings = get_settings()
        
        # Create VastDBManager instance
        db_manager = VastDBManager(
            endpoints=settings.vast_endpoint
        )
        
        print("🔍 Testing query_with_predicates with include_row_ids=True...")
        
        # Create a simple predicate
        predicate = (ibis_.id == "202d35bb-a43f-4ce7-9da0-4c3728c73695")
        
        # Test the query
        result = db_manager.query_with_predicates('sources', predicate, include_row_ids=True)
        
        print(f"✅ Query completed")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_raw_query()

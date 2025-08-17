#!/usr/bin/env python3
"""
Test script for dependency check functions
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.storage.vast_store import VASTStore


async def test_dependency_checks():
    """Test the dependency check functions"""
    print("🧪 Testing dependency check functions...")
    
    try:
        # Initialize VAST store
        store = VASTStore()
        
        # Test source dependency check
        test_source_id = "test-source-123"
        print(f"\n📝 Testing source dependency check for: {test_source_id}")
        
        source_deps = await store.check_source_dependencies(test_source_id)
        print(f"   Source dependencies: {source_deps}")
        
        # Test flow dependency check
        test_flow_id = "test-flow-456"
        print(f"\n📝 Testing flow dependency check for: {test_flow_id}")
        
        flow_deps = await store.check_flow_dependencies(test_flow_id)
        print(f"   Flow dependencies: {flow_deps}")
        
        # Test segment dependency check
        test_segment_id = "test-segment-789"
        test_flow_id_for_segment = "test-flow-456"
        print(f"\n📝 Testing segment dependency check for: {test_segment_id}")
        
        segment_deps = await store.check_segment_dependencies(test_segment_id, test_flow_id_for_segment)
        print(f"   Segment dependencies: {segment_deps}")
        
        # Test dependency summary
        print(f"\n📝 Testing dependency summary for source: {test_source_id}")
        summary = await store.get_dependency_summary('source', test_source_id)
        print(f"   Summary: {summary}")
        
        print("\n✅ Dependency check tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_dependency_checks())

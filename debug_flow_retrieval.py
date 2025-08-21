#!/usr/bin/env python3
"""
Debug script to test flow creation and retrieval
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.storage.vast_store import VASTStore
from app.models.models import VideoFlow, Source
from app.core.config import get_settings

async def debug_flow_retrieval():
    """Debug flow creation and retrieval"""
    print("🔍 Debugging Flow Creation and Retrieval")
    
    # Initialize VAST store
    settings = get_settings()
    store = VASTStore(
        endpoint=settings.vast_endpoint,
        access_key=settings.vast_access_key,
        secret_key=settings.vast_secret_key,
        bucket=settings.vast_bucket,
        schema=settings.vast_schema
    )
    
    # Create a test source first
    source = Source(
        id="550e8400-e29b-41d4-a716-446655440005",
        format="urn:x-nmos:format:video",
        label="Debug Source",
        description="Source for debugging flow retrieval"
    )
    
    print(f"📝 Creating source: {source.id}")
    source_created = await store.create_source(source)
    print(f"   Source created: {source_created}")
    
    if not source_created:
        print("❌ Failed to create source")
        return
    
    # Create a test flow
    flow = VideoFlow(
        id="550e8400-e29b-41d4-a716-446655440006",
        source_id="550e8400-e29b-41d4-a716-446655440005",
        format="urn:x-nmos:format:video",
        codec="video/h264",
        label="Debug Flow",
        description="Flow for debugging retrieval",
        frame_width=1920,
        frame_height=1080,
        frame_rate={"numerator": 25, "denominator": 1}
    )
    
    print(f"📝 Creating flow: {flow.id}")
    flow_created = await store.create_flow(flow)
    print(f"   Flow created: {flow_created}")
    
    if not flow_created:
        print("❌ Failed to create flow")
        return
    
    # Try to retrieve the flow
    print(f"🔍 Retrieving flow: {flow.id}")
    try:
        retrieved_flow = await store.get_flow(flow.id)
        
        if retrieved_flow:
            print(f"✅ Flow retrieved successfully!")
            print(f"   ID: {retrieved_flow.id}")
            print(f"   Format: {retrieved_flow.format}")
            print(f"   Frame rate: {retrieved_flow.frame_rate}")
        else:
            print("❌ Flow retrieval failed - returned None")
    except Exception as e:
        print(f"❌ Flow retrieval failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check if flow exists in database directly
    print(f"🔍 Checking database directly for flow: {flow.id}")
    try:
        results = store.db_manager.select('flows', predicate=None, output_by_row=True)
        print(f"   Database query results: {results}")
        if results:
            if isinstance(results, list):
                print(f"   Found {len(results)} flows:")
                for i, row in enumerate(results):
                    print(f"     Flow {i}: ID={row.get('id')}, Label={row.get('label')}")
            elif isinstance(results, dict):
                print(f"   Column-oriented results with {len(results.get('id', []))} flows:")
                for i, flow_id in enumerate(results.get('id', [])):
                    print(f"     Flow {i}: ID={flow_id}, Label={results.get('label', [])[i] if i < len(results.get('label', [])) else 'N/A'}")
        else:
            print("   No results from database query")
    except Exception as e:
        print(f"   Database query error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_flow_retrieval())

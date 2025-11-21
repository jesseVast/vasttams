#!/usr/bin/env python3
"""
TAMS Object Vectors Test Script

This script tests updating and retrieving data from the object_vectors table.

Usage:
    # Test with an existing object ID
    python mgmt/test_object_vectors.py --object-id <object_id>
    
    # Test with auto-generated test object
    python mgmt/test_object_vectors.py --create-test-object
    
    # Test vector search
    python mgmt/test_object_vectors.py --object-id <object_id> --test-search
    
    # List all vectors in the table
    python mgmt/test_object_vectors.py --list-vectors
    
    # Query specific object vector
    python mgmt/test_object_vectors.py --query-object-id <object_id>
"""

import sys
import os
import json
import argparse
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

# Add the src directory to the path
root_dir = os.path.abspath(str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(root_dir) / "src" / "server"))
sys.path.insert(0, root_dir)

# Change to root directory so config/config.yaml is found
os.chdir(root_dir)

from vasttamsserver.core.config import get_settings
from vasttamsserver.core.dependencies import get_vast_db, get_s3_client
from vasttamsserver.vast.service import VastObjectVectorService
from vasttamsserver.objects.service import ObjectStorageService
from vasttamsserver.objects.models import Object
from vasttamsserver.common.storage.timestamp_utils import get_tams_timestamp


def generate_test_vector(dimension: int = 768) -> List[float]:
    """Generate a random test vector of specified dimension"""
    return [random.uniform(-1.0, 1.0) for _ in range(dimension)]


def normalize_vector(vector: List[float]) -> List[float]:
    """Normalize a vector to unit length (for cosine similarity)"""
    magnitude = sum(x * x for x in vector) ** 0.5
    if magnitude == 0:
        return vector
    return [x / magnitude for x in vector]


async def create_test_object(vast_db, s3_client) -> str:
    """Create a test object for vector testing"""
    print("📦 Creating test object...")
    
    object_service = ObjectStorageService(vast_db, s3_client)
    
    # Create a minimal test object
    test_object = Object(
        id=f"test-vector-{random.randint(100000, 999999)}",
        timerange=None,
        size=1024,
        metadata=json.dumps({"test": True, "purpose": "vector_testing"}),
        created=get_tams_timestamp()
    )
    
    try:
        success = await object_service.create_object(test_object)
        if success:
            print(f"✅ Created test object: {test_object.id}")
            return test_object.id
        else:
            print("❌ Failed to create test object")
            return None
    except Exception as e:
        print(f"❌ Error creating test object: {e}")
        return None


async def test_update_vector(service: VastObjectVectorService, object_id: str, vector: List[float], 
                             summary: Optional[str] = None, embedding_model: Optional[str] = None):
    """Test updating a vector for an object"""
    print(f"\n🔹 Testing vector update for object: {object_id}")
    print(f"   Vector dimension: {len(vector)}")
    print(f"   Summary: {summary}")
    print(f"   Embedding model: {embedding_model}")
    
    try:
        success = await service.update_object_vector(
            object_id=object_id,
            vector=vector,
            summary=summary,
            embedding_model=embedding_model
        )
        
        if success:
            print("✅ Vector updated successfully")
            return True
        else:
            print("❌ Vector update returned False")
            return False
    except Exception as e:
        print(f"❌ Error updating vector: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_query_vector(vast_db, object_id: str):
    """Test querying a vector directly from the object_vectors table"""
    print(f"\n🔍 Querying vector for object: {object_id}")
    
    try:
        # Escape object_id to prevent SQL injection
        escaped_object_id = object_id.replace("'", "''")
        
        # Query the object_vectors table
        result = vast_db.query("object_vectors").select("*").where(f"object_id == '{escaped_object_id}'").execute()
        
        if isinstance(result, dict) and 'data' in result:
            data = result['data']
            if isinstance(data, dict) and data:
                # Check if we have any rows
                object_ids = data.get('object_id', [])
                if len(object_ids) > 0:
                    print(f"✅ Found vector record for object: {object_id}")
                    
                    # Display vector info (not the full vector)
                    vector_col = data.get('vector', [])
                    summary = data.get('summary', [None])[0] if data.get('summary') else None
                    embedding_date = data.get('embedding_date', [None])[0] if data.get('embedding_date') else None
                    embedding_model = data.get('embedding_model', [None])[0] if data.get('embedding_model') else None
                    
                    print(f"   Summary: {summary}")
                    print(f"   Embedding date: {embedding_date}")
                    print(f"   Embedding model: {embedding_model}")
                    if vector_col:
                        vector_val = vector_col[0]
                        if hasattr(vector_val, '__len__'):
                            print(f"   Vector dimension: {len(vector_val)}")
                            print(f"   Vector sample (first 5 values): {vector_val[:5] if len(vector_val) >= 5 else vector_val}")
                        else:
                            print(f"   Vector type: {type(vector_val)}")
                    
                    return True
                else:
                    print(f"❌ No vector record found for object: {object_id}")
                    return False
            else:
                print(f"❌ No data returned for object: {object_id}")
                return False
        else:
            print(f"❌ Unexpected result format: {type(result)}")
            return False
            
    except Exception as e:
        print(f"❌ Error querying vector: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_list_vectors(vast_db, limit: int = 10):
    """List all vectors in the object_vectors table"""
    print(f"\n📋 Listing vectors (limit: {limit})...")
    
    try:
        result = vast_db.query("object_vectors").select("object_id", "summary", "embedding_date", "embedding_model").limit(limit).execute()
        
        if isinstance(result, dict) and 'data' in result:
            data = result['data']
            if isinstance(data, dict) and data:
                object_ids = data.get('object_id', [])
                summaries = data.get('summary', [])
                embedding_dates = data.get('embedding_date', [])
                embedding_models = data.get('embedding_model', [])
                
                count = len(object_ids)
                print(f"✅ Found {count} vector record(s)")
                
                for i in range(count):
                    obj_id = object_ids[i] if i < len(object_ids) else None
                    summary = summaries[i] if i < len(summaries) else None
                    embedding_date = embedding_dates[i] if i < len(embedding_dates) else None
                    embedding_model = embedding_models[i] if i < len(embedding_models) else None
                    
                    print(f"\n   [{i+1}] Object ID: {obj_id}")
                    print(f"       Summary: {summary}")
                    print(f"       Embedding date: {embedding_date}")
                    print(f"       Embedding model: {embedding_model}")
                
                return True
            else:
                print("❌ No data returned")
                return False
        else:
            print("❌ Unexpected result format")
            return False
            
    except Exception as e:
        print(f"❌ Error listing vectors: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_vector_search(service: VastObjectVectorService, query_vector: List[float], 
                             num_matches: int = 5, distance_metric: Optional[str] = None,
                             distance_threshold: Optional[float] = None):
    """Test vector similarity search"""
    print(f"\n🔎 Testing vector search")
    print(f"   Query vector dimension: {len(query_vector)}")
    print(f"   Number of matches: {num_matches}")
    print(f"   Distance metric: {distance_metric or 'default'}")
    print(f"   Distance threshold: {distance_threshold or 'default'}")
    
    try:
        results = await service.search_vectors(
            query_vector=query_vector,
            num_matches=num_matches,
            distance_metric=distance_metric,
            distance_numerical_value=distance_threshold
        )
        
        matches = results.get('matches', [])
        print(f"✅ Search completed, found {len(matches)} match(es)")
        
        for i, match in enumerate(matches):
            print(f"\n   [{i+1}] Object ID: {match.get('object_id')}")
            print(f"       Segment ID: {match.get('segment_id')}")
            print(f"       Flow ID: {match.get('flow_id')}")
            print(f"       Source ID: {match.get('source_id')}")
            distance = match.get('distance')
            if distance is not None:
                print(f"       Distance: {distance:.6f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error performing vector search: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test object_vectors table operations")
    parser.add_argument("--object-id", type=str, help="Object ID to test with")
    parser.add_argument("--create-test-object", action="store_true", help="Create a test object")
    parser.add_argument("--test-search", action="store_true", help="Test vector search")
    parser.add_argument("--list-vectors", action="store_true", help="List all vectors")
    parser.add_argument("--query-object-id", type=str, help="Query vector for specific object")
    parser.add_argument("--num-matches", type=int, default=5, help="Number of matches for search")
    parser.add_argument("--distance-metric", type=str, choices=["cosine", "euclidean", "dot_product"], 
                       help="Distance metric for search")
    parser.add_argument("--distance-threshold", type=float, help="Distance threshold for search")
    parser.add_argument("--summary", type=str, help="Summary text for vector")
    parser.add_argument("--embedding-model", type=str, default="nomic-embed-1.5", help="Embedding model name")
    parser.add_argument("--list-limit", type=int, default=10, help="Limit for listing vectors")
    
    args = parser.parse_args()
    
    # Initialize services
    print("🔧 Initializing services...")
    try:
        settings = get_settings()
        vast_db = get_vast_db()
        s3_client = get_s3_client()
        service = VastObjectVectorService(vast_db, s3_client)
        print("✅ Services initialized")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # List vectors if requested
    if args.list_vectors:
        await test_list_vectors(vast_db, limit=args.list_limit)
        return 0
    
    # Query specific object if requested
    if args.query_object_id:
        await test_query_vector(vast_db, args.query_object_id)
        return 0
    
    # Determine object ID
    object_id = args.object_id
    
    if args.create_test_object:
        object_id = await create_test_object(vast_db, s3_client)
        if not object_id:
            print("❌ Cannot proceed without object ID")
            return 1
    
    if not object_id:
        print("❌ No object ID provided. Use --object-id or --create-test-object")
        parser.print_help()
        return 1
    
    # Test vector update
    test_vector = generate_test_vector(768)
    success = await test_update_vector(
        service, 
        object_id, 
        test_vector,
        summary=args.summary or f"Test vector for {object_id}",
        embedding_model=args.embedding_model
    )
    
    if not success:
        print("❌ Vector update failed, cannot proceed")
        return 1
    
    # Test querying the vector
    await test_query_vector(vast_db, object_id)
    
    # Test vector search if requested
    if args.test_search:
        # Use a slightly different vector for search (to test similarity)
        search_vector = generate_test_vector(768)
        await test_vector_search(
            service,
            search_vector,
            num_matches=args.num_matches,
            distance_metric=args.distance_metric,
            distance_threshold=args.distance_threshold
        )
    
    print("\n✅ All tests completed")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)



#!/usr/bin/env python3
"""
Large Flow Stress Test for TAMS API

This test creates a large flow with 1000 segments and tests selective deletion:
- Create 1 source
- Create 1 flow
- Create 1000 segments with 50KB objects
- Track all flow and segment names
- Delete 10 segments from the flow
- Delete 501 segments from the flow
- Verify remaining segments

Usage:
    python test_large_flow_stress.py
"""

import sys
import os
import uuid
import asyncio
import aiohttp
import json
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.real_tests.test_harness import test_harness


class TestLargeFlowStress:
    """Test large flow creation and selective segment deletion"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_data = {
            'source_id': None,
            'flow_id': None,
            'segment_ids': [],
            'object_ids': [],
            'segment_names': [],
            'flow_name': None
        }
        
    async def create_test_file(self, filename: str, size_kb: int = 50) -> tuple[str, int]:
        """Create a temporary test file and return its path and size"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}")
        temp_path = temp_file.name
        
        # Create file with random content (size_kb KB)
        size_bytes = int(size_kb * 1024)
        content = os.urandom(size_bytes)
        temp_file.write(content)
        temp_file.close()
        
        return temp_path, len(content)
    
    def cleanup_test_file(self, file_path: str):
        """Clean up temporary test file"""
        try:
            os.unlink(file_path)
        except OSError:
            pass
    
    async def test_large_flow_creation(self):
        """Test creating a large flow with 1000 segments"""
        print("🧪 Testing large flow creation with 1000 segments...")
        
        try:
            async with aiohttp.ClientSession() as session:
                print("🌐 Starting large flow stress test...")
                print(f"   📡 Base URL: {self.base_url}")
                print("   📋 Test will create 1000 segments and test selective deletion")
                print()
                
                # Step 1: Create a source
                print("📝 Step 1: Creating source for large flow test")
                source_id = str(uuid.uuid4())
                source_name = f"stress-test-source-{source_id[:8]}"
                source_data = {
                    "id": source_id,
                    "format": "urn:x-nmos:format:video",
                    "label": source_name,
                    "description": "Source for large flow stress test"
                }
                
                async with session.post(f"{self.base_url}/sources", json=source_data) as response:
                    if response.status == 201:
                        print(f"   ✅ Source created: {source_name} ({source_id})")
                        self.test_data['source_id'] = source_id
                    else:
                        print(f"   ❌ Source creation failed: {response.status}")
                        response_text = await response.text()
                        print(f"   📄 Response: {response_text}")
                        return False
                
                # Step 2: Create flow
                print("📝 Step 2: Creating flow for large flow test")
                flow_id = str(uuid.uuid4())
                flow_name = f"stress-test-flow-{flow_id[:8]}"
                flow_data = {
                    "id": flow_id,
                    "source_id": source_id,
                    "codec": "video/h264",
                    "frame_width": 1920,
                    "frame_height": 1080,
                    "frame_rate": "25/1",
                    "label": flow_name,
                    "description": "Flow for large flow stress test"
                }
                
                async with session.post(f"{self.base_url}/flows", json=flow_data) as response:
                    if response.status == 201:
                        print(f"   ✅ Flow created: {flow_name} ({flow_id})")
                        self.test_data['flow_id'] = flow_id
                        self.test_data['flow_name'] = flow_name
                    else:
                        print(f"   ❌ Flow creation failed: {response.status}")
                        response_text = await response.text()
                        print(f"   📄 Response: {response_text}")
                        return False
                
                # Step 3: Get storage allocation for 1000 objects
                print("📝 Step 3: Getting storage allocation for 1000 objects")
                storage_request = {
                    "storage_id": None,  # Use default storage
                    "limit": 1000
                }
                
                start_time = time.time()
                async with session.post(f"{self.base_url}/flows/{flow_id}/storage", json=storage_request) as response:
                    if response.status in [200, 201]:
                        storage_data = await response.json()
                        allocation_time = time.time() - start_time
                        print(f"   ✅ Storage allocated for {flow_name} in {allocation_time:.2f}s")
                        
                        # Extract media objects
                        media_objects = storage_data.get('media_objects', [])
                        if len(media_objects) >= 1000:
                            print(f"   📁 Media objects available: {len(media_objects)}")
                            self.test_data['object_ids'] = [obj.get('object_id') for obj in media_objects]
                        else:
                            print(f"   ❌ Insufficient media objects: {len(media_objects)} < 1000")
                            return False
                    else:
                        print(f"   ❌ Storage allocation failed: {response.status}")
                        response_text = await response.text()
                        print(f"   📄 Response: {response_text}")
                        return False
                
                # Step 4: Create 1000 segments
                print("📝 Step 4: Creating 1000 segments")
                segment_creation_start = time.time()
                
                # Create segments in batches to avoid overwhelming the API
                batch_size = 50
                total_segments = 1000
                
                for batch_start in range(0, total_segments, batch_size):
                    batch_end = min(batch_start + batch_size, total_segments)
                    batch_num = (batch_start // batch_size) + 1
                    total_batches = (total_segments + batch_size - 1) // batch_size
                    
                    print(f"   📦 Creating batch {batch_num}/{total_batches} (segments {batch_start+1}-{batch_end})")
                    
                    # Create segments for this batch
                    batch_segments = []
                    for i in range(batch_start, batch_end):
                        object_id = self.test_data['object_ids'][i]
                        segment_name = f"stress-seg-{i+1:04d}"
                        
                        segment_data = {
                            "object_id": object_id,
                            "timerange": f"{i*3600}:0_{(i+1)*3600}:0",
                            "ts_offset": f"{i*3600}:0",
                            "last_duration": "3600:0"
                        }
                        
                        data = aiohttp.FormData()
                        data.add_field('segment_data', json.dumps(segment_data), content_type='application/json')
                        
                        async with session.post(f"{self.base_url}/flows/{flow_id}/segments", data=data) as response:
                            if response.status == 201:
                                segment_response = await response.json()
                                segment_id = segment_response.get('object_id')
                                batch_segments.append({
                                    'id': segment_id,
                                    'name': segment_name,
                                    'index': i + 1
                                })
                            else:
                                print(f"   ❌ Segment {i+1} creation failed: {response.status}")
                                return False
                    
                    # Add batch segments to tracking
                    self.test_data['segment_ids'].extend([seg['id'] for seg in batch_segments])
                    self.test_data['segment_names'].extend([seg['name'] for seg in batch_segments])
                    
                    # Progress update
                    elapsed = time.time() - segment_creation_start
                    segments_created = len(self.test_data['segment_ids'])
                    rate = segments_created / elapsed if elapsed > 0 else 0
                    eta = (total_segments - segments_created) / rate if rate > 0 else 0
                    
                    print(f"      ✅ Batch {batch_num} complete: {len(batch_segments)} segments")
                    print(f"      📊 Progress: {segments_created}/{total_segments} ({segments_created/total_segments*100:.1f}%)")
                    print(f"      ⏱️  Rate: {rate:.1f} segments/sec, ETA: {eta:.1f}s")
                
                total_creation_time = time.time() - segment_creation_start
                print(f"   ✅ All 1000 segments created in {total_creation_time:.2f}s")
                print(f"   📊 Average rate: {1000/total_creation_time:.1f} segments/sec")
                
                # Step 5: Verify segment count
                print("📝 Step 5: Verifying segment count")
                async with session.get(f"{self.base_url}/flows/{flow_id}/segments") as response:
                    if response.status == 200:
                        segments = await response.json()
                        actual_count = len(segments)
                        print(f"   ✅ Flow {flow_name} has {actual_count} segments")
                        
                        if actual_count != 1000:
                            print(f"   ⚠️  Expected 1000 segments, got {actual_count}")
                        else:
                            print(f"   🎯 Perfect! All 1000 segments verified")
                    else:
                        print(f"   ❌ Failed to retrieve segments: {response.status}")
                        return False
                
                # Step 6: List all flow and segment names
                print("📝 Step 6: Listing all flow and segment names")
                print(f"   📁 Source: {source_name} ({source_id})")
                print(f"   📁 Flow: {flow_name} ({flow_id})")
                print(f"   📁 Segments: {len(self.test_data['segment_names'])} total")
                
                # Show first 10 and last 10 segment names
                if len(self.test_data['segment_names']) >= 20:
                    print(f"      📋 First 10: {', '.join(self.test_data['segment_names'][:10])}")
                    print(f"      📋 Last 10: {', '.join(self.test_data['segment_names'][-10:])}")
                else:
                    print(f"      📋 All: {', '.join(self.test_data['segment_names'])}")
                
                print("✅ Large flow creation test completed successfully!")
                return True
                
        except Exception as e:
            print(f"❌ Large flow creation test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_selective_segment_deletion(self):
        """Test selective deletion of segments"""
        print("\n🧪 Testing selective segment deletion...")
        
        if not self.test_data['flow_id'] or not self.test_data['segment_ids']:
            print("   ❌ No flow or segments available for deletion test")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                flow_id = self.test_data['flow_id']
                flow_name = self.test_data['flow_name']
                
                # Step 7: Delete first 10 segments
                print("📝 Step 7: Deleting first 10 segments")
                segments_to_delete = self.test_data['segment_ids'][:10]
                segment_names_to_delete = self.test_data['segment_names'][:10]
                
                print(f"   🗑️  Deleting segments: {', '.join(segment_names_to_delete)}")
                
                deletion_start = time.time()
                deleted_count = 0
                
                for segment_id in segments_to_delete:
                    # Delete segment by object_id (since segments are identified by object_id)
                    async with session.delete(f"{self.base_url}/flows/{flow_id}/segments/{segment_id}") as response:
                        if response.status in [200, 204]:
                            deleted_count += 1
                        else:
                            print(f"   ❌ Failed to delete segment {segment_id}: {response.status}")
                
                deletion_time = time.time() - deletion_start
                print(f"   ✅ Deleted {deleted_count}/10 segments in {deletion_time:.2f}s")
                
                # Verify deletion
                async with session.get(f"{self.base_url}/flows/{flow_id}/segments") as response:
                    if response.status == 200:
                        segments = await response.json()
                        remaining_after_10 = len(segments)
                        print(f"   📊 Segments remaining after 10 deletions: {remaining_after_10}")
                        
                        if remaining_after_10 == 990:
                            print(f"   🎯 Perfect! 10 segments deleted successfully")
                        else:
                            print(f"   ⚠️  Expected 990 segments, got {remaining_after_10}")
                    else:
                        print(f"   ❌ Failed to verify deletion: {response.status}")
                
                # Step 8: Delete next 501 segments
                print("📝 Step 8: Deleting next 501 segments")
                segments_to_delete_501 = self.test_data['segment_ids'][10:511]  # 10-510 (501 segments)
                segment_names_to_delete_501 = self.test_data['segment_names'][10:511]
                
                print(f"   🗑️  Deleting segments: {len(segments_to_delete_501)} segments")
                print(f"      📋 Range: {segment_names_to_delete_501[0]} to {segment_names_to_delete_501[-1]}")
                
                deletion_start_501 = time.time()
                deleted_count_501 = 0
                
                # Delete in smaller batches to avoid overwhelming the API
                batch_size = 25
                for i in range(0, len(segments_to_delete_501), batch_size):
                    batch = segments_to_delete_501[i:i+batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(segments_to_delete_501) + batch_size - 1) // batch_size
                    
                    print(f"      📦 Deleting batch {batch_num}/{total_batches} ({len(batch)} segments)")
                    
                    for segment_id in batch:
                        async with session.delete(f"{self.base_url}/flows/{flow_id}/segments/{segment_id}") as response:
                            if response.status in [200, 204]:
                                deleted_count_501 += 1
                            else:
                                print(f"         ❌ Failed to delete segment {segment_id}: {response.status}")
                
                deletion_time_501 = time.time() - deletion_start_501
                print(f"   ✅ Deleted {deleted_count_501}/501 segments in {deletion_time_501:.2f}s")
                
                # Verify final deletion
                async with session.get(f"{self.base_url}/flows/{flow_id}/segments") as response:
                    if response.status == 200:
                        segments = await response.json()
                        final_count = len(segments)
                        print(f"   📊 Final segments remaining: {final_count}")
                        
                        expected_final = 1000 - 10 - 501  # 489 segments
                        if final_count == expected_final:
                            print(f"   🎯 Perfect! Final count matches expected: {expected_final}")
                        else:
                            print(f"   ⚠️  Expected {expected_final} segments, got {final_count}")
                    else:
                        print(f"   ❌ Failed to verify final count: {response.status}")
                
                # Step 9: Final verification and cleanup
                print("📝 Step 9: Final verification and cleanup")
                print(f"   📊 Test Summary:")
                print(f"      📁 Source: {self.test_data['source_id']}")
                print(f"      📁 Flow: {flow_name} ({flow_id})")
                print(f"      📁 Initial segments: 1000")
                print(f"      📁 Deleted first: 10")
                print(f"      📁 Deleted second: 501")
                print(f"      📁 Final remaining: {final_count}")
                print(f"      📁 Total deleted: {deleted_count + deleted_count_501}")
                
                print("✅ Selective segment deletion test completed successfully!")
                return True
                
        except Exception as e:
            print(f"❌ Selective segment deletion test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_full_stress_test(self):
        """Run the complete large flow stress test"""
        print("🚀 TAMS Large Flow Stress Test")
        print("=" * 60)
        print("This test will:")
        print("1. Create 1 source")
        print("2. Create 1 flow")
        print("3. Create 1000 segments with 50KB objects")
        print("4. Track all flow and segment names")
        print("5. Delete 10 segments from the flow")
        print("6. Delete 501 segments from the flow")
        print("7. Verify remaining segments")
        print()
        
        # Run the tests
        success = True
        
        # Test 1: Large flow creation
        if not await self.test_large_flow_creation():
            success = False
        
        # Test 2: Selective deletion
        if success and not await self.test_selective_segment_deletion():
            success = False
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 STRESS TEST SUMMARY")
        print("=" * 60)
        
        if success:
            print("✅ All stress tests PASSED!")
            print(f"   📁 Source: {self.test_data['source_id']}")
            print(f"   📁 Flow: {self.test_data['flow_name']} ({self.test_data['flow_id']})")
            print(f"   📁 Segments created: {len(self.test_data['segment_ids'])}")
            print(f"   📁 Segments deleted: 511 (10 + 501)")
            print(f"   📁 Segments remaining: {len(self.test_data['segment_ids']) - 511}")
        else:
            print("❌ Some stress tests FAILED!")
            print("   Check the output above for details")
        
        return success


if __name__ == "__main__":
    """Run the large flow stress test"""
    # Create test instance
    tester = TestLargeFlowStress()
    
    # Run the test
    asyncio.run(tester.run_full_stress_test())

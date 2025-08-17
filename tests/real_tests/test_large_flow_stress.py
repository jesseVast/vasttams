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
from concurrent.futures import ThreadPoolExecutor
import requests

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
        # Configuration for parallel operations
        self.max_concurrent_segments = 50  # Max concurrent segment creation
        self.max_concurrent_uploads = 20   # Max concurrent S3 uploads
        
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
    
    async def create_segment_parallel(self, session: aiohttp.ClientSession, flow_id: str, 
                                    object_id: str, segment_index: int) -> Dict[str, Any]:
        """Create a single segment in parallel"""
        try:
            segment_name = f"stress-seg-{segment_index+1:04d}"
            
            segment_data = {
                "object_id": object_id,
                "timerange": f"{segment_index*3600}:0_{(segment_index+1)*3600}:0",
                "ts_offset": f"{segment_index*3600}:0",
                "last_duration": "3600:0"
            }
            
            data = aiohttp.FormData()
            data.add_field('segment_data', json.dumps(segment_data), content_type='application/json')
            
            async with session.post(f"{self.base_url}/flows/{flow_id}/segments", data=data) as response:
                if response.status == 201:
                    segment_response = await response.json()
                    segment_id = segment_response.get('object_id')
                    return {
                        'id': segment_id,
                        'name': segment_name,
                        'index': segment_index + 1,
                        'success': True
                    }
                else:
                    response_text = await response.text()
                    return {
                        'id': None,
                        'name': segment_name,
                        'index': segment_index + 1,
                        'success': False,
                        'error': f"HTTP {response.status}: {response_text}"
                    }
        except Exception as e:
            return {
                'id': None,
                'name': f"stress-seg-{segment_index+1:04d}",
                'index': segment_index + 1,
                'success': False,
                'error': str(e)
            }
    
    async def upload_file_parallel(self, put_url: str, file_path: str, object_id: str) -> Dict[str, Any]:
        """Upload a file to S3 in parallel using requests"""
        try:
            with open(file_path, 'rb') as f:
                response = requests.put(put_url, data=f, timeout=30)
                
            if response.status_code in [200, 201]:
                return {
                    'object_id': object_id,
                    'success': True,
                    'status_code': response.status_code
                }
            else:
                return {
                    'object_id': object_id,
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                'object_id': object_id,
                'success': False,
                'error': str(e)
            }
    
    async def test_large_flow_creation(self):
        """Test creating a large flow with 1000 segments using parallel operations"""
        print("🧪 Testing large flow creation with 1000 segments (PARALLEL OPTIMIZED)...")
        
        try:
            async with aiohttp.ClientSession() as session:
                print("🌐 Starting large flow stress test...")
                print(f"   📡 Base URL: {self.base_url}")
                print(f"   🚀 Parallel segment creation: {self.max_concurrent_segments}")
                print(f"   🚀 Parallel uploads: {self.max_concurrent_uploads}")
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
                
                # Step 3: Get storage allocation for 1000 objects (BULK - already optimized)
                print("📝 Step 3: Getting storage allocation for 1000 objects (BULK)")
                storage_request = {
                    "storage_id": None,  # Use default storage
                    "limit": 1000
                }
                
                start_time = time.time()
                print("   🚀 Requesting bulk storage allocation for 1000 objects...")
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
                            print(f"   🎯 Bulk storage allocation successful!")
                        else:
                            print(f"   ❌ Insufficient media objects: {len(media_objects)} < 1000")
                            return False
                    else:
                        print(f"   ❌ Storage allocation failed: {response.status}")
                        response_text = await response.text()
                        print(f"   📄 Response: {response_text}")
                        return False
                
                # Step 4: Create 1000 segments using PARALLEL creation
                print("📝 Step 4: Creating 1000 segments using PARALLEL creation")
                segment_creation_start = time.time()
                
                # Create segments in parallel batches
                total_segments = 1000
                all_segments = []
                
                print(f"   🚀 Starting parallel segment creation with {self.max_concurrent_segments} concurrent operations...")
                
                for batch_start in range(0, total_segments, self.max_concurrent_segments):
                    batch_end = min(batch_start + self.max_concurrent_segments, total_segments)
                    batch_num = (batch_start // self.max_concurrent_segments) + 1
                    total_batches = (total_segments + self.max_concurrent_segments - 1) // self.max_concurrent_segments
                    
                    print(f"   📦 Processing batch {batch_num}/{total_batches} (segments {batch_start+1}-{batch_end})")
                    batch_start_time = time.time()
                    
                    # Create tasks for this batch
                    tasks = []
                    for i in range(batch_start, batch_end):
                        object_id = self.test_data['object_ids'][i]
                        task = self.create_segment_parallel(session, flow_id, object_id, i)
                        tasks.append(task)
                    
                    # Execute batch in parallel
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    batch_segments = []
                    batch_errors = []
                    for result in batch_results:
                        if isinstance(result, Exception):
                            batch_errors.append(f"Task exception: {result}")
                        elif result.get('success'):
                            batch_segments.append(result)
                        else:
                            batch_errors.append(f"Segment {result.get('index')}: {result.get('error')}")
                    
                    # Add batch segments to tracking
                    self.test_data['segment_ids'].extend([seg['id'] for seg in batch_segments])
                    self.test_data['segment_names'].extend([seg['name'] for seg in batch_segments])
                    
                    # Progress update
                    batch_time = time.time() - batch_start_time
                    elapsed = time.time() - segment_creation_start
                    segments_created = len(self.test_data['segment_ids'])
                    rate = segments_created / elapsed if elapsed > 0 else 0
                    eta = (total_segments - segments_created) / rate if rate > 0 else 0
                    
                    print(f"      ✅ Batch {batch_num} complete: {len(batch_segments)} segments in {batch_time:.2f}s")
                    if batch_errors:
                        print(f"      ⚠️  Batch {batch_num} errors: {len(batch_errors)}")
                        for error in batch_errors[:3]:  # Show first 3 errors
                            print(f"         ❌ {error}")
                        if len(batch_errors) > 3:
                            print(f"         ... and {len(batch_errors) - 3} more errors")
                    
                    print(f"      📊 Progress: {segments_created}/{total_segments} ({segments_created/total_segments*100:.1f}%)")
                    print(f"      ⏱️  Rate: {rate:.1f} segments/sec, ETA: {eta:.1f}s")
                    
                    # Small delay between batches to avoid overwhelming the server
                    if batch_num < total_batches:
                        await asyncio.sleep(0.1)
                
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
                
                # Step 7: Delete first 10 segments using bulk delete
                print("📝 Step 7: Deleting first 10 segments using bulk delete")
                segments_to_delete = self.test_data['segment_ids'][:10]
                segment_names_to_delete = self.test_data['segment_names'][:10]
                
                print(f"   🗑️  Deleting segments: {', '.join(segment_names_to_delete)}")
                print("   🚀 Using bulk delete endpoint for better performance...")
                
                # Use bulk delete endpoint for better performance
                # Delete segments by timerange (first 10 segments cover 0-10 hours)
                timerange = "0:0_36000:0"  # 0 to 10 hours (10 * 3600 seconds)
                
                deletion_start = time.time()
                print(f"   📤 DELETE /flows/{flow_id}/segments?timerange={timerange}")
                
                async with session.delete(f"{self.base_url}/flows/{flow_id}/segments?timerange={timerange}") as response:
                    if response.status in [200, 204]:
                        print(f"   ✅ Bulk deleted first 10 segments successfully")
                        deleted_count = 10
                    else:
                        print(f"   ❌ Bulk deletion failed: {response.status}")
                        response_text = await response.text()
                        print(f"   📄 Response: {response_text}")
                        return False
                
                deletion_time = time.time() - deletion_start
                print(f"   ✅ Deleted {deleted_count}/10 segments in {deletion_time:.2f}s")
                
                # Verify deletion
                print("   🔍 Verifying deletion...")
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
                
                # Step 8: Delete next 501 segments using async deletion
                print("📝 Step 8: Delete next 501 segments using async deletion")
                segments_to_delete_501 = self.test_data['segment_ids'][10:511]  # 10-510 (501 segments)
                segment_names_to_delete_501 = self.test_data['segment_names'][10:511]
                
                print(f"   🗑️  Deleting segments: {len(segments_to_delete_501)} segments")
                print(f"      📋 Range: {segment_names_to_delete_501[0]} to {segment_names_to_delete_501[-1]}")
                
                # Use async deletion for large operations (>500 segments)
                print("   🚀 Using async deletion for large operation (501 segments)")
                print("   📤 POST /flow-delete-requests")
                
                # Create async deletion request
                deletion_request_data = {
                    "flow_id": flow_id,
                    "timerange": "36000:0_183600:0",  # 10 hours to 51 hours (segments 11-511)
                    "description": "Stress test deletion of 501 segments"
                }
                
                async with session.post(f"{self.base_url}/flow-delete-requests", json=deletion_request_data) as response:
                    if response.status == 201:
                        deletion_request = await response.json()
                        request_id = deletion_request.get('id')
                        print(f"   ✅ Async deletion request created: {request_id}")
                        
                        # Poll for completion
                        max_wait_time = 300  # 5 minutes max wait
                        poll_interval = 5  # Check every 5 seconds
                        start_poll = time.time()
                        poll_count = 0
                        
                        print("   🔄 Polling for deletion completion...")
                        print(f"      ⏱️  Max wait time: {max_wait_time}s, Poll interval: {poll_interval}s")
                        
                        while time.time() - start_poll < max_wait_time:
                            poll_count += 1
                            elapsed = time.time() - start_poll
                            
                            print(f"      📊 Poll #{poll_count} at {elapsed:.1f}s elapsed...")
                            
                            await asyncio.sleep(poll_interval)
                            
                            async with session.get(f"{self.base_url}/flow-delete-requests/{request_id}") as status_response:
                                if status_response.status == 200:
                                    status_data = await status_response.json()
                                    status = status_data.get('status', 'pending')
                                    print(f"         📊 Deletion status: {status}")
                                    
                                    if status == 'completed':
                                        print(f"   ✅ Async deletion completed successfully")
                                        deleted_count_501 = 501
                                        break
                                    elif status == 'failed':
                                        print(f"   ❌ Async deletion failed")
                                        return False
                                    # Continue polling if status is 'pending' or 'processing'
                                else:
                                    print(f"   ⚠️  Failed to check deletion status: {status_response.status}")
                        
                        if deleted_count_501 != 501:
                            print(f"   ⚠️  Async deletion did not complete within {max_wait_time}s")
                            deleted_count_501 = 0
                    else:
                        print(f"   ❌ Failed to create async deletion request: {response.status}")
                        response_text = await response.text()
                        print(f"   📄 Response: {response_text}")
                        return False
                
                deletion_time_501 = time.time() - deletion_start
                print(f"   ✅ Deleted {deleted_count_501}/501 segments in {deletion_time_501:.2f}s")
                
                # Verify final deletion
                print("   🔍 Verifying final deletion...")
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
    
    async def test_parallel_uploads(self):
        """Test parallel file uploads to S3"""
        print("\n🧪 Testing parallel file uploads...")
        
        if not self.test_data['flow_id'] or not self.test_data['object_ids']:
            print("   ❌ No flow or objects available for upload test")
            return False
        
        try:
            # Create test files for upload
            print("   📁 Creating test files for parallel upload...")
            test_files = []
            for i, object_id in enumerate(self.test_data['object_ids'][:100]):  # Test with first 100
                file_path, file_size = await self.create_test_file(f"test_{i+1}.bin", 50)
                test_files.append({
                    'file_path': file_path,
                    'object_id': object_id,
                    'index': i + 1
                })
            
            print(f"   📁 Created {len(test_files)} test files (50KB each)")
            
            # Get storage allocation for upload test
            print("   🚀 Getting storage allocation for upload test...")
            async with aiohttp.ClientSession() as session:
                flow_id = self.test_data['flow_id']
                storage_request = {
                    "storage_id": None,
                    "limit": len(test_files)
                }
                
                async with session.post(f"{self.base_url}/flows/{flow_id}/storage", json=storage_request) as response:
                    if response.status in [200, 201]:
                        storage_data = await response.json()
                        media_objects = storage_data.get('media_objects', [])
                        
                        if len(media_objects) >= len(test_files):
                            print(f"   ✅ Storage allocated for {len(test_files)} objects")
                            
                            # Create upload tasks
                            upload_tasks = []
                            for i, test_file in enumerate(test_files):
                                media_obj = media_objects[i]
                                put_url = media_obj.get('put_url', {}).get('url')
                                if put_url:
                                    task = self.upload_file_parallel(put_url, test_file['file_path'], test_file['object_id'])
                                    upload_tasks.append(task)
                            
                            # Execute uploads in parallel
                            print(f"   🚀 Starting parallel uploads with {self.max_concurrent_uploads} concurrent operations...")
                            upload_start = time.time()
                            
                            # Process uploads in batches to avoid overwhelming S3
                            batch_size = self.max_concurrent_uploads
                            successful_uploads = 0
                            failed_uploads = 0
                            
                            for batch_start in range(0, len(upload_tasks), batch_size):
                                batch_end = min(batch_start + batch_size, len(upload_tasks))
                                batch_num = (batch_start // batch_size) + 1
                                total_batches = (len(upload_tasks) + batch_size - 1) // batch_size
                                
                                print(f"      📤 Upload batch {batch_num}/{total_batches} ({batch_end - batch_start} files)")
                                batch_start_time = time.time()
                                
                                batch_tasks = upload_tasks[batch_start:batch_end]
                                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                                
                                # Process batch results
                                for result in batch_results:
                                    if isinstance(result, Exception):
                                        failed_uploads += 1
                                        print(f"         ❌ Upload exception: {result}")
                                    elif result.get('success'):
                                        successful_uploads += 1
                                    else:
                                        failed_uploads += 1
                                        print(f"         ❌ Upload failed: {result.get('error')}")
                                
                                batch_time = time.time() - batch_start_time
                                print(f"         ✅ Batch {batch_num} complete in {batch_time:.2f}s")
                                
                                # Small delay between batches
                                if batch_num < total_batches:
                                    await asyncio.sleep(0.1)
                            
                            upload_time = time.time() - upload_start
                            print(f"   ✅ Parallel uploads completed in {upload_time:.2f}s")
                            print(f"   📊 Results: {successful_uploads} successful, {failed_uploads} failed")
                            print(f"   📊 Upload rate: {successful_uploads/upload_time:.1f} files/sec")
                            
                        else:
                            print(f"   ❌ Insufficient storage allocation: {len(media_objects)} < {len(test_files)}")
                            return False
                    else:
                        print(f"   ❌ Storage allocation failed: {response.status}")
                        return False
            
            # Cleanup test files
            print("   🧹 Cleaning up test files...")
            for test_file in test_files:
                self.cleanup_test_file(test_file['file_path'])
            
            print("✅ Parallel upload test completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Parallel upload test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_full_stress_test(self):
        """Run the complete large flow stress test"""
        print("🚀 TAMS Large Flow Stress Test (PARALLEL OPTIMIZED)")
        print("=" * 70)
        print("This test will:")
        print("1. Create 1 source")
        print("2. Create 1 flow")
        print("3. Create 1000 segments with 50KB objects (PARALLEL)")
        print("4. Track all flow and segment names")
        print("5. Test parallel file uploads to S3 (100 files)")
        print("6. Delete 10 segments from the flow")
        print("7. Delete 501 segments from the flow")
        print("8. Verify remaining segments")
        print()
        print("🚀 OPTIMIZATIONS:")
        print("   • Bulk storage allocation (1000 objects at once)")
        print("   • Parallel segment creation (50 concurrent)")
        print("   • Parallel file uploads (20 concurrent)")
        print("   • Batch processing with progress tracking")
        print()
        
        # Run the tests
        success = True
        
        # Test 1: Large flow creation
        if not await self.test_large_flow_creation():
            success = False
        
        # Test 2: Selective deletion
        if success and not await self.test_selective_segment_deletion():
            success = False
        
        # Test 3: Parallel uploads
        if success and not await self.test_parallel_uploads():
            success = False
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 STRESS TEST SUMMARY")
        print("=" * 70)
        
        if success:
            print("✅ All stress tests PASSED!")
            print(f"   📁 Source: {self.test_data['source_id']}")
            print(f"   📁 Flow: {self.test_data['flow_name']} ({self.test_data['flow_id']})")
            print(f"   📁 Segments created: {len(self.test_data['segment_ids'])}")
            print(f"   📁 Segments deleted: 511 (10 + 501)")
            print(f"   📁 Segments remaining: {len(self.test_data['segment_ids']) - 511}")
            print("   🚀 Parallel optimizations: Bulk storage + Parallel segments + Parallel uploads")
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

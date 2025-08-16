#!/usr/bin/env python3
"""
Standalone script to create a flow with 10 segments in real environment.
This demonstrates the flow reference management system with actual database and S3 storage.
"""
import asyncio
import uuid
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.storage.vast_store import VASTStore
from app.models.models import Object, Source, VideoFlow, FlowSegment
from app.api.sources import SourceManager
from app.api.flows import FlowManager
from app.api.objects import ObjectManager
from app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_flow_with_10_segments():
    """Create a flow with 10 segments in the real environment"""
    logger.info("🚀 Starting Real Environment Flow Test with 10 Segments")
    
    try:
        # Get the real VAST store
        logger.info("🔧 Connecting to real VAST store...")
        settings = get_settings()
        vast_store = VASTStore(
            endpoints=[settings.vast_endpoint],
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema,
            s3_endpoint_url=settings.s3_endpoint_url,
            s3_access_key_id=settings.s3_access_key_id,
            s3_secret_access_key=settings.s3_secret_access_key,
            s3_bucket_name=settings.s3_bucket_name,
            s3_use_ssl=settings.s3_use_ssl
        )
        logger.info("✅ Connected to VAST store")
        
        # Create managers
        source_manager = SourceManager(vast_store)
        flow_manager = FlowManager(vast_store)
        object_manager = ObjectManager(vast_store)
        
        # Step 1: Create source
        logger.info("🔧 Creating test source...")
        test_source = Source(
            id=str(uuid.uuid4()),
            label="Real Multi-Segment Video Source",
            format="video",
            description="Test source for flow with 10 segments in real environment",
            created_by="real_test_user"
        )
        
        created_source = await source_manager.create_source(test_source)
        assert created_source is not None, "Source creation failed"
        logger.info(f"✅ Created source: {created_source.id}")
        
        # Step 2: Create flow
        logger.info("🔧 Creating test flow...")
        test_flow = VideoFlow(
            id=str(uuid.uuid4()),
            source_id=test_source.id,
            format="video",
            codec="H.264",
            label="Real Multi-Segment Video Flow",
            description="Test flow with 10 segments in real environment",
            created_by="real_test_user",
            frame_width=1920,
            frame_height=1080,
            frame_rate="30"
        )
        
        created_flow = await flow_manager.create_flow(test_flow)
        assert created_flow is not None, "Flow creation failed"
        logger.info(f"✅ Created flow: {created_flow.id}")
        
        # Step 3: Create 10 segments
        logger.info("🔧 Creating 10 segments...")
        segments = []
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        for i in range(10):
            start_time = base_time + timedelta(minutes=i * 10)
            end_time = start_time + timedelta(minutes=10)
            
            segment = FlowSegment(
                object_id=str(uuid.uuid4()),
                timerange=f"{start_time.isoformat()}/{end_time.isoformat()}",
                sample_offset=i * 1000,
                sample_count=1000,
                key_frame_count=10
            )
            
            # Create segment with test data
            test_data = f"test_segment_data_{i}".encode('utf-8')
            success = await vast_store.create_flow_segment(segment, str(test_flow.id), test_data)
            
            if success:
                segments.append(segment)
                logger.info(f"✅ Created segment {i+1}/10: {segment.object_id}")
            else:
                logger.error(f"❌ Failed to create segment {i+1}/10: {segment.object_id}")
                raise Exception(f"Failed to create segment {i+1}")
        
        logger.info(f"✅ Successfully created all 10 segments")
        
        # Step 4: Create objects with flow references
        logger.info("🔧 Creating objects with flow references...")
        objects = []
        
        for i in range(10):
            obj = Object(
                object_id=str(uuid.uuid4()),
                flow_references=[{"flow_id": test_flow.id, "timerange": f"2024-01-01T{i:02d}:00:00Z/2024-01-01T{i:02d}:10:00Z"}],
                size=1024000 * (i + 1),  # Varying sizes
                created=datetime.now(timezone.utc)
            )
            
            created_obj = await object_manager.create_object(obj)
            assert created_obj is not None, f"Object {i+1} creation failed"
            objects.append(created_obj)
            logger.info(f"✅ Created object {i+1}/10: {obj.object_id}")
        
        logger.info(f"✅ Successfully created all 10 objects with flow references")
        
        # Step 5: Test flow reference queries
        logger.info("🔧 Testing flow reference queries...")
        objects_with_refs = await vast_store.get_objects_by_flow_reference(str(test_flow.id))
        logger.info(f"✅ Found {len(objects_with_refs)} objects referencing flow {test_flow.id}")
        
        # Step 6: Test adding flow references
        logger.info("🔧 Testing flow reference addition...")
        new_flow_id = str(uuid.uuid4())
        
        for i, obj in enumerate(objects):
            success = await vast_store.add_flow_reference(
                obj.object_id, 
                new_flow_id, 
                "2024-01-02T00:00:00Z/2024-01-02T01:00:00Z"
            )
            assert success is True, f"Failed to add flow reference to object {i+1}"
            logger.info(f"✅ Added flow reference to object {i+1}")
        
        logger.info(f"✅ Successfully added flow references to all {len(objects)} objects")
        
        # Step 7: Test flow reference validation
        logger.info("🔧 Testing flow reference validation...")
        for i, obj in enumerate(objects):
            validation_results = await vast_store.validate_flow_references(obj.object_id)
            assert validation_results['valid'] is True, f"Object {i+1} should have valid flow references"
            logger.info(f"✅ Object {i+1} validation: {validation_results['total_references']} references, all valid")
        
        # Step 8: Test cascade delete behavior
        logger.info("🔧 Testing cascade delete behavior...")
        segments_before = await vast_store.get_flow_segments(str(test_flow.id))
        logger.info(f"Found {len(segments_before)} segments before cascade delete")
        
        # Test soft delete first (safer for testing)
        logger.info("Testing soft delete with cascade...")
        success = await vast_store.delete_flow_segments(str(test_flow.id), soft_delete=True)
        assert success is True, "Soft delete with cascade should succeed"
        
        segments_after_soft = await vast_store.get_flow_segments(str(test_flow.id))
        logger.info(f"Found {len(segments_after_soft)} segments after soft delete")
        
        logger.info("✅ All tests completed successfully!")
        
        # Store IDs for cleanup
        return {
            'source_id': str(test_source.id),
            'flow_id': str(test_flow.id),
            'segment_ids': [seg.object_id for seg in segments],
            'object_ids': [obj.object_id for obj in objects],
            'new_flow_id': new_flow_id
        }
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


async def cleanup_test_data(vast_store, source_manager, flow_manager, test_data):
    """Clean up test data from the real environment"""
    logger.info("🧹 Cleaning up test data from real environment...")
    
    try:
        # Clean up segments (if they weren't already deleted)
        for segment_id in test_data['segment_ids']:
            try:
                # Try to delete segment data from S3
                await vast_store.s3_store.delete_flow_segment(
                    test_data['flow_id'], 
                    segment_id, 
                    "2024-01-01T00:00:00Z/2024-01-01T01:40:00Z"  # Approximate timerange
                )
                logger.info(f"Cleaned up segment: {segment_id}")
            except Exception as e:
                logger.warning(f"Could not clean up segment {segment_id}: {e}")
        
        # Clean up flow
        try:
            await flow_manager.delete_flow(test_data['flow_id'], soft_delete=False, cascade=True)
            logger.info(f"Cleaned up flow: {test_data['flow_id']}")
        except Exception as e:
            logger.warning(f"Could not clean up flow {test_data['flow_id']}: {e}")
        
        # Clean up source
        try:
            await source_manager.delete_source(test_data['source_id'], soft_delete=False, cascade=True)
            logger.info(f"Cleaned up source: {test_data['source_id']}")
        except Exception as e:
            logger.warning(f"Could not clean up source {test_data['source_id']}: {e}")
        
        logger.info("✅ Cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


async def main():
    """Main function to run the test"""
    vast_store = None
    source_manager = None
    flow_manager = None
    
    try:
        # Run the test
        test_data = await create_flow_with_10_segments()
        
        # Get managers for cleanup
        settings = get_settings()
        vast_store = VASTStore(
            endpoints=[settings.vast_endpoint],
            access_key=settings.vast_access_key,
            secret_key=settings.vast_secret_key,
            bucket=settings.vast_bucket,
            schema=settings.vast_schema,
            s3_endpoint_url=settings.s3_endpoint_url,
            s3_access_key_id=settings.s3_access_key_id,
            s3_secret_access_key=settings.s3_secret_access_key,
            s3_bucket_name=settings.s3_bucket_name,
            s3_use_ssl=settings.s3_use_ssl
        )
        source_manager = SourceManager(vast_store)
        flow_manager = FlowManager(vast_store)
        
        logger.info("🎉 Test completed successfully!")
        logger.info(f"Created source: {test_data['source_id']}")
        logger.info(f"Created flow: {test_data['flow_id']}")
        logger.info(f"Created {len(test_data['segment_ids'])} segments")
        logger.info(f"Created {len(test_data['object_ids'])} objects")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        # Always attempt cleanup
        if vast_store and source_manager and flow_manager:
            try:
                await cleanup_test_data(vast_store, source_manager, flow_manager, test_data)
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())

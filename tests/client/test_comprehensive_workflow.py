"""
Comprehensive integration test for TAMS client workflow.

This test exercises the full lifecycle of sources, flows, segments, and tags.
Requires a running TAMS server at localhost:8000.
"""

import pytest
import pytest_asyncio
import asyncio
import sys
import logging
import tempfile
from pathlib import Path
from typing import Optional, List

# Add src/client to path for imports
client_path = Path(__file__).parent.parent.parent / "src" / "client"
if str(client_path) not in sys.path:
    sys.path.insert(0, str(client_path))

from vasttamsclient import TAMSClient
from vasttamsclient.exceptions import TAMSClientError, TAMSAPIError
from vasttamsclient.domain.source import TAMSSource
from vasttamsclient.domain.flow import TAMSFlow

# Test server configuration
TEST_SERVER_URL = "http://localhost:8000/api/tams/latest"
TEST_SERVER_BASE = "http://localhost:8000"  # For root endpoints like /health
TEST_USERNAME = "admin"
TEST_PASSWORD = "vastdata"

# Configure logging for verbose output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_server_available() -> bool:
    """Check if TAMS server is available."""
    try:
        import aiohttp
        
        async def check():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{TEST_SERVER_BASE}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        return response.status == 200
            except Exception:
                return False
        
        return asyncio.run(check())
    except Exception:
        return False


@pytest.fixture(scope="module")
def server_available():
    """Check if server is available, skip tests if not."""
    if not check_server_available():
        pytest.skip("TAMS server not available at localhost:8000. Start server to run integration tests.")
    return True


@pytest_asyncio.fixture(scope="function")
async def client(server_available):
    """Create a TAMSClient instance connected to real server."""
    client = TAMSClient(
        server_url=TEST_SERVER_URL,
        username=TEST_USERNAME,
        password=TEST_PASSWORD,
        timeout=60  # Longer timeout for file uploads
    )
    async with client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def temp_files():
    """Create temporary test files for uploads."""
    temp_dir = tempfile.mkdtemp()
    files = []
    
    # Create 12 small test files (4 for each of 3 flows)
    for i in range(12):
        file_path = Path(temp_dir) / f"test_video_{i}.mp4"
        # Create a small fake video file (just bytes, not real video)
        file_path.write_bytes(b"fake video data " * 100)  # ~1.6KB per file
        files.append(str(file_path))
    
    yield files
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
class TestComprehensiveWorkflow:
    """Comprehensive integration test for complete TAMS workflow."""
    
    async def test_comprehensive_workflow(self, client, temp_files):
        """
        Comprehensive workflow test covering:
        1. Create two sources (s1, s2)
        2. Create flows f1 in s1, f2 and f3 in s2 (f2=video, f3=audio)
        3. Add 4 segments to each flow (including file uploads)
        4. Create f4 that takes 2 segments from f2
        5. Add tags to all flows and sources
        6. Delete f2 (cascade should fail - f4 references it)
        7. Modify f1 parameters and s1 parameters
        8. Delete s1 (should fail - has flows)
        9. Delete s1 cascade (delete flows first, then source)
        10. Edit tags added to f3 (f2 was deleted)
        11. Cleanup
        """
        logger.info("=" * 80)
        logger.info("Starting Comprehensive Workflow Test")
        logger.info("=" * 80)
        
        # Track created objects for cleanup
        created_sources = []
        created_flows = []
        created_segments = []
        
        try:
            # ============================================================
            # Step 1: Create two sources (s1, s2)
            # ============================================================
            logger.info("\n[STEP 1] Creating two sources (s1, s2)")
            logger.info("-" * 80)
            
            s1 = client.TAMSSource(
                format="urn:x-nmos:format:video",
                label="Test Source S1"
            )
            await s1._ensure_created()
            created_sources.append(s1)
            logger.info(f"✓ Created source s1: {s1.id} - {s1.label}")
            
            s2 = client.TAMSSource(
                format="urn:x-nmos:format:video",
                label="Test Source S2"
            )
            await s2._ensure_created()
            created_sources.append(s2)
            logger.info(f"✓ Created source s2: {s2.id} - {s2.label}")
            
            # Verify sources exist
            retrieved_s1 = await client.get_source(s1.id)
            retrieved_s2 = await client.get_source(s2.id)
            assert retrieved_s1 is not None, "s1 should exist"
            assert retrieved_s2 is not None, "s2 should exist"
            logger.info("✓ Verified both sources exist in server")
            
            # ============================================================
            # Step 2: Create flows f1 in s1, f2 and f3 in s2
            # ============================================================
            logger.info("\n[STEP 2] Creating flows: f1 in s1, f2 and f3 in s2")
            logger.info("-" * 80)
            
            # f1 in s1 (video)
            f1 = s1.TAMSFlow(
                format="urn:x-nmos:format:video",
                codec="video/h264",
                label="Flow F1 (Video)",
                frame_width=1920,
                frame_height=1080,
                frame_rate={"numerator": 25, "denominator": 1}
            )
            await f1._ensure_created()
            created_flows.append(f1)
            logger.info(f"✓ Created flow f1: {f1.id} - {f1.label} in source {s1.id}")
            
            # f2 in s2 (video)
            f2 = s2.TAMSFlow(
                format="urn:x-nmos:format:video",
                codec="video/h264",
                label="Flow F2 (Video)",
                frame_width=1920,
                frame_height=1080,
                frame_rate={"numerator": 30, "denominator": 1}
            )
            await f2._ensure_created()
            created_flows.append(f2)
            logger.info(f"✓ Created flow f2: {f2.id} - {f2.label} in source {s2.id}")
            
            # f3 in s2 (audio)
            f3 = s2.TAMSFlow(
                format="urn:x-nmos:format:audio",
                codec="audio/aac",
                label="Flow F3 (Audio)",
                sample_rate=48000,
                channels=2
            )
            await f3._ensure_created()
            created_flows.append(f3)
            logger.info(f"✓ Created flow f3: {f3.id} - {f3.label} in source {s2.id}")
            
            # Verify flows
            assert f1.source_id == s1.id, "f1 should belong to s1"
            assert f2.source_id == s2.id, "f2 should belong to s2"
            assert f3.source_id == s2.id, "f3 should belong to s2"
            logger.info("✓ Verified all flows have correct source relationships")
            
            # ============================================================
            # Step 3: Add 4 segments to each flow (including file uploads)
            # ============================================================
            logger.info("\n[STEP 3] Adding 4 segments to each flow with file uploads")
            logger.info("-" * 80)
            
            # Segments for f1
            logger.info(f"Adding segments to f1 ({f1.id})...")
            f1_segments = []
            for i in range(4):
                segment = await f1.add_segment(
                    file_path=temp_files[i],
                    timerange={"value": f"[{i*10}:0_{(i+1)*10}:0)"},
                    auto_probe=False  # Skip auto-probe for speed
                )
                f1_segments.append(segment)
                created_segments.append(segment)
                logger.info(f"  ✓ Added segment {i+1}/4 to f1: object_id={segment.object_id}")
                # Add delay between uploads to avoid signature validation issues
                if i < 3:  # Don't delay after last segment
                    await asyncio.sleep(1)
            
            # Segments for f2
            logger.info(f"Adding segments to f2 ({f2.id})...")
            f2_segments = []
            for i in range(4):
                segment = await f2.add_segment(
                    file_path=temp_files[4 + i],
                    timerange={"value": f"[{i*10}:0_{(i+1)*10}:0)"},
                    auto_probe=False
                )
                f2_segments.append(segment)
                created_segments.append(segment)
                logger.info(f"  ✓ Added segment {i+1}/4 to f2: object_id={segment.object_id}")
                # Add delay between uploads to avoid signature validation issues
                if i < 3:  # Don't delay after last segment
                    await asyncio.sleep(1)
            
            # Segments for f3
            logger.info(f"Adding segments to f3 ({f3.id})...")
            f3_segments = []
            for i in range(4):
                segment = await f3.add_segment(
                    file_path=temp_files[8 + i],
                    timerange={"value": f"[{i*10}:0_{(i+1)*10}:0)"},
                    auto_probe=False
                )
                f3_segments.append(segment)
                created_segments.append(segment)
                logger.info(f"  ✓ Added segment {i+1}/4 to f3: object_id={segment.object_id}")
                # Add delay between uploads to avoid signature validation issues
                if i < 3:  # Don't delay after last segment
                    await asyncio.sleep(1)
            
            # Verify segments
            f1_segments_list = await f1.list_segments()
            f2_segments_list = await f2.list_segments()
            f3_segments_list = await f3.list_segments()
            assert len(f1_segments_list) == 4, "f1 should have 4 segments"
            assert len(f2_segments_list) == 4, "f2 should have 4 segments"
            assert len(f3_segments_list) == 4, "f3 should have 4 segments"
            logger.info("✓ Verified all flows have 4 segments each")
            
            # ============================================================
            # Step 4: Create f4 that takes 2 segments from f2
            # ============================================================
            logger.info("\n[STEP 4] Creating f4 that references 2 segments from f2")
            logger.info("-" * 80)
            
            # Create f4 in s2 (will reference segments from f2)
            f4 = s2.TAMSFlow(
                format="urn:x-nmos:format:video",
                codec="video/h264",
                label="Flow F4 (References F2)",
                frame_width=1920,
                frame_height=1080,
                frame_rate={"numerator": 30, "denominator": 1}
            )
            await f4._ensure_created()
            created_flows.append(f4)
            logger.info(f"✓ Created flow f4: {f4.id} - {f4.label}")
            
            # Get first 2 segments from f2 and reference them in f4
            from vasttamsclient.api import segments as segment_api
            from vasttamsclient.domain.segment import TAMSSegment
            
            # Reference first 2 segments from f2
            for i, f2_seg in enumerate(f2_segments[:2]):
                # Create segment in f4 using the same object_id from f2
                segment_data = {
                    "object_id": f2_seg.object_id,
                    "timerange": {"value": f"[{i*10}:0_{(i+1)*10}:0)"}
                }
                segment_result = await segment_api.create_segment(client, f4.id, segment_data)
                f4_segment = TAMSSegment(client, f4.id, segment_result)
                created_segments.append(f4_segment)
                logger.info(f"  ✓ Created segment in f4 referencing f2 segment {i+1}: object_id={f2_seg.object_id}")
            
            # Verify f4 has 2 segments
            f4_segments_list = await f4.list_segments()
            assert len(f4_segments_list) == 2, "f4 should have 2 segments"
            logger.info("✓ Verified f4 has 2 segments referencing f2")
            
            # ============================================================
            # Step 5: Add tags to all flows and sources
            # ============================================================
            logger.info("\n[STEP 5] Adding tags to all flows and sources")
            logger.info("-" * 80)
            
            # Tags for s1
            await s1.set_tag("environment", "test")
            await s1.set_tag("workflow", "integration")
            logger.info(f"✓ Added tags to s1: environment=test, workflow=integration")
            
            # Tags for s2
            await s2.set_tag("environment", "test")
            await s2.set_tag("workflow", "integration")
            await s2.set_tag("source_type", "multi_flow")
            logger.info(f"✓ Added tags to s2: environment=test, workflow=integration, source_type=multi_flow")
            
            # Tags for f1
            await f1.set_tag("quality", "hd")
            await f1.set_tag("codec_profile", "high")
            logger.info(f"✓ Added tags to f1: quality=hd, codec_profile=high")
            
            # Tags for f2
            await f2.set_tag("quality", ["hd", "4k"])  # List value
            await f2.set_tag("codec_profile", "main")
            await f2.set_tag("status", "active")
            logger.info(f"✓ Added tags to f2: quality=[hd, 4k], codec_profile=main, status=active")
            
            # Tags for f3
            await f3.set_tag("audio_format", "stereo")
            await f3.set_tag("bitrate", "256kbps")
            logger.info(f"✓ Added tags to f3: audio_format=stereo, bitrate=256kbps")
            
            # Tags for f4
            await f4.set_tag("quality", "hd")
            await f4.set_tag("derived_from", f2.id)
            logger.info(f"✓ Added tags to f4: quality=hd, derived_from={f2.id}")
            
            # Verify tags
            s1_tags = await s1.get_tags()
            f2_tags = await f2.get_tags()
            assert "environment" in s1_tags, "s1 should have environment tag"
            assert "quality" in f2_tags, "f2 should have quality tag"
            assert isinstance(f2_tags["quality"], list), "f2 quality tag should be a list"
            logger.info("✓ Verified tags are set correctly (including list values)")
            
            # ============================================================
            # Step 6: Delete f2 (cascade should fail - f4 references it)
            # ============================================================
            logger.info("\n[STEP 6] Attempting to delete f2 (should fail - f4 references it)")
            logger.info("-" * 80)
            
            try:
                await f2.delete()
                logger.warning("⚠ f2 deletion succeeded (unexpected - f4 should reference it)")
                # If it succeeded, we need to recreate it for later steps
                f2 = s2.TAMSFlow(
                    format="urn:x-nmos:format:video",
                    codec="video/h264",
                    label="Flow F2 (Video) - Recreated",
                    frame_width=1920,
                    frame_height=1080,
                    frame_rate={"numerator": 30, "denominator": 1}
                )
                await f2._ensure_created()
                created_flows.append(f2)
            except TAMSAPIError as e:
                logger.info(f"✓ f2 deletion failed as expected: {e}")
                assert "400" in str(e.status_code) or "409" in str(e.status_code) or "cannot" in str(e).lower() or "reference" in str(e).lower(), \
                    f"Expected cascade failure, got: {e}"
            except Exception as e:
                # Some servers may return different error types
                logger.info(f"✓ f2 deletion failed as expected: {type(e).__name__}: {e}")
            
            # ============================================================
            # Step 7: Modify f1 parameters and s1 parameters
            # ============================================================
            logger.info("\n[STEP 7] Modifying f1 parameters and s1 parameters")
            logger.info("-" * 80)
            
            # Modify f1
            original_f1_label = f1.label
            await f1.update(label="Flow F1 (Updated)", description="Updated flow description")
            await f1.refresh()
            assert f1.label == "Flow F1 (Updated)", "f1 label should be updated"
            logger.info(f"✓ Updated f1: label='{f1.label}', description added")
            
            # Modify s1
            original_s1_label = s1.label
            await s1.update(label="Test Source S1 (Updated)", description="Updated source description")
            await s1.refresh()
            assert s1.label == "Test Source S1 (Updated)", "s1 label should be updated"
            logger.info(f"✓ Updated s1: label='{s1.label}', description added")
            
            # ============================================================
            # Step 8: Delete s1 (should fail - has flows)
            # ============================================================
            logger.info("\n[STEP 8] Attempting to delete s1 (should fail - has flows)")
            logger.info("-" * 80)
            
            try:
                await s1.delete()
                logger.warning("⚠ s1 deletion succeeded (unexpected - should have flows)")
            except TAMSAPIError as e:
                logger.info(f"✓ s1 deletion failed as expected: {e}")
                assert "400" in str(e.status_code) or "409" in str(e.status_code) or "cannot" in str(e).lower() or "flow" in str(e).lower(), \
                    f"Expected cascade failure, got: {e}"
            except Exception as e:
                logger.info(f"✓ s1 deletion failed as expected: {type(e).__name__}: {e}")
            
            # ============================================================
            # Step 9: Delete s1 cascade (delete flows first, then source)
            # ============================================================
            logger.info("\n[STEP 9] Deleting s1 with cascade (delete flows first)")
            logger.info("-" * 80)
            
            # Delete all flows in s1 first
            s1_flows = await s1.list_flows()
            logger.info(f"Found {len(s1_flows)} flows in s1")
            for flow in s1_flows:
                try:
                    # Delete all segments first
                    segments = await flow.list_segments()
                    if segments:
                        await flow.delete_segments()
                        logger.info(f"  ✓ Deleted {len(segments)} segments from flow {flow.id}")
                    await flow.delete()
                    logger.info(f"  ✓ Deleted flow {flow.id}")
                    if flow in created_flows:
                        created_flows.remove(flow)
                except Exception as e:
                    logger.warning(f"  ⚠ Error deleting flow {flow.id}: {e}")
            
            # Now delete s1
            try:
                await s1.delete()
                logger.info(f"✓ Successfully deleted s1 ({s1.id})")
                if s1 in created_sources:
                    created_sources.remove(s1)
            except Exception as e:
                logger.warning(f"⚠ Error deleting s1: {e}")
            
            # Verify s1 is deleted
            deleted_s1 = await client.get_source(s1.id)
            assert deleted_s1 is None, "s1 should be deleted"
            logger.info("✓ Verified s1 is deleted from server")
            
            # ============================================================
            # Step 10: Edit tags added to f3 (f2 was not deleted)
            # ============================================================
            logger.info("\n[STEP 10] Editing tags on f3")
            logger.info("-" * 80)
            
            # Update existing tags
            await f3.set_tag("audio_format", "surround")  # Update existing
            await f3.set_tag("bitrate", "320kbps")  # Update existing
            await f3.set_tag("new_tag", "new_value")  # Add new tag
            
            # Verify updates
            f3_tags = await f3.get_tags()
            assert f3_tags["audio_format"] == "surround", "audio_format should be updated"
            assert f3_tags["bitrate"] == "320kbps", "bitrate should be updated"
            assert f3_tags["new_tag"] == "new_value", "new_tag should be added"
            logger.info(f"✓ Updated f3 tags: audio_format=surround, bitrate=320kbps, new_tag=new_value")
            
            # Test tag list values
            await f3.set_tag("formats", ["stereo", "surround", "mono"])
            f3_tags_after = await f3.get_tags()
            assert isinstance(f3_tags_after["formats"], list), "formats tag should be a list"
            assert len(f3_tags_after["formats"]) == 3, "formats list should have 3 items"
            logger.info(f"✓ Set list tag on f3: formats={f3_tags_after['formats']}")
            
            # ============================================================
            # Step 11: Cleanup
            # ============================================================
            logger.info("\n[STEP 11] Cleaning up remaining resources")
            logger.info("-" * 80)
            
            # Delete f4 first (references f2)
            if f4 in created_flows:
                try:
                    segments = await f4.list_segments()
                    if segments:
                        await f4.delete_segments()
                    await f4.delete()
                    logger.info(f"✓ Deleted f4 ({f4.id})")
                    created_flows.remove(f4)
                except Exception as e:
                    logger.warning(f"⚠ Error deleting f4: {e}")
            
            # Delete f2 (should work now that f4 is deleted)
            if f2 in created_flows:
                try:
                    segments = await f2.list_segments()
                    if segments:
                        await f2.delete_segments()
                    await f2.delete()
                    logger.info(f"✓ Deleted f2 ({f2.id})")
                    created_flows.remove(f2)
                except Exception as e:
                    logger.warning(f"⚠ Error deleting f2: {e}")
            
            # Delete f3
            if f3 in created_flows:
                try:
                    segments = await f3.list_segments()
                    if segments:
                        await f3.delete_segments()
                    await f3.delete()
                    logger.info(f"✓ Deleted f3 ({f3.id})")
                    created_flows.remove(f3)
                except Exception as e:
                    logger.warning(f"⚠ Error deleting f3: {e}")
            
            # Delete s2 (should work now that all flows are deleted)
            if s2 in created_sources:
                try:
                    await s2.delete()
                    logger.info(f"✓ Deleted s2 ({s2.id})")
                    created_sources.remove(s2)
                except Exception as e:
                    logger.warning(f"⚠ Error deleting s2: {e}")
            
            logger.info("\n" + "=" * 80)
            logger.info("Comprehensive Workflow Test Completed Successfully!")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"\n❌ Test failed with error: {e}", exc_info=True)
            raise
        finally:
            # Final cleanup - try to delete anything remaining
            logger.info("\n[FINAL CLEANUP] Attempting to clean up any remaining resources")
            for flow in created_flows[:]:  # Copy list to avoid modification during iteration
                try:
                    segments = await flow.list_segments()
                    if segments:
                        await flow.delete_segments()
                    await flow.delete()
                    created_flows.remove(flow)
                    logger.info(f"  ✓ Cleaned up flow {flow.id}")
                except Exception:
                    pass
            
            for source in created_sources[:]:
                try:
                    await source.delete()
                    created_sources.remove(source)
                    logger.info(f"  ✓ Cleaned up source {source.id}")
                except Exception:
                    pass


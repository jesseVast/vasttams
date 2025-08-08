"""
Test 403 Forbidden responses for read-only flows (TAMS API v6.0 compliance)

This test suite verifies that the application correctly returns 403 Forbidden
responses when attempting to modify flows that are marked as read-only.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from app.vast_store import VASTStore
from app.flows import FlowManager
from app.models import Source, VideoFlow, Tags
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class Test403Compliance:
    """Test 403 Forbidden responses for read-only flows"""

    def setup_method(self, method):
        """Setup test environment with real database."""
        self.settings = get_settings()
        self.store = VASTStore(
            endpoint=self.settings.vast_endpoint,
            access_key=self.settings.vast_access_key,
            secret_key=self.settings.vast_secret_key,
            bucket=self.settings.vast_bucket,
            schema=self.settings.vast_schema,
            s3_endpoint_url=self.settings.s3_endpoint_url,
            s3_access_key_id=self.settings.s3_access_key_id,
            s3_secret_access_key=self.settings.s3_secret_access_key,
            s3_bucket_name=self.settings.s3_bucket_name,
            s3_use_ssl=self.settings.s3_use_ssl
        )
        self.flow_manager = FlowManager(self.store)
        asyncio.run(self._async_setup())

    async def _async_setup(self):
        """Asynchronous setup for database connections."""
        try:
            # Create test source
            self.test_source = Source(
                id=uuid.uuid4(),
                format="urn:x-nmos:format:video",
                label="Test Source for 403",
                created_by="test-user"
            )
            await self.store.create_source(self.test_source)
            
            # Create test flow (initially not read-only)
            self.test_flow = VideoFlow(
                id=uuid.uuid4(),
                source_id=self.test_source.id,
                format="urn:x-nmos:format:video",
                codec="video/mp4",
                label="Test Flow for 403",
                frame_width=1920,
                frame_height=1080,
                frame_rate="25/1",
                read_only=False,
                created_by="test-user"
            )
            await self.store.create_flow(self.test_flow)
            
            logger.info("✅ Test setup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Test setup failed: {e}")
            raise

    def teardown_method(self, method):
        """Cleanup test environment."""
        try:
            # Clean up test data
            asyncio.run(self._cleanup())
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    async def _cleanup(self):
        """Clean up test data."""
        try:
            # Delete test flow and source
            await self.store.delete_flow(str(self.test_flow.id), soft_delete=False)
            await self.store.delete_source(str(self.test_source.id), soft_delete=False)
            logger.info("✅ Test cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    @pytest.mark.asyncio
    async def test_403_on_readonly_flow_update(self):
        """Test that updating a read-only flow returns 403 Forbidden"""
        logger.info("🧪 Testing 403 response on read-only flow update...")
        
        # Set flow to read-only
        self.test_flow.read_only = True
        await self.store.update_flow(str(self.test_flow.id), self.test_flow)
        
        # Try to update the read-only flow
        updated_flow = VideoFlow(
            id=self.test_flow.id,
            source_id=self.test_flow.source_id,
            format=self.test_flow.format,
            codec=self.test_flow.codec,
            label="Updated Label - Should Fail",
            frame_width=1920,
            frame_height=1080,
            frame_rate="25/1",
            read_only=True,
            created_by="test-user"
        )
        
        try:
            await self.flow_manager.update_flow(str(self.test_flow.id), updated_flow)
            assert False, "Should have raised HTTPException with 403 status"
        except Exception as e:
            # Check that the exception is an HTTPException with 403 status
            assert "403" in str(e) or "Forbidden" in str(e), f"Expected 403 error, got: {e}"
            # Verify the flow wasn't actually updated
            current_flow = await self.store.get_flow(str(self.test_flow.id))
            assert current_flow.label != "Updated Label - Should Fail", "Flow was updated despite being read-only"
            logger.info("✅ 403 compliance verified - read-only flow was not updated")

    @pytest.mark.asyncio
    async def test_403_on_readonly_flow_delete(self):
        """Test that deleting a read-only flow returns 403 Forbidden"""
        logger.info("🧪 Testing 403 response on read-only flow deletion...")
        
        # Set flow to read-only
        self.test_flow.read_only = True
        await self.store.update_flow(str(self.test_flow.id), self.test_flow)
        
        # Try to delete the read-only flow
        try:
            await self.flow_manager.delete_flow(str(self.test_flow.id), soft_delete=True)
            assert False, "Should have raised HTTPException with 403 status"
        except Exception as e:
            # Check that the exception is an HTTPException with 403 status
            assert "403" in str(e) or "Forbidden" in str(e), f"Expected 403 error, got: {e}"
            # Verify the flow still exists
            current_flow = await self.store.get_flow(str(self.test_flow.id))
            assert current_flow is not None, "Flow was deleted despite being read-only"
            logger.info("✅ 403 compliance verified - read-only flow was not deleted")

    @pytest.mark.asyncio
    async def test_403_on_readonly_flow_tag_update(self):
        """Test that updating tags on a read-only flow returns 403 Forbidden"""
        logger.info("🧪 Testing 403 response on read-only flow tag update...")
        
        # Set flow to read-only
        self.test_flow.read_only = True
        await self.store.update_flow(str(self.test_flow.id), self.test_flow)
        
        # Try to update tags on the read-only flow using FlowManager
        try:
            await self.flow_manager.update_tag(str(self.test_flow.id), "test_tag", "new_value")
            assert False, "Should have raised HTTPException with 403 status"
        except Exception as e:
            # Check that the exception is an HTTPException with 403 status
            assert "403" in str(e) or "Forbidden" in str(e), f"Expected 403 error, got: {e}"
            # Check that tags weren't updated
            current_flow = await self.store.get_flow(str(self.test_flow.id))
            assert not current_flow.tags or "test_tag" not in current_flow.tags, "Tags were updated despite being read-only"
            logger.info("✅ 403 compliance verified - read-only flow tags were not updated")

    @pytest.mark.asyncio
    async def test_403_on_readonly_flow_description_update(self):
        """Test that updating description on a read-only flow returns 403 Forbidden"""
        logger.info("🧪 Testing 403 response on read-only flow description update...")
        
        # Set flow to read-only
        self.test_flow.read_only = True
        await self.store.update_flow(str(self.test_flow.id), self.test_flow)
        
        # Try to update description on the read-only flow using FlowManager
        try:
            await self.flow_manager.update_description(str(self.test_flow.id), "Updated Description - Should Fail")
            assert False, "Should have raised HTTPException with 403 status"
        except Exception as e:
            # Check that the exception is an HTTPException with 403 status
            assert "403" in str(e) or "Forbidden" in str(e), f"Expected 403 error, got: {e}"
            # Check that description wasn't updated
            current_flow = await self.store.get_flow(str(self.test_flow.id))
            assert current_flow.description != "Updated Description - Should Fail", "Description was updated despite being read-only"
            logger.info("✅ 403 compliance verified - read-only flow description was not updated")

    @pytest.mark.asyncio
    async def test_403_on_readonly_flow_label_update(self):
        """Test that updating label on a read-only flow returns 403 Forbidden"""
        logger.info("🧪 Testing 403 response on read-only flow label update...")
        
        # Set flow to read-only
        self.test_flow.read_only = True
        await self.store.update_flow(str(self.test_flow.id), self.test_flow)
        
        # Try to update label on the read-only flow using FlowManager
        try:
            await self.flow_manager.update_label(str(self.test_flow.id), "Updated Label - Should Fail")
            assert False, "Should have raised HTTPException with 403 status"
        except Exception as e:
            # Check that the exception is an HTTPException with 403 status
            assert "403" in str(e) or "Forbidden" in str(e), f"Expected 403 error, got: {e}"
            # Check that label wasn't updated
            current_flow = await self.store.get_flow(str(self.test_flow.id))
            assert current_flow.label != "Updated Label - Should Fail", "Label was updated despite being read-only"
            logger.info("✅ 403 compliance verified - read-only flow label was not updated")

    @pytest.mark.asyncio
    async def test_readonly_flow_can_be_set(self):
        """Test that read-only status can be set on a flow"""
        logger.info("🧪 Testing that read-only status can be set...")
        
        # Set flow to read-only
        self.test_flow.read_only = True
        await self.store.update_flow(str(self.test_flow.id), self.test_flow)
        
        # Verify the read-only status was set
        current_flow = await self.store.get_flow(str(self.test_flow.id))
        assert current_flow.read_only is True, "Read-only status was not set correctly"
        logger.info("✅ Read-only status can be set correctly")

    @pytest.mark.asyncio
    async def test_non_readonly_flow_can_be_modified(self):
        """Test that non-read-only flows can be modified normally"""
        logger.info("🧪 Testing that non-read-only flows can be modified...")
        
        # Ensure flow is not read-only
        self.test_flow.read_only = False
        await self.store.update_flow(str(self.test_flow.id), self.test_flow)
        
        # Try to update the flow
        updated_flow = VideoFlow(
            id=self.test_flow.id,
            source_id=self.test_flow.source_id,
            format=self.test_flow.format,
            codec=self.test_flow.codec,
            label="Updated Label - Should Succeed",
            frame_width=1920,
            frame_height=1080,
            frame_rate="25/1",
            read_only=False,
            created_by="test-user"
        )
        
        await self.store.update_flow(str(self.test_flow.id), updated_flow)
        
        # Verify the update succeeded
        current_flow = await self.store.get_flow(str(self.test_flow.id))
        assert current_flow.label == "Updated Label - Should Succeed", "Flow was not updated when it should have been"
        logger.info("✅ Non-read-only flows can be modified normally") 
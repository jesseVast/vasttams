"""
Test webhook ownership implementation (TAMS API v6.0 compliance)

This test suite verifies that webhooks correctly support ownership fields
as required by the TAMS API v6.0 specification.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from app.vast_store import VASTStore
from app.models import WebhookPost, Webhook
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class TestWebhookOwnership:
    """Test webhook ownership implementation"""

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
        asyncio.run(self._async_setup())

    async def _async_setup(self):
        """Asynchronous setup for database connections."""
        try:
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
            # List and delete all test webhooks
            webhooks = await self.store.list_webhooks()
            for webhook in webhooks:
                if webhook.url.startswith("https://test-webhook"):
                    # Note: We don't have a delete_webhook method yet, so we'll just log
                    logger.info(f"Test webhook would be deleted: {webhook.url}")
            logger.info("✅ Test cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    @pytest.mark.asyncio
    async def test_webhook_creation_with_ownership(self):
        """Test that webhooks can be created with ownership fields"""
        logger.info("🧪 Testing webhook creation with ownership fields...")
        
        # Create webhook with ownership fields
        webhook_data = WebhookPost(
            url="https://test-webhook-ownership.com",
            api_key_name="Authorization",
            api_key_value="Bearer test-token",
            events=["flows/created", "flows/updated"],
            owner_id="test-user-123",
            created_by="test-admin"
        )
        
        success = await self.store.create_webhook(webhook_data)
        assert success is True, "Webhook creation should succeed"
        
        # Verify webhook was created with ownership fields
        webhooks = await self.store.list_webhooks()
        test_webhook = None
        for webhook in webhooks:
            if webhook.url == "https://test-webhook-ownership.com":
                test_webhook = webhook
                break
        
        assert test_webhook is not None, "Test webhook should be found"
        assert test_webhook.owner_id == "test-user-123", "Owner ID should be set correctly"
        assert test_webhook.created_by == "test-admin", "Created by should be set correctly"
        assert test_webhook.created is not None, "Created timestamp should be set"
        
        logger.info("✅ Webhook creation with ownership fields works correctly")

    @pytest.mark.asyncio
    async def test_webhook_creation_without_ownership(self):
        """Test that webhooks can be created without ownership fields (defaults)"""
        logger.info("🧪 Testing webhook creation without ownership fields...")
        
        # Create webhook without ownership fields
        webhook_data = WebhookPost(
            url="https://test-webhook-default.com",
            api_key_name="Authorization",
            api_key_value="Bearer test-token",
            events=["flows/deleted"]
        )
        
        success = await self.store.create_webhook(webhook_data)
        assert success is True, "Webhook creation should succeed"
        
        # Verify webhook was created with default ownership fields
        webhooks = await self.store.list_webhooks()
        test_webhook = None
        for webhook in webhooks:
            if webhook.url == "https://test-webhook-default.com":
                test_webhook = webhook
                break
        
        assert test_webhook is not None, "Test webhook should be found"
        assert test_webhook.owner_id == "system", "Owner ID should default to 'system'"
        assert test_webhook.created_by == "system", "Created by should default to 'system'"
        assert test_webhook.created is not None, "Created timestamp should be set"
        
        logger.info("✅ Webhook creation with default ownership fields works correctly")

    @pytest.mark.asyncio
    async def test_webhook_ownership_fields_in_model(self):
        """Test that Webhook model includes ownership fields"""
        logger.info("🧪 Testing Webhook model ownership fields...")
        
        # Create a webhook instance with ownership fields
        webhook = Webhook(
            url="https://test-model.com",
            api_key_name="Authorization",
            events=["flows/created"],
            owner_id="test-owner",
            created_by="test-creator",
            created=datetime.now(timezone.utc)
        )
        
        # Verify ownership fields are present
        assert webhook.owner_id == "test-owner", "Owner ID should be accessible"
        assert webhook.created_by == "test-creator", "Created by should be accessible"
        assert webhook.created is not None, "Created timestamp should be accessible"
        
        logger.info("✅ Webhook model ownership fields work correctly")

    @pytest.mark.asyncio
    async def test_webhook_post_model_ownership_fields(self):
        """Test that WebhookPost model includes ownership fields"""
        logger.info("🧪 Testing WebhookPost model ownership fields...")
        
        # Create a webhook post instance with ownership fields
        webhook_post = WebhookPost(
            url="https://test-post-model.com",
            api_key_name="Authorization",
            api_key_value="Bearer token",
            events=["flows/updated"],
            owner_id="test-owner-post",
            created_by="test-creator-post"
        )
        
        # Verify ownership fields are present
        assert webhook_post.owner_id == "test-owner-post", "Owner ID should be accessible"
        assert webhook_post.created_by == "test-creator-post", "Created by should be accessible"
        
        logger.info("✅ WebhookPost model ownership fields work correctly")

    @pytest.mark.asyncio
    async def test_webhook_listing_includes_ownership(self):
        """Test that webhook listing includes ownership fields"""
        logger.info("🧪 Testing webhook listing includes ownership fields...")
        
        # Create a webhook with ownership
        webhook_data = WebhookPost(
            url="https://test-webhook-listing.com",
            api_key_name="Authorization",
            api_key_value="Bearer test-token",
            events=["flows/created"],
            owner_id="listing-test-user",
            created_by="listing-test-admin"
        )
        
        await self.store.create_webhook(webhook_data)
        
        # List webhooks and verify ownership fields are included
        webhooks = await self.store.list_webhooks()
        test_webhook = None
        for webhook in webhooks:
            if webhook.url == "https://test-webhook-listing.com":
                test_webhook = webhook
                break
        
        assert test_webhook is not None, "Test webhook should be found in listing"
        assert hasattr(test_webhook, 'owner_id'), "Webhook should have owner_id field"
        assert hasattr(test_webhook, 'created_by'), "Webhook should have created_by field"
        assert hasattr(test_webhook, 'created'), "Webhook should have created field"
        
        logger.info("✅ Webhook listing includes ownership fields correctly")

    @pytest.mark.asyncio
    async def test_webhook_ownership_compliance(self):
        """Test that webhook ownership implementation complies with TAMS API v6.0"""
        logger.info("🧪 Testing webhook ownership TAMS API v6.0 compliance...")
        
        # Test that webhooks support ownership as implied by the specification
        # The spec mentions "suitable permissions (e.g. the owning user)" for webhooks
        
        webhook_data = WebhookPost(
            url="https://test-compliance.com",
            api_key_name="Authorization",
            api_key_value="Bearer compliance-token",
            events=["flows/created", "flows/updated", "flows/deleted"],
            owner_id="compliance-user",
            created_by="compliance-admin"
        )
        
        success = await self.store.create_webhook(webhook_data)
        assert success is True, "Webhook creation should succeed for compliance test"
        
        # Verify the webhook has ownership tracking
        webhooks = await self.store.list_webhooks()
        compliance_webhook = None
        for webhook in webhooks:
            if webhook.url == "https://test-compliance.com":
                compliance_webhook = webhook
                break
        
        assert compliance_webhook is not None, "Compliance webhook should be found"
        assert compliance_webhook.owner_id == "compliance-user", "Owner ID should be tracked"
        assert compliance_webhook.created_by == "compliance-admin", "Creator should be tracked"
        
        logger.info("✅ Webhook ownership implementation complies with TAMS API v6.0") 
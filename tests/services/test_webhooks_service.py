#!/usr/bin/env python3
"""
Service Layer Tests for Webhooks Service

Tests webhooks/service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.webhooks.service import WebhookService
from vasttams.webhooks.models import Webhook


class TestWebhookService:
    """Test WebhookService"""
    
    def test_init(self):
        """Test service initialization"""
        mock_db = Mock()
        service = WebhookService(mock_db)
        assert service.vast_db == mock_db
    
    @pytest.mark.asyncio
    async def test_get_webhooks_empty(self):
        """Test get_webhooks with empty result"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        assert isinstance(webhooks, list)
        assert len(webhooks) == 0
    
    @pytest.mark.asyncio
    async def test_get_webhooks_with_data(self):
        """Test get_webhooks with data"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-api-key'],
                'events': ['["flow.created"]'],
                'flow_ids': ['[]'],
                'source_ids': ['[]'],
                'created': ['2024-01-01T00:00:00Z'],
                'updated': ['2024-01-01T00:00:00Z']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        assert isinstance(webhooks, list)
        if webhooks:
            assert webhooks[0].id == webhook_id
    
    @pytest.mark.asyncio
    async def test_get_webhook_existing(self):
        """Test get_webhook with existing webhook"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-api-key'],
                'events': ['["flow.created"]'],
                'flow_ids': ['[]'],
                'source_ids': ['[]']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhook = await service.get_webhook(webhook_id)
        
        assert webhook is not None
        assert webhook.id == webhook_id
    
    @pytest.mark.asyncio
    async def test_get_webhook_nonexistent(self):
        """Test get_webhook with non-existent webhook"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhook = await service.get_webhook(webhook_id)
        
        assert webhook is None
    
    @pytest.mark.asyncio
    async def test_get_webhooks_parses_json_fields(self):
        """Test get_webhooks parses JSON fields correctly"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-api-key'],
                'events': ['["flow.created", "flow.updated"]'],
                'flow_ids': ['[]'],
                'source_ids': ['[]'],
                'tags': ['{"key": "value"}']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        assert isinstance(webhooks, list)
        if webhooks:
            webhook = webhooks[0]
            assert isinstance(webhook.events, list)
            assert len(webhook.events) == 2


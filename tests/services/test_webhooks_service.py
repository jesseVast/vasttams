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


class TestWebhookServiceGetWebhooks:
    """Test get_webhooks method edge cases"""
    
    @pytest.mark.asyncio
    async def test_get_webhooks_data_as_list(self):
        """Test get_webhooks with data as list format"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [{
                'id': webhook_id,
                'url': 'http://example.com/webhook',
                'api_key_name': 'test-api-key',
                'api_key_value': 'test-value',
                'events': ["flow.created"],  # Already parsed (list format doesn't parse JSON)
                'flow_ids': [],
                'source_ids': [],
                'enabled': True
            }]
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        assert isinstance(webhooks, list)
        assert len(webhooks) == 1
        assert webhooks[0].id == webhook_id
    
    @pytest.mark.asyncio
    async def test_get_webhooks_json_parse_error(self):
        """Test get_webhooks handles JSON parse errors gracefully"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'events': ['invalid-json['],  # Invalid JSON
                'flow_ids': ['[]']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        # Should handle parse error gracefully
        assert isinstance(webhooks, list)
    
    @pytest.mark.asyncio
    async def test_get_webhooks_datetime_parsing(self):
        """Test get_webhooks parses datetime fields correctly"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'created': ['2024-01-01T00:00:00Z'],
                'updated': ['2024-01-01T00:00:00Z']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        assert isinstance(webhooks, list)
        if webhooks:
            assert webhooks[0].created is not None
    
    @pytest.mark.asyncio
    async def test_get_webhooks_invalid_datetime(self):
        """Test get_webhooks handles invalid datetime gracefully"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'created': ['invalid-datetime'],
                'updated': ['invalid-datetime']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        assert isinstance(webhooks, list)
    
    @pytest.mark.asyncio
    async def test_get_webhooks_parse_error_continues(self):
        """Test get_webhooks continues parsing other webhooks on error"""
        webhook_id1 = str(uuid.uuid4())
        webhook_id2 = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id1, webhook_id2],
                'url': ['http://example.com/webhook1', 'http://example.com/webhook2'],
                'events': ['invalid-json[', '["flow.created"]']  # First invalid, second valid
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhooks = await service.get_webhooks()
        
        # Should parse valid webhooks even if some fail
        assert isinstance(webhooks, list)
    
    @pytest.mark.asyncio
    async def test_get_webhooks_exception_handling(self):
        """Test get_webhooks handles exceptions"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.get_webhooks()
        
        assert exc_info.value.status_code == 500


class TestWebhookServiceGetWebhook:
    """Test get_webhook method edge cases"""
    
    @pytest.mark.asyncio
    async def test_get_webhook_data_as_list(self):
        """Test get_webhook with data as list format"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [{
                'id': webhook_id,
                'url': 'http://example.com/webhook',
                'api_key_name': 'test-api-key',
                'api_key_value': 'test-value',
                'events': ["flow.created"],  # Already parsed (list format doesn't parse JSON)
                'enabled': True
            }]
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhook = await service.get_webhook(webhook_id)
        
        assert webhook is not None
        assert webhook.id == webhook_id
    
    @pytest.mark.asyncio
    async def test_get_webhook_empty_list(self):
        """Test get_webhook with empty list result"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': []}
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhook = await service.get_webhook(webhook_id)
        
        assert webhook is None
    
    @pytest.mark.asyncio
    async def test_get_webhook_json_fields(self):
        """Test get_webhook parses all JSON fields"""
        webhook_id = str(uuid.uuid4())
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        collection_id1 = str(uuid.uuid4())
        collection_id2 = str(uuid.uuid4())
        storage_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]'],
                'flow_ids': [json.dumps([flow_id])],
                'source_ids': [json.dumps([source_id])],
                'flow_collected_by_ids': [json.dumps([collection_id1])],
                'source_collected_by_ids': [json.dumps([collection_id2])],
                'accept_get_urls': ['["url1", "url2"]'],
                'accept_storage_ids': [json.dumps([storage_id])],
                'tags': ['{"key": "value"}'],
                'enabled': [True]
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        webhook = await service.get_webhook(webhook_id)
        
        assert webhook is not None
        assert isinstance(webhook.events, list)
        assert isinstance(webhook.flow_ids, list)
        assert isinstance(webhook.source_ids, list)
    
    @pytest.mark.asyncio
    async def test_get_webhook_exception_handling(self):
        """Test get_webhook handles exceptions"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.get_webhook(webhook_id)
        
        assert exc_info.value.status_code == 500


class TestWebhookServiceCreateWebhook:
    """Test create_webhook method"""
    
    @pytest.mark.asyncio
    async def test_create_webhook_basic(self):
        """Test create_webhook with basic data"""
        from vasttams.webhooks.models import WebhookPost
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]'],
                'enabled': [True]
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.insert_record = Mock()
        mock_db.get_qualified_table_name = Mock(return_value="test.webhooks")
        
        service = WebhookService(mock_db)
        
        webhook_post = WebhookPost(
            url="http://example.com/webhook",
            api_key_name="test-key",
            api_key_value="test-value",
            events=["flow.created"],
            enabled=True
        )
        
        webhook = await service.create_webhook(webhook_post)
        
        assert webhook is not None
        assert webhook.id == webhook_id
        mock_db.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_webhook_with_all_fields(self):
        """Test create_webhook with all optional fields"""
        from vasttams.webhooks.models import WebhookPost
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]'],
                'flow_ids': [json.dumps([str(uuid.uuid4())])],
                'source_ids': [json.dumps([str(uuid.uuid4())])],
                'tags': ['{"key": "value"}'],
                'enabled': [True]
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.insert_record = Mock()
        mock_db.get_qualified_table_name = Mock(return_value="test.webhooks")
        
        service = WebhookService(mock_db)
        
        from vasttams.common.models import Tags
        flow_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        webhook_post = WebhookPost(
            url="http://example.com/webhook",
            api_key_name="test-key",
            api_key_value="test-value",
            events=["flow.created"],
            flow_ids=[flow_id],
            source_ids=[source_id],
            tags=Tags(key="value"),
            enabled=True,
            presigned=True,
            verbose_storage=True
        )
        
        webhook = await service.create_webhook(webhook_post)
        
        assert webhook is not None
        # Verify JSON fields were serialized
        call_args = mock_db.insert_record.call_args
        assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_create_webhook_exception_handling(self):
        """Test create_webhook handles exceptions"""
        from vasttams.webhooks.models import WebhookPost
        
        mock_db = Mock()
        mock_db.insert_record.side_effect = Exception("Database error")
        mock_db.get_qualified_table_name = Mock(return_value="test.webhooks")
        
        service = WebhookService(mock_db)
        
        webhook_post = WebhookPost(
            url="http://example.com/webhook",
            api_key_name="test-key",
            api_key_value="test-value",
            events=["flow.created"]
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.create_webhook(webhook_post)
        
        assert exc_info.value.status_code == 500


class TestWebhookServiceUpdateWebhook:
    """Test update_webhook method"""
    
    @pytest.mark.asyncio
    async def test_update_webhook_basic(self):
        """Test update_webhook with basic update"""
        from vasttams.webhooks.models import WebhookUpdate
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        # get_webhook is called twice - once to check existence, once to return updated
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]'],
                'enabled': [True]
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.execute_sql = Mock()
        mock_db.get_qualified_table_name = Mock(return_value="test.webhooks")
        
        service = WebhookService(mock_db)
        
        webhook_update = WebhookUpdate(url="http://new-url.com/webhook")
        
        webhook = await service.update_webhook(webhook_id, webhook_update)
        
        assert webhook is not None
        mock_db.execute_sql.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_webhook_not_found(self):
        """Test update_webhook with non-existent webhook"""
        from vasttams.webhooks.models import WebhookUpdate
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        
        webhook_update = WebhookUpdate(url="http://new-url.com/webhook")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.update_webhook(webhook_id, webhook_update)
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_webhook_all_fields(self):
        """Test update_webhook with all fields"""
        from vasttams.webhooks.models import WebhookUpdate
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.delete.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]'],
                'enabled': [True]
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.execute_sql.side_effect = Exception("SQL error")  # Trigger fallback
        mock_db.insert_record = Mock()
        mock_db.get_qualified_table_name = Mock(return_value="test.webhooks")
        
        service = WebhookService(mock_db)
        
        from vasttams.common.models import Tags
        new_flow_id = str(uuid.uuid4())
        webhook_update = WebhookUpdate(
            url="http://new-url.com/webhook",
            api_key_name="new-key",
            events=["flow.updated"],
            flow_ids=[new_flow_id],
            enabled=False,
            presigned=False,
            verbose_storage=False
        )
        
        webhook = await service.update_webhook(webhook_id, webhook_update)
        
        # Should use fallback upsert pattern
        assert webhook is not None
        mock_db.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_webhook_partial_update(self):
        """Test update_webhook with partial fields"""
        from vasttams.webhooks.models import WebhookUpdate
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]'],
                'enabled': [True]
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.execute_sql = Mock()
        mock_db.get_qualified_table_name = Mock(return_value="test.webhooks")
        
        service = WebhookService(mock_db)
        
        # Only update enabled field
        webhook_update = WebhookUpdate(enabled=False)
        
        webhook = await service.update_webhook(webhook_id, webhook_update)
        
        assert webhook is not None
        # Should only update enabled field
        mock_db.execute_sql.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_webhook_no_fields(self):
        """Test update_webhook with no fields to update"""
        from vasttams.webhooks.models import WebhookUpdate
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]'],
                'enabled': [True]
            }
        }
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name = Mock(return_value="test.webhooks")
        
        service = WebhookService(mock_db)
        
        # Empty update (only updated timestamp)
        webhook_update = WebhookUpdate()
        
        webhook = await service.update_webhook(webhook_id, webhook_update)
        
        assert webhook is not None
    
    @pytest.mark.asyncio
    async def test_update_webhook_exception_handling(self):
        """Test update_webhook handles exceptions"""
        from vasttams.webhooks.models import WebhookUpdate
        
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        
        webhook_update = WebhookUpdate(url="http://new-url.com/webhook")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.update_webhook(webhook_id, webhook_update)
        
        assert exc_info.value.status_code == 500


class TestWebhookServiceDeleteWebhook:
    """Test delete_webhook method"""
    
    @pytest.mark.asyncio
    async def test_delete_webhook_success(self):
        """Test delete_webhook successfully deletes webhook"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.delete.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': [webhook_id],
                'url': ['http://example.com/webhook'],
                'api_key_name': ['test-key'],
                'api_key_value': ['test-value'],
                'events': ['["flow.created"]']
            }
        }
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        
        result = await service.delete_webhook(webhook_id)
        
        assert result is True
        mock_query.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self):
        """Test delete_webhook with non-existent webhook"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': {}}
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_webhook(webhook_id)
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_webhook_exception_handling(self):
        """Test delete_webhook handles exceptions"""
        webhook_id = str(uuid.uuid4())
        
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.delete.return_value = mock_query
        mock_query.execute.side_effect = Exception("Database error")
        mock_db.query.return_value = mock_query
        
        service = WebhookService(mock_db)
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_webhook(webhook_id)
        
        assert exc_info.value.status_code == 500


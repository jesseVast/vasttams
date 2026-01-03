"""
Webhook Service

This module handles webhook-related storage operations including CRUD operations.
"""

import asyncio
import logging
import json
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.timestamp_utils import get_tams_timestamp, prepare_data_for_pyarrow, is_timestamp_field
from .models import Webhook, WebhookPost, WebhookUpdate

logger = logging.getLogger(__name__)


class WebhookService:
    """Handles webhook-related storage operations"""
    
    def __init__(self, vast_db):
        self.vast_db = vast_db
    
    async def get_webhooks(self) -> List[Webhook]:
        """Get all webhooks"""
        try:
            result = self.vast_db.query("webhooks").select("*").execute()
            
            webhooks = []
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        webhook_data = {}
                        for column, values in data.items():
                            if column != '$row_id':
                                value = values[i] if i < len(values) else None
                                
                                # Parse JSON fields
                                if column in ['events', 'flow_ids', 'source_ids', 'flow_collected_by_ids', 
                                             'source_collected_by_ids', 'accept_get_urls', 'accept_storage_ids', 'tags'] and value:
                                    try:
                                        value = json.loads(value) if isinstance(value, str) else value
                                    except json.JSONDecodeError:
                                        value = None
                                
                                # Handle datetime fields
                                if column in ['created', 'updated'] and value and isinstance(value, str):
                                    try:
                                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    except (ValueError, AttributeError):
                                        value = None
                                
                                webhook_data[column] = value
                        
                        if webhook_data:
                            try:
                                webhooks.append(Webhook(**webhook_data))
                            except Exception as e:
                                logger.warning("Failed to parse webhook: %s", e)
                                continue
                elif isinstance(data, list):
                    for row in data:
                        webhook_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        if webhook_data:
                            try:
                                webhooks.append(Webhook(**webhook_data))
                            except Exception as e:
                                logger.warning("Failed to parse webhook: %s", e)
                                continue
            
            return webhooks
        except Exception as e:
            logger.error("Failed to get webhooks: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a specific webhook by ID"""
        try:
            result = self.vast_db.query("webhooks").select("*").where(f"id = '{webhook_id}'").execute()
            
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        return None
                    
                    webhook_data = {}
                    for column, values in data.items():
                        if column != '$row_id':
                            value = values[0] if len(values) > 0 else None
                            
                            # Parse JSON fields
                            if column in ['events', 'flow_ids', 'source_ids', 'flow_collected_by_ids', 
                                         'source_collected_by_ids', 'accept_get_urls', 'accept_storage_ids', 'tags'] and value:
                                try:
                                    value = json.loads(value) if isinstance(value, str) else value
                                except json.JSONDecodeError:
                                    value = None
                            
                            # Handle datetime fields
                            if column in ['created', 'updated'] and value and isinstance(value, str):
                                try:
                                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except (ValueError, AttributeError):
                                    value = None
                            
                            webhook_data[column] = value
                    
                    return Webhook(**webhook_data)
                elif isinstance(data, list):
                    if not data:
                        return None
                    webhook_data = dict(data[0]) if hasattr(data[0], '__iter__') and not isinstance(data[0], str) else data[0]
                    if webhook_data:
                        return Webhook(**webhook_data)
            
            return None
        except Exception as e:
            logger.error("Failed to get webhook: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_webhook(self, webhook_post: WebhookPost) -> Webhook:
        """Create a new webhook"""
        try:
            import uuid
            webhook_id = str(uuid.uuid4())
            
            now = get_tams_timestamp()
            
            data = {
                'id': webhook_id,
                'url': webhook_post.url,
                'api_key_name': webhook_post.api_key_name,
                'api_key_value': webhook_post.api_key_value,
                'events': json.dumps(webhook_post.events) if webhook_post.events else None,
                'flow_ids': json.dumps(webhook_post.flow_ids) if webhook_post.flow_ids else None,
                'source_ids': json.dumps(webhook_post.source_ids) if webhook_post.source_ids else None,
                'flow_collected_by_ids': json.dumps(webhook_post.flow_collected_by_ids) if webhook_post.flow_collected_by_ids else None,
                'source_collected_by_ids': json.dumps(webhook_post.source_collected_by_ids) if webhook_post.source_collected_by_ids else None,
                'accept_get_urls': json.dumps(webhook_post.accept_get_urls) if webhook_post.accept_get_urls else None,
                'accept_storage_ids': json.dumps(webhook_post.accept_storage_ids) if webhook_post.accept_storage_ids else None,
                'presigned': webhook_post.presigned,
                'verbose_storage': webhook_post.verbose_storage,
                'tags': json.dumps(webhook_post.tags.dict() if hasattr(webhook_post, 'tags') and webhook_post.tags else {}),
                'enabled': webhook_post.enabled,
                'created': now,
                'updated': now,
            }
            
            # Prepare data for PyArrow insertion
            insert_data = prepare_data_for_pyarrow(data)
            
            # Insert into database
            # Run blocking insert_record in thread pool to avoid blocking event loop
            await asyncio.to_thread(self.vast_db.insert_record, "webhooks", insert_data)
            
            # Fetch the created webhook
            created_webhook = await self.get_webhook(webhook_id)
            return created_webhook
        except Exception as e:
            logger.error("Failed to create webhook: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_webhook(self, webhook_id: str, webhook_update: WebhookUpdate) -> Optional[Webhook]:
        """Update an existing webhook"""
        try:
            # Check if webhook exists
            existing = await self.get_webhook(webhook_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            # Prepare update data with only provided fields
            now = get_tams_timestamp()
            
            update_data = {}
            
            # Update fields that are provided
            if webhook_update.url is not None:
                update_data['url'] = webhook_update.url
            if webhook_update.api_key_name is not None:
                update_data['api_key_name'] = webhook_update.api_key_name
            if webhook_update.api_key_value is not None:
                update_data['api_key_value'] = webhook_update.api_key_value
            if webhook_update.events is not None:
                update_data['events'] = json.dumps(webhook_update.events)
            if webhook_update.flow_ids is not None:
                update_data['flow_ids'] = json.dumps(webhook_update.flow_ids)
            if webhook_update.source_ids is not None:
                update_data['source_ids'] = json.dumps(webhook_update.source_ids)
            if webhook_update.flow_collected_by_ids is not None:
                update_data['flow_collected_by_ids'] = json.dumps(webhook_update.flow_collected_by_ids)
            if webhook_update.source_collected_by_ids is not None:
                update_data['source_collected_by_ids'] = json.dumps(webhook_update.source_collected_by_ids)
            if webhook_update.accept_get_urls is not None:
                update_data['accept_get_urls'] = json.dumps(webhook_update.accept_get_urls)
            if webhook_update.accept_storage_ids is not None:
                update_data['accept_storage_ids'] = json.dumps(webhook_update.accept_storage_ids)
            if webhook_update.presigned is not None:
                update_data['presigned'] = webhook_update.presigned
            if webhook_update.verbose_storage is not None:
                update_data['verbose_storage'] = webhook_update.verbose_storage
            if webhook_update.enabled is not None:
                update_data['enabled'] = webhook_update.enabled
            
            # Always update the 'updated' timestamp
            update_data['updated'] = now
            
            # If we have data to update, perform the update
            if update_data:
                from ..common.storage.timestamp_utils import prepare_data_for_sql
                sql_data = prepare_data_for_sql(update_data)
                
                set_clauses = []
                for column, value in sql_data.items():
                    # Check if this is a timestamp field that should be CAST
                    if is_timestamp_field(column) and isinstance(value, str) and value.startswith('CAST('):
                        # Handle timestamp fields that are already CAST expressions - don't quote them
                        set_clauses.append(f"{column} = {value}")
                    elif isinstance(value, str):
                        escaped_value = value.replace("'", "''")
                        set_clauses.append(f"{column} = '{escaped_value}'")
                    elif value is None:
                        set_clauses.append(f"{column} = NULL")
                    else:
                        set_clauses.append(f"{column} = {value}")
                
                if set_clauses:
                    table = self.vast_db.get_qualified_table_name("webhooks")
                    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = '{webhook_id}'"
                    
                    try:
                        self.vast_db.execute_sql(sql)
                    except Exception:
                        # Fallback to upsert pattern - merge update_data with existing webhook
                        # First get the existing webhook data
                        existing = await self.get_webhook(webhook_id)
                        if existing:
                            # Merge updated fields into existing data
                            merged_data = {
                                'id': existing.id,
                                'url': update_data.get('url', existing.url),
                                'api_key_name': update_data.get('api_key_name', existing.api_key_name),
                                'api_key_value': update_data.get('api_key_value', existing.api_key_value),
                                'events': update_data.get('events', json.dumps(existing.events) if existing.events else None),
                                'flow_ids': update_data.get('flow_ids', json.dumps(existing.flow_ids) if existing.flow_ids else None),
                                'source_ids': update_data.get('source_ids', json.dumps(existing.source_ids) if existing.source_ids else None),
                                'flow_collected_by_ids': update_data.get('flow_collected_by_ids', json.dumps(existing.flow_collected_by_ids) if existing.flow_collected_by_ids else None),
                                'source_collected_by_ids': update_data.get('source_collected_by_ids', json.dumps(existing.source_collected_by_ids) if existing.source_collected_by_ids else None),
                                'accept_get_urls': update_data.get('accept_get_urls', json.dumps(existing.accept_get_urls) if existing.accept_get_urls else None),
                                'accept_storage_ids': update_data.get('accept_storage_ids', json.dumps(existing.accept_storage_ids) if existing.accept_storage_ids else None),
                                'presigned': update_data.get('presigned', existing.presigned),
                                'verbose_storage': update_data.get('verbose_storage', existing.verbose_storage),
                                'tags': json.dumps(existing.tags.dict() if existing.tags else {}),
                                'enabled': update_data.get('enabled', existing.enabled),
                                'created': existing.created,
                                'updated': now
                            }
                            
                            # Delete existing record
                            self.vast_db.query("webhooks").delete().where(f"id = '{webhook_id}'").execute()
                            
                            # Insert merged record
                            insert_data = prepare_data_for_pyarrow(merged_data)
                            # Run blocking insert_record in thread pool to avoid blocking event loop
                            await asyncio.to_thread(self.vast_db.insert_record, "webhooks", insert_data)
            
            # Fetch and return the updated webhook
            updated_webhook = await self.get_webhook(webhook_id)
            if not updated_webhook:
                raise HTTPException(status_code=500, detail="Failed to retrieve updated webhook")
            return updated_webhook
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to update webhook: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        try:
            # Check if webhook exists
            existing = await self.get_webhook(webhook_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            # Delete the webhook
            self.vast_db.query("webhooks").delete().where(f"id = '{webhook_id}'").execute()
            
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to delete webhook: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")


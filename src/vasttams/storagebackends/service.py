"""
Storage Backend Service

This module handles storage backend-related storage operations including
CRUD operations and validation against object usage.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from ..common.storage.interfaces import StorageInterface
from ..common.storage.timestamp_utils import get_tams_timestamp, prepare_data_for_pyarrow
from .models import StorageBackend, StorageBackendPost, StorageBackendPatch

logger = logging.getLogger(__name__)


class StorageBackendService:
    """Handles storage backend-related storage operations"""
    
    def __init__(self, vast_db, s3_client):
        self.vast_db = vast_db
        self.s3_client = s3_client
    
    async def get_storage_backends(self) -> List[StorageBackend]:
        """Get all storage backends"""
        try:
            result = self.vast_db.query("storage_backends").select("*").execute()
            
            backends = []
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    # Convert column arrays to row dictionaries
                    num_rows = len(next(iter(data.values())))
                    for i in range(num_rows):
                        backend_data = {}
                        for column, values in data.items():
                            if column != '$row_id':
                                value = values[i] if i < len(values) else None
                                
                                # Handle datetime fields
                                if column in ['created_at', 'updated_at'] and value and isinstance(value, str):
                                    try:
                                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    except (ValueError, AttributeError):
                                        value = None
                                
                                backend_data[column] = value
                        
                        if backend_data:
                            # Mask secrets in responses
                            backend_data['access_key'] = None
                            backend_data['secret_key'] = None
                            backends.append(StorageBackend(**backend_data))
                elif isinstance(data, list):
                    for row in data:
                        backend_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                        if backend_data:
                            backends.append(StorageBackend(**backend_data))
            else:
                for row in result if isinstance(result, list) else []:
                    backend_data = dict(row) if hasattr(row, '__iter__') and not isinstance(row, str) else row
                    if backend_data:
                        backend_data['access_key'] = None
                        backend_data['secret_key'] = None
                        backends.append(StorageBackend(**backend_data))
                    if backend_data:
                        backend_data['access_key'] = None
                        backend_data['secret_key'] = None
                        backends.append(StorageBackend(**backend_data))
            
            return backends
        except Exception as e:
            logger.error("Failed to get storage backends: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_storage_backend(self, backend_id: str) -> Optional[StorageBackend]:
        """Get a specific storage backend by ID"""
        try:
            result = self.vast_db.query("storage_backends").select("*").where(f"id = '{backend_id}'").execute()
            
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and data:
                    num_rows = len(next(iter(data.values())))
                    if num_rows == 0:
                        return None
                    
                    backend_data = {}
                    for column, values in data.items():
                        if column != '$row_id':
                            value = values[0] if len(values) > 0 else None
                            
                            if column in ['created_at', 'updated_at'] and value and isinstance(value, str):
                                try:
                                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except (ValueError, AttributeError):
                                    value = None
                            
                            backend_data[column] = value
                    
                    backend_data['access_key'] = None
                    backend_data['secret_key'] = None
                    return StorageBackend(**backend_data)
                elif isinstance(data, list):
                    if not data:
                        return None
                    backend_data = dict(data[0]) if hasattr(data[0], '__iter__') and not isinstance(data[0], str) else data[0]
                    backend_data['access_key'] = None
                    backend_data['secret_key'] = None
                    return StorageBackend(**backend_data)
            else:
                if not result or len(result) == 0:
                    return None
                backend_data = dict(result[0]) if hasattr(result[0], '__iter__') and not isinstance(result[0], str) else result[0]
                backend_data['access_key'] = None
                backend_data['secret_key'] = None
                return StorageBackend(**backend_data)
            
            return None
        except Exception as e:
            logger.error("Failed to get storage backend %s: %s", backend_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def create_storage_backend(self, backend: StorageBackendPost) -> StorageBackend:
        """Create a new storage backend"""
        try:
            import uuid
            import re
            
            # Generate ID if not provided
            backend_id = str(uuid.uuid4())
            now = get_tams_timestamp()
            
            # Generate label from ID if not provided
            if not backend.label:
                # Create a reasonable label from store_product and provider
                label = f"{backend.store_product}-{backend.provider}".lower()
                # Remove special characters to match validation
                label = re.sub(r'[^a-zA-Z0-9_-]', '_', label)
                # Add ID suffix for uniqueness
                label = f"{label}-{backend_id[:8]}"
            else:
                label = backend.label
            
            # Check if another backend already has default_storage=True
            existing_backends = await self.get_storage_backends()
            if backend.default_storage:
                for existing in existing_backends:
                    if existing.default_storage:
                        logger.warning("Removing default_storage flag from backend %s", existing.id)
                        # Update existing default to False
                        await self._update_storage_backend_flag(existing.id, 'default_storage', False)
            
            storage_backend = StorageBackend(
                id=backend_id,
                label=label,
                store_type=backend.store_type,
                provider=backend.provider,
                store_product=backend.store_product,
                region=backend.region,
                availability_zone=backend.availability_zone,
                endpoint_url=backend.endpoint_url,
                access_key=backend.access_key,
                secret_key=backend.secret_key,
                bucket_name=backend.bucket_name,
                root_path=backend.root_path,
                use_ssl=backend.use_ssl,
                default_storage=backend.default_storage,
                created_at=now,
                updated_at=now
            )
            
            backend_data = storage_backend.model_dump()
            backend_data = prepare_data_for_pyarrow(backend_data)
            
            self.vast_db.insert_record("storage_backends", backend_data)
            
            logger.info("Created storage backend %s with label %s", backend_id, label)
            return storage_backend
        except Exception as e:
            logger.error("Failed to create storage backend: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_storage_backend(self, backend_id: str, backend_update: StorageBackendPatch) -> StorageBackend:
        """Update a storage backend"""
        try:
            # Get existing backend
            existing = await self.get_storage_backend(backend_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Storage backend not found")
            
            # Update fields
            update_data = backend_update.model_dump(exclude_unset=True)
            if not update_data:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            # Check if setting default_storage=True
            if update_data.get('default_storage'):
                existing_backends = await self.get_storage_backends()
                for backend in existing_backends:
                    if backend.id != backend_id and backend.default_storage:
                        logger.warning("Removing default_storage flag from backend %s", backend.id)
                        await self._update_storage_backend_flag(backend.id, 'default_storage', False)
            
            # Merge updates
            updated_data = existing.model_dump()
            updated_data.update(update_data)
            updated_data['updated_at'] = get_tams_timestamp()
            
            # Try UPDATE first
            try:
                from ..common.storage.timestamp_utils import prepare_data_for_sql
                update_dict = prepare_data_for_sql(updated_data)
                update_dict = {k: v for k, v in update_dict.items() if v is not None}
                
                if update_dict:
                    set_clauses = []
                    for column, value in update_dict.items():
                        if isinstance(value, str) and value.startswith('CAST('):
                            set_clauses.append(f"{column} = {value}")
                        elif isinstance(value, str):
                            escaped_value = value.replace("'", "''")
                            set_clauses.append(f"{column} = '{escaped_value}'")
                        elif value is None:
                            set_clauses.append(f"{column} = NULL")
                        else:
                            set_clauses.append(f"{column} = {value}")
                    
                    table = self.vast_db.get_qualified_table_name("storage_backends")
                    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = '{backend_id}'"
                    logger.debug("Updating storage backend %s with SQL: %s", backend_id, sql)
                    self.vast_db.execute_sql(sql)
                    logger.info("Successfully updated storage backend %s", backend_id)
                else:
                    logger.warning("No fields to update for storage backend %s", backend_id)
                
                # Return updated backend
                return await self.get_storage_backend(backend_id)
                
            except Exception as update_error:
                logger.warning("UPDATE failed for storage backend %s, trying upsert approach: %s", backend_id, update_error)
                
                # If UPDATE fails, try DELETE + INSERT (upsert)
                try:
                    # Delete existing backend using query API (non-SQL)
                    self.vast_db.query("storage_backends").delete().where(f"id = '{backend_id}'").execute()
                    logger.info("Deleted existing storage backend %s for upsert", backend_id)
                    
                    # Insert new backend data
                    # Use existing data for fields not being updated
                    for key in ['id', 'created_at', 'default_storage']:
                        if key not in updated_data:
                            updated_data[key] = existing.model_dump()[key]
                    
                    # Insert the updated record
                    from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
                    pyarrow_data = prepare_data_for_pyarrow(updated_data)
                    self.vast_db.insert_record("storage_backends", pyarrow_data)
                    logger.info("Successfully upserted storage backend %s", backend_id)
                    
                    # Return updated backend
                    return await self.get_storage_backend(backend_id)
                    
                except Exception as upsert_error:
                    logger.error("Upsert failed for storage backend %s: %s", backend_id, upsert_error)
                    raise
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to update storage backend %s: %s", backend_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _update_storage_backend_flag(self, backend_id: str, flag_name: str, flag_value: bool):
        """Update a flag on a storage backend"""
        try:
            table = self.vast_db.get_qualified_table_name("storage_backends")
            sql = f"UPDATE {table} SET {flag_name} = {flag_value} WHERE id = '{backend_id}'"
            self.vast_db.execute_sql(sql)
        except Exception as e:
            logger.error("Failed to update storage backend flag %s for %s: %s", flag_name, backend_id, e)
            raise
    
    async def delete_storage_backend(self, backend_id: str) -> bool:
        """Delete a storage backend"""
        try:
            # Per TAMS 8.0 spec, storage_id is in get_urls JSON, not a direct column
            # Skip reference validation for now - would require complex JSON parsing
            # across all segments' get_urls arrays
            logger.info("Deleting storage backend %s", backend_id)
            
            # Delete the backend
            self.vast_db.query("storage_backends").delete().where(f"id = '{backend_id}'").execute()
            
            logger.info("Deleted storage backend %s", backend_id)
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to delete storage backend %s: %s", backend_id, e)
            raise HTTPException(status_code=500, detail="Internal server error")


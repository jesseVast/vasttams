"""
Deletion Request Service

Handles creation, storage, and processing of deletion requests for non-blocking segment deletions.
"""

import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from ..common.models import TimeRange
from ..service.deletion import DeletionRequest
from ..core.dependencies import get_vast_db

logger = logging.getLogger(__name__)


class DeletionRequestService:
    """Service for managing deletion requests"""
    
    def __init__(self, vast_db):
        self.vast_db = vast_db
        self._processing_tasks: Dict[str, asyncio.Task] = {}
    
    async def create_deletion_request(
        self,
        flow_id: str,
        timerange_to_delete: TimeRange,
        delete_flow: bool = False,
        created_by: Optional[str] = None
    ) -> DeletionRequest:
        """Create a new deletion request"""
        request_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        deletion_request = DeletionRequest(
            id=request_id,
            flow_id=flow_id,
            timerange_to_delete=timerange_to_delete,
            delete_flow=delete_flow,
            status="created",
            timerange_remaining=timerange_to_delete,
            created=now,
            created_by=created_by or "system",
            updated=now,
            expiry=now + timedelta(days=7),  # Default 7 day expiry
            error=None
        )
        
        # Store in database
        await self._store_deletion_request(deletion_request)
        
        logger.info("Created deletion request %s for flow %s, timerange %s", 
                   request_id, flow_id, timerange_to_delete)
        
        return deletion_request
    
    async def _store_deletion_request(self, request: DeletionRequest) -> None:
        """Store deletion request in database"""
        try:
            # Convert to dict for storage
            request_dict = request.model_dump()
            
            # Store in deletion_requests table
            # Note: This assumes the table exists with appropriate schema
            # We'll use execute_sql for now
            table_name = self.vast_db.get_qualified_table_name("deletion_requests")
            
            # Convert timerange to string for storage
            timerange_str = str(request.timerange_to_delete.value) if hasattr(request.timerange_to_delete, 'value') else str(request.timerange_to_delete)
            timerange_remaining_str = str(request.timerange_remaining.value) if request.timerange_remaining and hasattr(request.timerange_remaining, 'value') else (str(request.timerange_remaining) if request.timerange_remaining else None)
            
            insert_sql = f"""
                INSERT INTO {table_name} (
                    id, flow_id, timerange_to_delete, delete_flow, status,
                    timerange_remaining, created, created_by, updated, expiry
                ) VALUES (
                    '{request.id}',
                    '{request.flow_id}',
                    '{timerange_str}',
                    {request.delete_flow},
                    '{request.status}',
                    {f"'{timerange_remaining_str}'" if timerange_remaining_str else "NULL"},
                    '{request.created.isoformat() if request.created else datetime.utcnow().isoformat()}',
                    '{request.created_by or "system"}',
                    '{request.updated.isoformat() if request.updated else datetime.utcnow().isoformat()}',
                    '{request.expiry.isoformat() if request.expiry else (datetime.utcnow() + timedelta(days=7)).isoformat()}'
                )
            """
            
            self.vast_db.execute_sql(insert_sql)
            logger.debug("Stored deletion request %s in database", request.id)
        except Exception as e:
            logger.error("Failed to store deletion request %s: %s", request.id, e)
            raise
    
    async def get_deletion_request(self, request_id: str) -> Optional[DeletionRequest]:
        """Get a deletion request by ID"""
        try:
            table_name = self.vast_db.get_qualified_table_name("deletion_requests")
            query_sql = f"SELECT id, flow_id, timerange_to_delete, delete_flow, status, timerange_remaining, created, created_by, updated, expiry, error FROM {table_name} WHERE id = '{request_id}'"
            result = self.vast_db.execute_sql(query_sql)
            
            if not result:
                return None
            
            # Parse result
            request_data = self._parse_deletion_request_result(result)
            if not request_data:
                return None
            
            return DeletionRequest(**request_data)
        except Exception as e:
            logger.error("Failed to get deletion request %s: %s", request_id, e)
            return None
    
    async def get_deletion_requests(self) -> List[DeletionRequest]:
        """Get all active deletion requests"""
        try:
            table_name = self.vast_db.get_qualified_table_name("deletion_requests")
            query_sql = f"SELECT id, flow_id, timerange_to_delete, delete_flow, status, timerange_remaining, created, created_by, updated, expiry, error FROM {table_name} WHERE status IN ('created', 'started') ORDER BY created DESC LIMIT 100"
            result = self.vast_db.execute_sql(query_sql)
            
            if not result:
                return []
            
            requests = []
            request_data_list = self._parse_deletion_requests_result(result)
            for data in request_data_list:
                try:
                    requests.append(DeletionRequest(**data))
                except Exception as e:
                    logger.warning("Failed to parse deletion request: %s", e)
                    continue
            
            return requests
        except Exception as e:
            logger.error("Failed to get deletion requests: %s", e)
            return []
    
    async def update_deletion_request_status(
        self,
        request_id: str,
        status: str,
        timerange_remaining: Optional[TimeRange] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update deletion request status"""
        try:
            table_name = self.vast_db.get_qualified_table_name("deletion_requests")
            update_fields = [f"status = '{status}'", f"updated = '{datetime.utcnow().isoformat()}'"]
            
            if timerange_remaining:
                timerange_str = str(timerange_remaining.value) if hasattr(timerange_remaining, 'value') else str(timerange_remaining)
                update_fields.append(f"timerange_remaining = '{timerange_str}'")
            
            if error:
                import json
                error_json = json.dumps(error)
                update_fields.append(f"error = '{error_json}'")
            
            update_sql = f"""
                UPDATE {table_name}
                SET {', '.join(update_fields)}
                WHERE id = '{request_id}'
            """
            
            self.vast_db.execute_sql(update_sql)
            logger.debug("Updated deletion request %s status to %s", request_id, status)
            return True
        except Exception as e:
            logger.error("Failed to update deletion request %s: %s", request_id, e)
            return False
    
    def _parse_deletion_request_result(self, result: Any) -> Optional[Dict[str, Any]]:
        """Parse database result into deletion request dict"""
        try:
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    # Columnar format
                    if not any(data.values()):
                        return None
                    # Convert to row format
                    row = {}
                    for col, values in data.items():
                        if values and len(values) > 0:
                            row[col] = values[0]
                    return self._convert_row_to_deletion_request(row)
                elif isinstance(data, list) and len(data) > 0:
                    return self._convert_row_to_deletion_request(data[0])
            elif isinstance(result, list) and len(result) > 0:
                return self._convert_row_to_deletion_request(result[0])
            return None
        except Exception as e:
            logger.error("Failed to parse deletion request result: %s", e)
            return None
    
    def _parse_deletion_requests_result(self, result: Any) -> List[Dict[str, Any]]:
        """Parse database result into list of deletion request dicts"""
        try:
            rows = []
            if isinstance(result, dict) and 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    # Columnar format - convert to rows
                    if not any(data.values()):
                        return []
                    col_names = list(data.keys())
                    col_values = [data[col] for col in col_names]
                    row_count = len(col_values[0]) if col_values else 0
                    for i in range(row_count):
                        row = {col_names[j]: col_values[j][i] if i < len(col_values[j]) else None 
                              for j in range(len(col_names))}
                        rows.append(self._convert_row_to_deletion_request(row))
                elif isinstance(data, list):
                    rows = [self._convert_row_to_deletion_request(row) for row in data]
            elif isinstance(result, list):
                rows = [self._convert_row_to_deletion_request(row) for row in result]
            
            return rows
        except Exception as e:
            logger.error("Failed to parse deletion requests result: %s", e)
            return []
    
    def _convert_row_to_deletion_request(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to deletion request dict"""
        try:
            # Parse timerange strings
            timerange_to_delete = None
            if 'timerange_to_delete' in row and row['timerange_to_delete']:
                timerange_to_delete = TimeRange(value=row['timerange_to_delete'])
            
            timerange_remaining = None
            if 'timerange_remaining' in row and row['timerange_remaining']:
                timerange_remaining = TimeRange(value=row['timerange_remaining'])
            
            # Parse dates
            created = None
            if 'created' in row and row['created']:
                if isinstance(row['created'], str):
                    created = datetime.fromisoformat(row['created'].replace('Z', '+00:00'))
                elif isinstance(row['created'], datetime):
                    created = row['created']
            
            updated = None
            if 'updated' in row and row['updated']:
                if isinstance(row['updated'], str):
                    updated = datetime.fromisoformat(row['updated'].replace('Z', '+00:00'))
                elif isinstance(row['updated'], datetime):
                    updated = row['updated']
            
            expiry = None
            if 'expiry' in row and row['expiry']:
                if isinstance(row['expiry'], str):
                    expiry = datetime.fromisoformat(row['expiry'].replace('Z', '+00:00'))
                elif isinstance(row['expiry'], datetime):
                    expiry = row['expiry']
            
            # Parse error JSON
            error = None
            if 'error' in row and row['error']:
                import json
                try:
                    if isinstance(row['error'], str):
                        error = json.loads(row['error'])
                    else:
                        error = row['error']
                except:
                    error = None
            
            return {
                'id': row.get('id'),
                'flow_id': row.get('flow_id'),
                'timerange_to_delete': timerange_to_delete,
                'delete_flow': bool(row.get('delete_flow', False)),
                'status': row.get('status', 'created'),
                'timerange_remaining': timerange_remaining,
                'created': created,
                'created_by': row.get('created_by'),
                'updated': updated,
                'expiry': expiry,
                'error': error
            }
        except Exception as e:
            logger.error("Failed to convert row to deletion request: %s", e)
            raise
    
    async def process_deletion_request(
        self,
        request_id: str,
        segment_service,
        flow_service=None
    ) -> None:
        """Process a deletion request asynchronously"""
        try:
            # Update status to started
            await self.update_deletion_request_status(request_id, "started")
            
            # Get the deletion request
            request = await self.get_deletion_request(request_id)
            if not request:
                logger.error("Deletion request %s not found", request_id)
                await self.update_deletion_request_status(
                    request_id, "error",
                    error={"message": "Deletion request not found"}
                )
                return
            
            logger.info("Processing deletion request %s for flow %s", request_id, request.flow_id)
            
            # Process deletion in chunks to avoid blocking
            timerange = request.timerange_to_delete
            timerange_str = str(timerange.value) if timerange else None
            
            # Handle "all segments" case (large timerange like "0:0_999999:0")
            if timerange_str and ("999999" in timerange_str or timerange_str == "0:0_999999:0"):
                # Get all segments
                segments = await segment_service.get_flow_segments(request.flow_id, None)
            else:
                segments = await segment_service.get_flow_segments(request.flow_id, timerange_str)
            
            if not segments:
                # No segments to delete
                await self.update_deletion_request_status(request_id, "done", timerange_remaining=None)
                logger.info("Deletion request %s completed - no segments found", request_id)
                
                # Delete flow if requested
                if request.delete_flow and flow_service:
                    try:
                        await flow_service.delete_flow(request.flow_id, cascade=False)
                        logger.info("Deleted flow %s after segment deletion", request.flow_id)
                    except Exception as e:
                        logger.warning("Failed to delete flow %s: %s", request.flow_id, e)
                return
            
            # Delete segments in batches to avoid blocking
            batch_size = 50  # Process 50 segments per batch
            total_segments = len(segments)
            deleted_count = 0
            
            for i in range(0, total_segments, batch_size):
                batch = segments[i:i + batch_size]
                
                # Delete batch
                for segment in batch:
                    try:
                        # Delete individual segment
                        timerange_value = segment.timerange.value if segment.timerange else "0:0"
                        await segment_service.delete_flow_segments(
                            request.flow_id,
                            timerange=timerange_value
                        )
                        deleted_count += 1
                    except Exception as e:
                        logger.warning("Failed to delete segment in batch: %s", e)
                        continue
                
                # Update progress
                remaining_count = total_segments - deleted_count
                if remaining_count > 0:
                    # Calculate remaining timerange (simplified - use original for now)
                    await self.update_deletion_request_status(
                        request_id, "started",
                        timerange_remaining=request.timerange_remaining
                    )
                
                # Yield to event loop periodically
                await asyncio.sleep(0.01)
            
            # Cleanup unreferenced objects after deleting segments (TAMS 8.0 spec requirement)
            try:
                from ..objects.service import ObjectStorageService
                from ..core.dependencies import get_s3_client
                s3_client = get_s3_client()
                object_service = ObjectStorageService(self.vast_db, s3_client)
                unreferenced = await object_service.get_unreferenced_objects()
                if unreferenced:
                    deleted_count_objects = await object_service.delete_unreferenced_objects(unreferenced)
                    logger.info("Deletion request %s: Cleaned up %d unreferenced objects after deleting %d segments", 
                              request_id, deleted_count_objects, deleted_count)
            except Exception as e:
                logger.warning("Deletion request %s: Failed to cleanup unreferenced objects: %s", request_id, e)
                # Don't fail the deletion if cleanup fails
            
            # Mark as done
            await self.update_deletion_request_status(request_id, "done", timerange_remaining=None)
            logger.info("Deletion request %s completed - deleted %d segments", request_id, deleted_count)
            
            # Delete flow if requested
            if request.delete_flow and flow_service:
                try:
                    await flow_service.delete_flow(request.flow_id, cascade=False)
                    logger.info("Deleted flow %s after segment deletion", request.flow_id)
                except Exception as e:
                    logger.warning("Failed to delete flow %s: %s", request.flow_id, e)
        
        except Exception as e:
            logger.error("Failed to process deletion request %s: %s", request_id, e)
            await self.update_deletion_request_status(
                request_id, "error",
                error={"message": str(e)}
            )


"""Data operations for VastDBManager"""

import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Union
from pyarrow import Schema
import pyarrow as pa

from .config import DEFAULT_BATCH_SIZE, DEFAULT_MAX_WORKERS, PARALLEL_THRESHOLD, DEFAULT_MAX_RETRIES

logger = logging.getLogger(__name__)


class DataOperations:
    """Handles data CRUD operations (insert, update, delete, query)"""
    
    def __init__(self, connection_manager, cache_manager, predicate_builder, performance_monitor):
        """Initialize data operations with required components"""
        self.connection_manager = connection_manager
        self.cache_manager = cache_manager
        self.predicate_builder = predicate_builder
        self.performance_monitor = performance_monitor
    
    def insert_single_record(self, table_name: str, data: Dict[str, Any]):
        """Insert a single Python dictionary record into a table"""
        try:
            if not self.connection_manager.is_connected():
                raise RuntimeError("Not connected to VAST database")
            
            start_time = time.time()
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                table = schema_obj.table(table_name)
                table.insert_pydict(data)
            
            execution_time = time.time() - start_time
            
            # Record performance metrics
            self.performance_monitor.record_query(
                query_type="insert_pydict",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=1,
                splits_used=1,
                subsplits_used=1,
                success=True
            )
            
            logger.debug(f"Inserted data into table {table_name} in {execution_time:.3f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="insert_pydict",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Error inserting data into table {table_name}: {e}")
            raise
    
    def insert_record_list(self, table_name: str, data: List[Dict[str, Any]]):
        """Insert a list of Python dictionary records into a table"""
        try:
            if not self.connection_manager.is_connected():
                raise RuntimeError("Not connected to VAST database")
            
            start_time = time.time()
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                table = schema_obj.table(table_name)
                table.insert_pylist(data)
            
            execution_time = time.time() - start_time
            
            # Record performance metrics
            self.performance_monitor.record_query(
                query_type="insert_pylist",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=len(data),
                splits_used=1,
                subsplits_used=1,
                success=True
            )
            
            logger.debug(f"Inserted {len(data)} rows into table {table_name} in {execution_time:.3f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="insert_pylist",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Error inserting data into table {table_name}: {e}")
            raise
    
    def query_with_predicates(self, table_name: str, predicates: Optional[Any] = None, 
                             columns: Optional[List[str]] = None, limit: Optional[int] = None,
                             include_row_ids: bool = False):
        """Query data from a table with optional predicates using VAST's query capabilities"""
        try:
            start_time = time.time()
            
            # Handle predicates - can be either Ibis predicates or Python dictionaries
            vast_filter = None
            if predicates is not None:
                if hasattr(predicates, 'op'):  # This is an Ibis predicate
                    # Use the predicate directly with VAST
                    vast_filter = predicates
                    logger.debug(f"Using Ibis predicate directly: {predicates}")
                elif isinstance(predicates, dict):
                    # Convert Python dictionary predicates to VAST filter string
                    vast_filter = self.predicate_builder.build_vast_predicates(predicates)
                    logger.debug(f"Converted dictionary predicates to VAST filter: {vast_filter}")
                else:
                    logger.warning(f"Unknown predicate type {type(predicates)}: {predicates}")
            
            # Get table info and create query config
            table_info = self.cache_manager.get_table_stats(table_name)
            if not table_info:
                logger.error(f"Table {table_name} not found in cache")
                return None
            
            # Create basic query configuration - let VAST handle optimization
            query_config = self._create_basic_query_config(table_name)
            
            # Execute query with VAST
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                vast_table = schema_obj.table(table_name)
                
                # Execute the query using the correct VAST API
                if vast_filter is not None:
                    # For filtered queries, we need to use the predicate parameter
                    if include_row_ids:
                        # Use internal_row_id parameter directly - this is the correct method
                        result = vast_table.select(columns=columns, predicate=vast_filter, internal_row_id=True)
                    else:
                        result = vast_table.select(columns=columns, predicate=vast_filter, config=query_config)
                else:
                    # For unfiltered queries
                    if include_row_ids:
                        # Use internal_row_id parameter directly - this is the correct method
                        result = vast_table.select(columns=columns, internal_row_id=True)
                    else:
                        result = vast_table.select(columns=columns, config=query_config)
                
                # Execute the query to get the actual data
                result = result.read_all()
                
                # Convert to dictionary format
                if hasattr(result, 'to_pydict'):
                    data = result.to_pydict()
                    
                    # Apply limit if specified (after converting to dict)
                    if limit and data and any(isinstance(v, list) for v in data.values()):
                        keys = list(data.keys())
                        if keys:
                            first_key = keys[0]
                            if isinstance(data[first_key], list) and len(data[first_key]) > limit:
                                # Truncate all columns to limit
                                for key in keys:
                                    if isinstance(data[key], list):
                                        data[key] = data[key][:limit]
                else:
                    logger.warning(f"Result does not have to_pydict method: {result}")
                    data = {}
                
                # Handle row IDs if requested
                if include_row_ids and data and '$row_id' in data:
                    logger.debug(f"Row IDs found: {data['$row_id']}")
                
                execution_time = time.time() - start_time
                logger.debug(f"Query execution time: {execution_time:.3f}s")
                
                return data
                
        except Exception as e:
            logger.error(f"Error in query_with_predicates for table {table_name}: {e}")
            raise
    
    def update(self, table_name: str, data: Dict[str, List[Any]], predicate: Optional[Any] = None):
        """Update data in a table using VAST's native UPDATE capability"""
        try:
            if predicate is None:
                logger.warning(f"Update operation requires a predicate for table {table_name}")
                return 0
            
            # Get the table schema upfront for validation
            table_schema = self.cache_manager.get_table_columns(table_name)
            if table_schema is None:
                logger.error(f"Could not get schema for table {table_name}")
                return 0
            
            # Validate column names upfront before doing any expensive operations
            columns = list(data.keys())
            available_columns = [f.name for f in table_schema]
            invalid_columns = [col for col in columns if col not in available_columns]
            
            if invalid_columns:
                logger.error(f"Invalid columns for table {table_name}: {invalid_columns}")
                logger.error(f"Available columns: {available_columns}")
                return 0
            
            logger.info(f"Updating {len(columns)} columns in table {table_name}")
            
            # Query with predicate to get rows to update (with row IDs)
            matching_rows = self.query_with_predicates(table_name, predicate, include_row_ids=True)
            
            if not matching_rows:
                logger.warning(f"No rows found matching predicate for update in table {table_name}")
                return 0
            
            # Extract row IDs from the result
            if hasattr(matching_rows, 'to_pydict'):
                row_data = matching_rows.to_pydict()
            else:
                row_data = matching_rows
            
            if '$row_id' not in row_data:
                logger.error(f"Row IDs not found in query result")
                return 0
            
            row_ids = row_data['$row_id']
            num_rows = len(row_ids)
            logger.info(f"Found {num_rows} rows to update")
            
            # Build update schema with $row_id + columns being updated
            update_schema = [pa.field('$row_id', pa.uint64())]
            
            for field in table_schema:
                if field.name in columns:
                    update_schema.append(field)
            
            # Create update data with new values + row IDs
            update_data = {}
            for column in columns:
                update_data[column] = []
            
            # Repeat the update values for each row
            for _ in range(num_rows):
                for column in columns:
                    if isinstance(data[column], list):
                        # Use first value if it's a list
                        update_data[column].append(data[column][0] if data[column] else None)
                    else:
                        # Use the value directly
                        update_data[column].append(data[column])
            
            # Add row IDs
            update_data['$row_id'] = row_ids
            
            # Create RecordBatch and update the table
            records = pa.RecordBatch.from_pydict(update_data, schema=pa.schema(update_schema))
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                vast_table = schema_obj.table(table_name)
                
                vast_table.update(records)
                logger.info(f"Successfully updated {num_rows} rows in table {table_name}")
                return num_rows
                
        except Exception as e:
            logger.error(f"Failed to update table {table_name}: {e}")
            raise
    
    def delete(self, table_name: str, predicate: Optional[Any] = None):
        """Delete data from a table using VAST's native DELETE capability"""
        try:
            if predicate is None:
                logger.warning(f"Delete operation requires a predicate for table {table_name}")
                return 0
            
            # Query with predicate to get rows to delete (with row IDs)
            matching_rows = self.query_with_predicates(table_name, predicate, include_row_ids=True)
            
            if not matching_rows:
                logger.warning(f"No rows found matching predicate for delete in table {table_name}")
                return 0
            
            # Extract row IDs from the result
            if hasattr(matching_rows, 'to_pydict'):
                row_data = matching_rows.to_pydict()
            else:
                row_data = matching_rows
            
            if '$row_id' not in row_data:
                logger.error(f"Row IDs not found in query result")
                return 0
            
            row_ids = row_data['$row_id']
            num_rows = len(row_ids)
            logger.info(f"Found {num_rows} rows to delete")
            
            # Create delete data with only the $row_id field
            delete_data = {'$row_id': row_ids}
            
            # Create RecordBatch and delete the rows
            records = pa.RecordBatch.from_pydict(delete_data, schema=pa.schema([pa.field('$row_id', pa.uint64())]))
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                vast_table = schema_obj.table(table_name)
                
                vast_table.delete(records)
                logger.info(f"Successfully deleted {num_rows} rows from table {table_name}")
                
                # Update cache to reflect the deletion
                self.cache_manager.update_table_cache(table_name, None, -num_rows)
                return num_rows
                    
        except Exception as e:
            logger.error(f"Error deleting from table {table_name}: {e}")
            raise
    
    def _create_basic_query_config(self, table_name: str) -> 'vastdb.config.QueryConfig':
        """Create basic QueryConfig with essential parameters only - let VAST handle optimization"""
        try:
            from vastdb.config import QueryConfig
            
            # Basic configuration - only essential parameters that VAST doesn't auto-optimize
            config = QueryConfig(
                use_semi_sorted_projections=True,  # Use our projections
                # Let VAST handle splits, subsplits, and row limits automatically
            )
            
            logger.debug(f"Created basic QueryConfig for {table_name} - VAST handles optimization")
            return config
            
        except Exception as e:
            logger.warning(f"Failed to create basic QueryConfig: {e}, using VAST defaults")
            # Return default config if creation fails - VAST will handle optimization
            try:
                from vastdb.config import QueryConfig
                return QueryConfig()
            except ImportError:
                # Fallback if vastdb.config is not available
                return None
    
    def _convert_uuids_to_strings(self, obj):
        """Recursively convert UUID objects to strings in any data structure"""
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_uuids_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_uuids_to_strings(item) for item in obj]
        else:
            return obj
    
    def _insert_column_batch(self, table_name: str, data: Dict[str, List[Any]]):
        """Insert data from a Python dictionary with row pooling and cache updates"""
        try:
            start_time = time.time()
            
            # Get the table schema from cache or database
            schema = self.cache_manager.get_table_columns(table_name)
            if schema is None:
                # If not cached, fetch from database
                connection = self.connection_manager.get_connection()
                bucket = self.connection_manager.get_bucket()
                schema_name = self.connection_manager.get_schema()
                
                with connection.transaction() as tx:
                    bucket_obj = tx.bucket(bucket)
                    schema_obj = bucket_obj.schema(schema_name)
                    vast_table = schema_obj.table(table_name)
                    schema = vast_table.columns()
                    # Cache the schema
                    stats = vast_table.get_stats()
                    total_rows = getattr(stats, 'total_rows', 0) or 0
                    self.cache_manager.update_table_cache(table_name, schema, total_rows)
            
            # Filter schema to only include columns present in data
            columns = list(data.keys())
            schema_fields = [
                field for field in schema
                if field.name in columns
            ]
            
            # Create record batch (VAST expects RecordBatch, not Table)
            # Convert UUID objects and complex types to strings for PyArrow compatibility
            converted_data = {}
            for col, values in data.items():
                converted_values = []
                for value in values:
                    # First convert any UUIDs to strings recursively
                    value = self._convert_uuids_to_strings(value)
                    
                    if isinstance(value, (dict, list)):
                        # Convert nested dictionaries and lists to JSON strings
                        import json
                        converted_values.append(json.dumps(value))
                    else:
                        converted_values.append(value)
                converted_data[col] = converted_values
            
            record_batch = pa.RecordBatch.from_pydict(converted_data, schema=pa.schema(schema_fields))
            
            num_records = len(record_batch)
            logger.info(f"Inserting {num_records} rows into '{table_name}'")
            
            # Insert the data
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                vast_table = schema_obj.table(table_name)
                
                vast_table.insert(record_batch)
                
            execution_time = time.time() - start_time
            
            # Update cache with new row count
            current_stats = self.cache_manager.get_table_stats(table_name)
            current_rows = 0
            if current_stats and isinstance(current_stats, dict):
                current_rows = current_stats.get('total_rows', 0)
                # Handle nested dictionary case (defensive programming)
                if isinstance(current_rows, dict):
                    current_rows = current_rows.get('total_rows', 0)
                # Ensure we have a valid number before calling int()
                if current_rows is not None and current_rows != '':
                    try:
                        current_rows = int(current_rows)
                    except (ValueError, TypeError):
                        current_rows = 0
                else:
                    current_rows = 0
            
            new_total_rows = current_rows + num_records
            
            # Update cache with new stats
            self.cache_manager.update_table_cache(table_name, schema, new_total_rows)
            
            # Record performance metrics
            self.performance_monitor.record_query(
                query_type="insert_pydict",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=num_records,
                splits_used=1,
                subsplits_used=1,
                success=True
            )
            
            logger.info(f"Successfully inserted {num_records} rows into '{table_name}' in {execution_time:.3f}s")
            logger.info(f"Updated cache: {current_rows} -> {new_total_rows} total rows")
            
            return num_records
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="insert_pydict",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Failed to insert data into table '{table_name}': {e}")
            raise
    
    def insert(self, table_name: str, data: Dict[str, List[Any]]):
        """Backward compatibility method - alias for _insert_column_batch"""
        return self._insert_column_batch(table_name, data)
    
    def select(self, table_name: str, predicate: Optional[Any] = None, 
               output_by_row: bool = False, columns: Optional[List[str]] = None):
        """Backward compatibility method - alias for query_with_predicates"""
        # Pass predicates directly - let query_with_predicates handle the type
        # Ibis predicates will be used directly, dictionaries will be converted
        
        result = self.query_with_predicates(
            table_name=table_name,
            predicates=predicate,
            columns=columns
        )
        
        # Convert PyArrow Table to dict if needed
        if result is not None and hasattr(result, 'to_pydict'):
            result = result.to_pydict()
        
        if output_by_row and result is not None:
            # Convert column-oriented result to row-oriented format
            if len(result) > 0:
                num_rows = len(next(iter(result.values())))
                return [
                    {col: result[col][i] for col in result.keys()}
                    for i in range(num_rows)
                ]
        
        return result

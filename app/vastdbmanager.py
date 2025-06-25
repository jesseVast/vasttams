"""
VAST Database Manager

A high-performance manager for VAST database operations including schema management,
table operations, and data manipulation with optimized memory usage and error handling.

This module provides a clean interface to VAST database operations with support for:
- Schema and table management
- Efficient data insertion, deletion, and updates
- Optimized queries with memory-conscious operations
- Comprehensive error handling and logging
"""

import logging
import vastdb
import vastdb.transaction
import pyarrow as pa
from pyarrow import Table, Schema, RecordBatch
from typing import Dict, List, Optional, Union, Any
from contextlib import contextmanager
from ibis import Deferred

# Configure logging
logger = logging.getLogger(__name__)


class VastDBManager:
    """
    High-performance VAST database manager for efficient data operations.
    
    This class provides a clean interface to VAST database operations with optimized
    memory usage, comprehensive error handling, and support for both column-oriented
    and row-oriented data operations.
    
    Attributes:
        endpoint (str): VAST database endpoint URL
        access_key (str): Access key for authentication
        secret_key (str): Secret key for authentication
        bucket (str): Target bucket name
        schema (str): Database schema name
        table_schemas (Dict[str, Schema]): Cached table schemas
        _session (vastdb.Session): VAST database session
        _ready (bool): Connection readiness status
    """
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        schema: str,
        timeout: int = 30
    ) -> None:
        """
        Initialize VAST database manager.
        
        Args:
            endpoint: VAST database endpoint URL
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            bucket: Target bucket name
            schema: Database schema name
            timeout: Connection timeout in seconds (default: 30)
            
        Raises:
            Exception: If connection or schema setup fails
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.schema = schema
        self.table_schemas: Dict[str, Schema] = {}
        self._ready = False
        
        logger.info(f"Initializing VAST DB connection to {endpoint}")
        
        try:
            self._session = vastdb.connect(
                endpoint=self.endpoint,
                access=self.access_key,
                secret=self.secret_key,
                timeout=timeout
            )
            self._setup_schema()
        except Exception as e:
            logger.error(f"Failed to initialize VAST DB connection: {e}")
            raise
    
    @property
    def session(self) -> vastdb.Session:
        """Get the VAST database session."""
        return self._session
    
    @property
    def tables(self) -> list[str]:
        """Get list of available table names."""
        return list(self.table_schemas.keys())
    
    @property
    def is_ready(self) -> bool:
        """Check if the database manager is ready for operations."""
        return self._ready
    
    @contextmanager
    def _transaction(self):
        """
        Context manager for database transactions.
        
        Yields:
            vastdb.transaction.Transaction: Database transaction object
        """
        with self._session.transaction() as tx:
            yield tx
    
    def _get_bucket(self, transaction: vastdb.transaction.Transaction):
        """Get bucket from transaction."""
        return transaction.bucket(self.bucket)
    
    def _get_schema(self, transaction: vastdb.transaction.Transaction):
        """Get schema from transaction."""
        return self._get_bucket(transaction).schema(self.schema)
    
    def _get_table(self, transaction: vastdb.transaction.Transaction, table_name: str):
        """Get table from transaction."""
        return self._get_schema(transaction).table(table_name)
    
    def create_table(self, table_name: str, table_schema: Schema) -> None:
        """
        Create a new table with the specified schema.
        
        Args:
            table_name: Name of the table to create
            table_schema: PyArrow schema defining the table structure
            
        Raises:
            Exception: If table creation fails
        """
        logger.info(f"Creating table '{table_name}' with schema: {table_schema}")
        
        try:
            with self._transaction() as tx:
                bucket = self._get_bucket(tx)
                schema = bucket.schema(self.schema, fail_if_missing=False)
                
                # Check if table already exists
                existing_table = schema.table(table_name, fail_if_missing=False)
                if existing_table is None:
                    table = schema.create_table(table_name, table_schema)
                    self.table_schemas[table_name] = table_schema
                    logger.info(f"Table '{table_name}' created successfully")
                else:
                    logger.warning(f"Table '{table_name}' already exists")
                    self.table_schemas[table_name] = table_schema
                    
        except Exception as e:
            logger.error(f"Failed to create table '{table_name}': {e}")
            raise
    
    def _discover_tables(self) -> None:
        """
        Discover and cache existing table schemas.
        
        This method populates the table_schemas dictionary with schemas
        from existing tables in the database.
        """
        logger.info("Discovering existing tables...")
        
        try:
            with self._transaction() as tx:
                schema = self._get_schema(tx)
                
                for table in schema.tables():
                    table_name = table.name
                    self.table_schemas[table_name] = table.columns()
                    logger.debug(f"Discovered table: {table_name}")
                    
        except Exception as e:
            logger.error(f"Failed to discover tables: {e}")
            raise
    
    def _setup_schema(self) -> None:
        """
        Set up the database schema and discover existing tables.
        
        Creates the schema if it doesn't exist and discovers existing tables.
        """
        logger.info(f"Setting up schema '{self.schema}'")
        
        try:
            with self._transaction() as tx:
                bucket = self._get_bucket(tx)
                
                # Ensure schema exists
                schema = bucket.schema(self.schema, fail_if_missing=False)
                if schema is None:
                    schema = bucket.create_schema(self.schema)
                    logger.info(f"Schema '{self.schema}' created")
                else:
                    logger.info(f"Schema '{self.schema}' already exists")
                    self._discover_tables()
                    
        except Exception as e:
            logger.error(f"Failed to setup schema: {e}")
            raise
        
        self._ready = True
        logger.info("VAST DB manager is ready")
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the current schema.
        
        Returns:
            List of table names in the schema
        """
        try:
            with self._transaction() as tx:
                schema = self._get_schema(tx)
                tables = [table.name for table in schema.tables()]
                logger.debug(f"Tables in schema '{self.schema}': {tables}")
                return tables
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            raise
    
    def list_schemas(self) -> List[str]:
        """
        List all schemas in the current bucket.
        
        Returns:
            List of schema names in the bucket
        """
        try:
            with self._transaction() as tx:
                bucket = self._get_bucket(tx)
                schemas = [schema.name for schema in bucket.schemas()]
                logger.debug(f"Schemas in bucket '{self.bucket}': {schemas}")
                return schemas
        except Exception as e:
            logger.error(f"Failed to list schemas: {e}")
            raise
    
    def drop_schema(self) -> None:
        """
        Drop the current schema and all its tables.
        
        This operation is irreversible and will delete all data in the schema.
        """
        logger.warning(f"Dropping schema '{self.schema}' and all its tables")
        
        try:
            with self._transaction() as tx:
                schema = self._get_schema(tx)
                schema.drop()
                logger.info(f"Schema '{self.schema}' dropped successfully")
                
        except Exception as e:
            logger.error(f"Failed to drop schema: {e}")
            raise
        finally:
            # Clear cached table schemas
            self.table_schemas.clear()
    
    def drop_table(self, table_name: str) -> None:
        """
        Drop a specific table from the schema.
        
        Args:
            table_name: Name of the table to drop
            
        Raises:
            Exception: If table doesn't exist or drop operation fails
        """
        logger.warning(f"Dropping table '{table_name}'")
        
        try:
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                table.drop()
                logger.info(f"Table '{table_name}' dropped successfully")
                
        except Exception as e:
            logger.error(f"Failed to drop table '{table_name}': {e}")
            raise
        finally:
            # Remove from cached schemas
            self.table_schemas.pop(table_name, None)
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific table.
        
        Args:
            table_name: Name of the table to get stats for
            
        Returns:
            Dictionary containing table statistics
            
        Raises:
            Exception: If table doesn't exist or stats retrieval fails
        """
        try:
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                stats = table.get_stats()
                logger.debug(f"Table stats for '{table_name}': {stats}")
                return stats
        except Exception as e:
            logger.error(f"Failed to get stats for table '{table_name}': {e}")
            raise
    
    def get_table_columns(self, table_name: str) -> Schema:
        """
        Get column definitions for a specific table.
        
        Args:
            table_name: Name of the table to get columns for
            
        Returns:
            PyArrow schema containing column definitions
            
        Raises:
            Exception: If table doesn't exist or column retrieval fails
        """
        try:
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                columns = table.columns()
                logger.debug(f"Table columns for '{table_name}': {columns}")
                return columns
        except Exception as e:
            logger.error(f"Failed to get columns for table '{table_name}': {e}")
            raise
    
    def _get_smallest_column(self, table_name: str) -> str:
        """
        Get the name of the column with the smallest byte width for optimization.
        
        This is used to minimize memory usage when fetching row IDs for operations
        like delete and update.
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            Name of the column with smallest byte width, or first column if none found
        """
        if table_name not in self.table_schemas:
            raise ValueError(f"Table '{table_name}' not found in cached schemas")
        
        schema = self.table_schemas[table_name]
        smallest_column = None
        smallest_width = float('inf')
        
        for field in schema:
            try:
                width = field.type.byte_width
                if width < smallest_width:
                    smallest_width = width
                    smallest_column = field.name
            except AttributeError:
                # Skip non-fixed-width columns
                continue
        
        if smallest_column:
            logger.debug(f"Smallest column for '{table_name}': {smallest_column} ({smallest_width} bytes)")
            return smallest_column
        else:
            # Fallback to first column if no fixed-width columns found
            first_column = schema[0].name
            logger.debug(f"No fixed-width columns found for '{table_name}', using: {first_column}")
            return first_column
    
    def _select(
        self,
        table_name: str,
        column_names: Optional[List[str]] = None,
        predicate: Optional[Union[str, Deferred]] = None,
        internal_rowid: bool = False
    ) -> Table:
        """
        Internal method to select data from a table.
        
        Args:
            table_name: Name of the table to query
            column_names: List of column names to select (None for all)
            predicate: Ibis predicate for filtering
            internal_rowid: Whether to include internal row IDs
            
        Returns:
            PyArrow table containing the query results
            
        Raises:
            Exception: If query execution fails
        """
        logger.debug(f"Executing select on '{table_name}' with columns: {column_names}, predicate: {predicate}")
        
        try:
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                data = table.select(
                    columns=column_names,
                    predicate=predicate,
                    internal_row_id=internal_rowid
                )
                result = data.read_all()
                logger.debug(f"Select returned {len(result)} rows")
                return result
        except Exception as e:
            logger.error(f"Select operation failed for table '{table_name}': {e}")
            raise
    
    def select(
        self,
        table_name: str,
        column_names: Optional[List[str]] = None,
        predicate: Optional[Union[str, Deferred]] = None,
        internal_rowid: bool = False,
        output_by_row: bool = True
    ) -> Union[List[Dict[str, Any]], Dict[str, List[Any]]]:
        """
        Select data from a table with flexible output format.
        
        Args:
            table_name: Name of the table to query
            column_names: List of column names to select (None for all)
            predicate: Ibis predicate for filtering
            internal_rowid: Whether to include internal row IDs
            output_by_row: If True, return list of row dicts; if False, return column dict
            
        Returns:
            Query results in the specified format
            
        Note:
            This method is not suitable for large datasets. For large queries,
            use the VAST SDK directly with the session from this class.
        """
        pyarrow_table = self._select(
            table_name=table_name,
            column_names=column_names,
            predicate=predicate,
            internal_rowid=internal_rowid
        )
        
        if output_by_row:
            return pyarrow_table.to_pylist()
        else:
            return pyarrow_table.to_pydict()
    
    def delete(self, table_name: str, predicate: Union[str, Deferred]) -> int:
        """
        Delete rows from a table based on a predicate.
        
        Args:
            table_name: Name of the table to delete from
            predicate: Ibis predicate defining which rows to delete
            
        Returns:
            Number of rows deleted
            
        Raises:
            Exception: If delete operation fails
        """
        logger.info(f"Deleting rows from '{table_name}' with predicate: {predicate}")
        
        try:
            # Optimize by selecting only the smallest column to get row IDs
            smallest_column = self._get_smallest_column(table_name)
            row_data = self._select(
                table_name=table_name,
                column_names=[smallest_column],
                predicate=predicate,
                internal_rowid=True
            )
            
            if len(row_data) == 0:
                logger.info("No rows to delete")
                return 0
            
            # Delete the rows
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                table.delete(row_data)
            
            logger.info(f"Successfully deleted {len(row_data)} rows")
            return len(row_data)
            
        except Exception as e:
            logger.error(f"Delete operation failed for table '{table_name}': {e}")
            raise
    
    def delete_rowids(self, table_name: str, delete_rows: Table) -> int:
        """
        Delete specific rows by their internal row IDs.
        
        Args:
            table_name: Name of the table to delete from
            delete_rows: PyArrow table containing row IDs to delete
            
        Returns:
            Number of rows deleted
            
        Raises:
            Exception: If delete operation fails
        """
        logger.info(f"Deleting {len(delete_rows)} rows from '{table_name}' by row IDs")
        
        try:
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                table.delete(delete_rows)
            
            logger.info(f"Successfully deleted {len(delete_rows)} rows")
            return len(delete_rows)
            
        except Exception as e:
            logger.error(f"Delete by row IDs failed for table '{table_name}': {e}")
            raise
    
    def insert_pydict(self, table_name: str, data: Dict[str, List[Any]]) -> int:
        """
        Insert data into a table using a column-oriented dictionary format.
        
        Args:
            table_name: Name of the table to insert into
            data: Dictionary with column names as keys and lists of values as values
                  Example: {'column1': [val1, val2], 'column2': [val3, val4]}
                  
        Returns:
            Number of rows inserted
            
        Raises:
            Exception: If insert operation fails
        """
        logger.info(f"Inserting data into '{table_name}' using pydict format")
        
        try:
            # Filter schema to only include columns present in data
            columns = list(data.keys())
            schema_fields = [
                field for field in self.table_schemas[table_name]
                if field.name in columns
            ]
            
            # Create record batch
            record_batch = RecordBatch.from_pydict(data, schema=Schema(schema_fields))
            num_records = len(record_batch)
            
            # Insert the data
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                table.insert(record_batch)
            
            logger.info(f"Successfully inserted {num_records} rows into '{table_name}'")
            return num_records
            
        except Exception as e:
            logger.error(f"Insert pydict failed for table '{table_name}': {e}")
            raise
    
    def insert_pylist(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """
        Insert data into a table using a row-oriented list format.
        
        Args:
            table_name: Name of the table to insert into
            data: List of dictionaries, each representing a row
                  Example: [{'column1': val1, 'column2': val2}, ...]
                  
        Returns:
            Number of rows inserted
            
        Raises:
            Exception: If insert operation fails
        """
        logger.info(f"Inserting {len(data)} rows into '{table_name}' using pylist format")
        
        try:
            # Create record batch using full table schema
            record_batch = RecordBatch.from_pylist(data, schema=self.table_schemas[table_name])
            num_records = len(record_batch)
            
            # Insert the data
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                table.insert(record_batch)
            
            logger.info(f"Successfully inserted {num_records} rows into '{table_name}'")
            return num_records
            
        except Exception as e:
            logger.error(f"Insert pylist failed for table '{table_name}': {e}")
            raise
    
    def insert(
        self,
        table_name: str,
        data: Union[Dict,Dict[str, List[Any]], List[Dict[str, Any]]]
    ) -> int:
        """
        Insert data into a table with flexible input format.
        
        Args:
            table_name: Name of the table to insert into
            data: Data to insert (dict,dict[str, List[Any]], List[Dict[str, Any]])
        Returns:
            Number of rows inserted
        """
        if isinstance(data, dict):
            (test_key, test_value) = next(iter(data.items()))
            if isinstance(test_value, list):
                return self.insert_pydict(table_name, data)
            else:
                return self.insert_pylist(table_name, [data])
        else:
            if isinstance(data, list):
                return self.insert_pylist(table_name, data)
            else:
                raise TypeError("Expected list for pylist format")
    
    def update(self, table_name: str, data: Dict[str, Any], predicate: Union[str, Deferred]) -> int:
        """
        Update rows in a table based on a predicate.
        
        Args:
            table_name: Name of the table to update
            data: Dictionary with column names and new values
                  Example: {'column1': new_value1, 'column2': new_value2}
            predicate: Ibis predicate defining which rows to update
                  
        Returns:
            Number of rows updated
            
        Raises:
            Exception: If update operation fails
            
        Note:
            This method is not suitable for large datasets. For large updates,
            use the VAST SDK directly with the session from this class.
        """
        logger.info(f"Updating rows in '{table_name}' with predicate: {predicate}")
        
        try:
            # Get row IDs for the rows to update
            smallest_column = self._get_smallest_column(table_name)
            row_data = self._select(
                table_name=table_name,
                column_names=[smallest_column],
                predicate=predicate,
                internal_rowid=True
            )
            
            if len(row_data) == 0:
                logger.info("No rows to update")
                return 0
            
            # Prepare update data with row IDs
            columns = list(data.keys())
            update_schema_fields = [pa.field('$row_id', pa.uint64())]
            
            # Add fields for columns being updated
            for field in self.table_schemas[table_name]:
                if field.name in columns:
                    update_schema_fields.append(field)
            
            # Create update data structure
            update_data = {'$row_id': row_data.to_pydict()['$row_id']}
            for column in columns:
                update_data[column] = [data[column]] * len(row_data)
            
            # Create record batch and update
            record_batch = RecordBatch.from_pydict(update_data, schema=Schema(update_schema_fields))
            
            with self._transaction() as tx:
                table = self._get_table(tx, table_name)
                table.update(record_batch)
            
            logger.info(f"Successfully updated {len(row_data)} rows in '{table_name}'")
            return len(row_data)
            
        except Exception as e:
            logger.error(f"Update operation failed for table '{table_name}': {e}")
            raise
    
    def close(self) -> None:
        """Close the database connection and clean up resources."""
        logger.info("Closing VAST DB connection")
        try:
            if hasattr(self, '_session'):
                self._session.close()
            self._ready = False
            logger.info("VAST DB connection closed")
        except Exception as e:
            logger.error(f"Error closing VAST DB connection: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.close()
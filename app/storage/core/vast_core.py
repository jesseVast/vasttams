"""
Core VAST operations without any TAMS-specific logic

This module provides pure VAST infrastructure operations that can be used
by any application, not just TAMS.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
import vastdb

logger = logging.getLogger(__name__)


class VASTCore:
    """
    Core VAST operations without any TAMS-specific logic
    
    This class provides pure VAST infrastructure operations that can be used
    by any application. It handles only VAST-specific concerns like:
    - Connection management
    - Basic CRUD operations
    - Table management
    - Query execution
    """
    
    def __init__(self, endpoints: Union[str, List[str]], auto_connect: bool = True):
        """
        Initialize VAST Core with connection parameters
        
        Args:
            endpoints: Single endpoint string or list of endpoints
            auto_connect: Whether to automatically connect to the database
        """
        if isinstance(endpoints, str):
            self.endpoints = [endpoints]
        else:
            self.endpoints = endpoints
            
        self.current_endpoint_index = 0
        self.connection = None
        self.bucket = None
        self.schema = None
        
        logger.info("VASTCore initialization with %d endpoints", len(self.endpoints))
        
        if auto_connect:
            self.connect()
    
    def connect(self) -> bool:
        """
        Connect to VAST database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            endpoint = self.endpoints[self.current_endpoint_index]
            logger.info("Connecting to VAST endpoint: %s", endpoint)
            
            # Create connection
            self.connection = vastdb.connect(endpoint)
            
            # Get default bucket and schema
            self.bucket = self.connection.bucket("default")
            self.schema = self.bucket.schema("default")
            
            logger.info("Successfully connected to VAST endpoint: %s", endpoint)
            return True
            
        except Exception as e:
            logger.error("Failed to connect to VAST endpoint %s: %s", 
                        self.endpoints[self.current_endpoint_index], e)
            
            # Try next endpoint if available
            if len(self.endpoints) > 1:
                self.current_endpoint_index = (self.current_endpoint_index + 1) % len(self.endpoints)
                logger.info("Trying next endpoint: %s", self.endpoints[self.current_endpoint_index])
                return self.connect()
            
            return False
    
    def is_connected(self) -> bool:
        """
        Check if connected to VAST database
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connection is not None and self.bucket is not None
    
    def get_connection(self):
        """
        Get the current VAST connection
        
        Returns:
            VAST connection object or None if not connected
        """
        return self.connection
    
    def get_bucket(self):
        """
        Get the current VAST bucket
        
        Returns:
            VAST bucket object or None if not connected
        """
        return self.bucket
    
    def get_schema(self):
        """
        Get the current VAST schema
        
        Returns:
            VAST schema object or None if not connected
        """
        return self.schema
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the current schema
        
        Returns:
            List[str]: List of table names
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return []
            
            tables = [table.name for table in self.schema.tables()]
            logger.info("Listed %d tables", len(tables))
            return tables
            
        except Exception as e:
            logger.error("Failed to list tables: %s", e)
            return []
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return False
            
            return table_name in [table.name for table in self.schema.tables()]
            
        except Exception as e:
            logger.error("Failed to check if table %s exists: %s", table_name, e)
            return False
    
    def get_table(self, table_name: str):
        """
        Get a table object
        
        Args:
            table_name: Name of the table to get
            
        Returns:
            VAST table object or None if not found
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return None
            
            if not self.table_exists(table_name):
                logger.error("Table %s does not exist", table_name)
                return None
            
            table = self.schema.table(table_name)
            logger.info("Retrieved table: %s", table_name)
            return table
            
        except Exception as e:
            logger.error("Failed to get table %s: %s", table_name, e)
            return None
    
    def create_table(self, table_name: str, schema: Any) -> bool:
        """
        Create a new table
        
        Args:
            table_name: Name of the table to create
            schema: Table schema (PyArrow Schema)
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return False
            
            if self.table_exists(table_name):
                logger.warning("Table %s already exists", table_name)
                return True
            
            table = self.schema.create_table(table_name, schema)
            logger.info("Successfully created table: %s", table_name)
            return True
            
        except Exception as e:
            logger.error("Failed to create table %s: %s", table_name, e)
            return False
    
    def drop_table(self, table_name: str) -> bool:
        """
        Drop a table
        
        Args:
            table_name: Name of the table to drop
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return False
            
            if not self.table_exists(table_name):
                logger.warning("Table %s does not exist", table_name)
                return True
            
            table = self.get_table(table_name)
            if table:
                table.drop()
                logger.info("Successfully dropped table: %s", table_name)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to drop table %s: %s", table_name, e)
            return False
    
    def insert_record(self, table_name: str, data: Dict[str, Any]) -> bool:
        """
        Insert a record into a table
        
        Args:
            table_name: Name of the table to insert into
            data: Record data as dictionary
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return False
            
            table = self.get_table(table_name)
            if not table:
                return False
            
            # Convert data to PyArrow format if needed
            # This is a simplified version - in practice you'd need proper PyArrow conversion
            table.insert(data)
            logger.info("Successfully inserted record into table: %s", table_name)
            return True
            
        except Exception as e:
            logger.error("Failed to insert record into table %s: %s", table_name, e)
            return False
    
    def query_records(self, table_name: str, predicate: Optional[Dict[str, Any]] = None, 
                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query records from a table
        
        Args:
            table_name: Name of the table to query
            predicate: Query predicate (simplified format)
            limit: Maximum number of records to return
            
        Returns:
            List[Dict]: List of records
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return []
            
            table = self.get_table(table_name)
            if not table:
                return []
            
            # Build query
            query = table.query()
            
            # Apply predicate if provided
            if predicate:
                # This is a simplified predicate application
                # In practice you'd need proper predicate building
                for field, value in predicate.items():
                    if isinstance(value, list):
                        query = query.filter(f"{field} in {value}")
                    else:
                        query = query.filter(f"{field} == {value}")
            
            # Apply limit if provided
            if limit:
                query = query.limit(limit)
            
            # Execute query
            result = query.execute()
            
            # Convert to list of dictionaries
            records = []
            for row in result:
                record = {}
                for i, column in enumerate(result.column_names):
                    record[column] = row[i]
                records.append(record)
            
            logger.info("Successfully queried %d records from table: %s", len(records), table_name)
            return records
            
        except Exception as e:
            logger.error("Failed to query records from table %s: %s", table_name, e)
            return []
    
    def update_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a record in a table
        
        Args:
            table_name: Name of the table to update
            record_id: ID of the record to update
            data: Updated data
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return False
            
            # Note: VAST doesn't have native UPDATE operations
            # This would need to be implemented as DELETE + INSERT or using VAST's update capabilities
            logger.warning("Update operation not implemented for VAST - use delete + insert instead")
            return False
            
        except Exception as e:
            logger.error("Failed to update record in table %s: %s", table_name, e)
            return False
    
    def delete_record(self, table_name: str, record_id: str) -> bool:
        """
        Delete a record from a table
        
        Args:
            table_name: Name of the table to delete from
            record_id: ID of the record to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return False
            
            # Note: VAST doesn't have native DELETE operations
            # This would need to be implemented using VAST's delete capabilities
            logger.warning("Delete operation not implemented for VAST")
            return False
            
        except Exception as e:
            logger.error("Failed to delete record from table %s: %s", table_name, e)
            return False
    
    def get_table_stats(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a table
        
        Args:
            table_name: Name of the table to get stats for
            
        Returns:
            Dict: Table statistics or None if failed
        """
        try:
            if not self.is_connected():
                logger.error("Not connected to VAST database")
                return None
            
            table = self.get_table(table_name)
            if not table:
                return None
            
            stats = table.get_stats()
            table_stats = {
                'name': table_name,
                'total_rows': getattr(stats, 'total_rows', 0) or 0,
                'total_size': getattr(stats, 'total_size', 0) or 0,
                'column_count': len(table.columns())
            }
            
            logger.info("Retrieved stats for table: %s", table_name)
            return table_stats
            
        except Exception as e:
            logger.error("Failed to get stats for table %s: %s", table_name, e)
            return None
    
    def close(self):
        """Close the VAST connection"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
                self.bucket = None
                self.schema = None
                logger.info("Closed VAST connection")
        except Exception as e:
            logger.error("Error closing VAST connection: %s", e)

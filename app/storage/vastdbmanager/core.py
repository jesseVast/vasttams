"""Refactored Core VastDBManager integrating all modular components"""

import logging
import time
from datetime import timedelta, datetime, timezone
from typing import List, Dict, Any, Optional, Union
import vastdb
from pyarrow import Schema
import uuid

from .cache import CacheManager
from .queries import PredicateBuilder
from .analytics import TimeSeriesAnalytics, AggregationAnalytics, PerformanceMonitor, HybridAnalytics
from .config import DEFAULT_BATCH_SIZE, DEFAULT_MAX_WORKERS, PARALLEL_THRESHOLD, DEFAULT_MAX_RETRIES
from .connection_manager import ConnectionManager
from .table_operations import TableOperations
from .data_operations import DataOperations
from .batch_operations import BatchOperations

logger = logging.getLogger(__name__)


class VastDBManager:
    """Refactored VastDBManager with modular architecture"""
    
    def __init__(self, endpoints: Union[str, List[str]], auto_connect: bool = True):
        """
        Initialize VastDBManager with modular components
        
        Args:
            endpoints: Single endpoint string or list of endpoints
            auto_connect: Whether to automatically connect to the database
        """
        # Initialize modular components
        self.connection_manager = ConnectionManager(endpoints)
        self.cache_manager = CacheManager()
        self.predicate_builder = PredicateBuilder()
        self.performance_monitor = PerformanceMonitor()
        self.table_operations = TableOperations(self.connection_manager)
        self.data_operations = DataOperations(
            self.connection_manager, 
            self.cache_manager, 
            self.predicate_builder, 
            self.performance_monitor
        )
        self.batch_operations = BatchOperations(
            self.data_operations, 
            self.performance_monitor
        )
        
        # Initialize analytics components
        self.time_series_analytics = TimeSeriesAnalytics(self.cache_manager)
        self.aggregation_analytics = AggregationAnalytics(self.cache_manager)
        self.hybrid_analytics = HybridAnalytics(self.cache_manager)
        
        # Initialize connection to first endpoint if auto_connect is enabled
        if auto_connect:
            self.connection_manager.connect()
            
            # Discover existing tables
            self._discover_tables()
        
        logger.info(f"Initialized VastDBManager with {len(self.connection_manager.endpoints)} endpoints")
    
    def _discover_tables(self):
        """Discover and cache existing table schemas at startup"""
        try:
            if not self.connection_manager.is_connected():
                return
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                
                for table in schema_obj.tables():
                    table_name = table.name
                    # Cache only essential metadata: schema and initial row count
                    table_stats = table.get_stats()
                    total_rows = getattr(table_stats, 'total_rows', 0) or 0
                    self.cache_manager.update_table_cache(table_name, table.columns(), total_rows)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Discovered and cached table: %s (%s rows)", table_name, total_rows)
                    
            logger.info(f"Discovered and cached {len(self.cache_manager.get_all_table_names())} tables")
                    
        except Exception as e:
            logger.error(f"Failed to discover tables: {e}")
            raise
    
    @property
    def tables(self) -> List[str]:
        """Get list of available table names from cache"""
        try:
            return self.cache_manager.get_all_table_names()
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
    
    def list_tables(self) -> List[str]:
        """Get list of available table names"""
        return self.tables
    
    def connect(self):
        """Connect to VAST database using the first available endpoint"""
        self.connection_manager.connect()
    
    def connect_to_endpoint(self, endpoint: Optional[str] = None):
        """Connect to a specific VAST database endpoint"""
        self.connection_manager.connect_to_endpoint(endpoint)
    
    def disconnect(self):
        """Disconnect from VAST database"""
        self.connection_manager.disconnect()
    
    def get_table_columns(self, table_name: str) -> Optional[Schema]:
        """Get column definitions for a table"""
        try:
            # Check cache first
            columns = self.cache_manager.get_table_columns(table_name)
            if columns is not None:
                return columns
            
            # Fetch from database if not cached
            if self.connection_manager.is_connected():
                connection = self.connection_manager.get_connection()
                bucket = self.connection_manager.get_bucket()
                schema_name = self.connection_manager.get_schema()
                
                with connection.transaction() as tx:
                    bucket_obj = tx.bucket(bucket)
                    schema_obj = bucket_obj.schema(schema_name)
                    table = schema_obj.table(table_name)
                    columns = table.columns()
                    
                    # Cache the result
                    stats = table.get_stats()
                    total_rows = getattr(stats, 'total_rows', 0) or 0
                    self.cache_manager.update_table_cache(table_name, columns, total_rows)
                    
                    return columns
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
            return None
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics"""
        try:
            # Check cache first
            stats = self.cache_manager.get_table_stats(table_name)
            if stats.get('total_rows', 0) > 0:
                return stats
            
            # Fetch from database if not cached
            if self.connection_manager.is_connected():
                connection = self.connection_manager.get_connection()
                bucket = self.connection_manager.get_bucket()
                schema_name = self.connection_manager.get_schema()
                
                with connection.transaction() as tx:
                    bucket_obj = tx.bucket(bucket)
                    schema_obj = bucket_obj.schema(schema_name)
                    table = schema_obj.table(table_name)
                    vast_stats = table.get_stats()
                    
                    total_rows = getattr(vast_stats, 'total_rows', 0) or 0
                    columns = table.columns()
                    
                    # Update cache
                    self.cache_manager.update_table_cache(table_name, columns, total_rows)
                    
                    return {'total_rows': total_rows}
            
            return {'total_rows': 0}
            
        except Exception as e:
            logger.error(f"Error getting stats for table {table_name}: {e}")
            return {'total_rows': 0}
    
    def create_table(self, table_name: str, schema: Schema, projections: Optional[Dict[str, List[str]]] = None):
        """Create a new table with VAST projections for optimal performance, or evolve existing table schema"""
        return self.table_operations.create_table(table_name, schema, projections)
    
    def get_table_projections(self, table_name: str) -> List[str]:
        """Get list of projection names for a table"""
        return self.table_operations.get_table_projections(table_name)
    
    def add_projection(self, table_name: str, projection_name: str, columns: List[str]):
        """Add a new projection to an existing table"""
        return self.table_operations.add_projection(table_name, projection_name, columns)
    
    # Data Operations - Delegate to DataOperations module
    def insert_single_record(self, table_name: str, data: Dict[str, Any]):
        """Insert a single Python dictionary record into a table"""
        return self.data_operations.insert_single_record(table_name, data)
    
    def insert_record_list(self, table_name: str, data: List[Dict[str, Any]]):
        """Insert a list of Python dictionary records into a table"""
        return self.data_operations.insert_record_list(table_name, data)
    
    def query_with_predicates(self, table_name: str, predicates: Optional[Any] = None, 
                             columns: Optional[List[str]] = None, limit: Optional[int] = None,
                             include_row_ids: bool = False):
        """Query data from a table with optional predicates using VAST's query capabilities"""
        return self.data_operations.query_with_predicates(
            table_name, predicates, columns, limit, include_row_ids
        )
    
    def update(self, table_name: str, data: Dict[str, List[Any]], predicate: Optional[Any] = None):
        """Update data in a table using VAST's native UPDATE capability"""
        return self.data_operations.update(table_name, data, predicate)
    
    def delete(self, table_name: str, predicate: Optional[Any] = None):
        """Delete data from a table using VAST's native DELETE capability"""
        return self.data_operations.delete(table_name, predicate)
    
    def insert(self, table_name: str, data: Dict[str, List[Any]]):
        """Insert data from a Python dictionary with row pooling and cache updates"""
        return self.data_operations.insert(table_name, data)
    
    def select(self, table_name: str, predicate: Optional[Any] = None, 
               output_by_row: bool = False, columns: Optional[List[str]] = None):
        """Query data from a table with optional predicates"""
        return self.data_operations.select(table_name, predicate, output_by_row, columns)
    
    # Batch Operations - Delegate to BatchOperations module
    def insert_batch_efficient(self, table_name: str, data: Dict[str, List[Any]], 
                              batch_size: int = DEFAULT_BATCH_SIZE, max_workers: int = DEFAULT_MAX_WORKERS):
        """Insert large datasets efficiently using row pooling and parallel processing"""
        return self.batch_operations.insert_batch_efficient(table_name, data, batch_size, max_workers)
    
    def insert_batch_transactional(self, table_name: str, data: Dict[str, List[Any]], 
                                  batch_size: int = DEFAULT_BATCH_SIZE, max_workers: int = DEFAULT_MAX_WORKERS, 
                                  max_retries: int = DEFAULT_MAX_RETRIES, enable_rollback: bool = True):
        """Insert data with transactional safety - no records are lost on failure"""
        return self.batch_operations.insert_batch_transactional(
            table_name, data, batch_size, max_workers, max_retries, enable_rollback
        )
    
    def cleanup_partial_insertion(self, table_name: str, failed_batch_ids: List[str], 
                                 batch_details: Dict[str, Any]) -> bool:
        """Clean up partial insertions when batch operations fail"""
        return self.batch_operations.cleanup_partial_insertion(table_name, failed_batch_ids, batch_details)
    
    # Analytics and Performance
    def get_performance_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance summary"""
        return self.performance_monitor.get_performance_summary(time_window)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_manager.get_cache_stats()
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache_manager.clear_cache()
        logger.info("Cleared all cached data")
    
    def refresh_table_metadata(self, table_name: str):
        """Refresh table metadata in cache (useful when columns change)"""
        try:
            if not self.connection_manager.is_connected():
                logger.warning(f"Cannot refresh metadata for {table_name}: not connected")
                return
            
            connection = self.connection_manager.get_connection()
            bucket = self.connection_manager.get_bucket()
            schema_name = self.connection_manager.get_schema()
            
            with connection.transaction() as tx:
                bucket_obj = tx.bucket(bucket)
                schema_obj = bucket_obj.schema(schema_name)
                table = schema_obj.table(table_name)
                
                # Get fresh metadata
                table_stats = table.get_stats()
                total_rows = getattr(table_stats, 'total_rows', 0) or 0
                columns = table.columns()
                
                # Update cache with fresh metadata
                self.cache_manager.update_table_cache(table_name, columns, total_rows)
                logger.info(f"Refreshed metadata for table {table_name}: {total_rows} rows, {len(columns)} columns")
                
        except Exception as e:
            logger.error(f"Error refreshing metadata for table {table_name}: {e}")
            # Invalidate cache on error to force fresh fetch next time
            self.cache_manager.invalidate_table_cache(table_name)
    
    def close(self):
        """Cleanup resources"""
        try:
            # Close connections
            self.disconnect()
            self.hybrid_analytics.close()
            
            logger.info("VastDBManager closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing VastDBManager: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

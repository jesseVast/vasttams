"""Core VastDBManager integrating all modular components"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from vastdb import connect, transaction
from vastdb.transaction.schema.table import QueryConfig
from pyarrow import Schema

from .cache import CacheManager
from .queries import PredicateBuilder, QueryOptimizer, QueryExecutor
from .analytics import TimeSeriesAnalytics, AggregationAnalytics, PerformanceMonitor, HybridAnalytics
from .endpoints import EndpointManager, LoadBalancer

logger = logging.getLogger(__name__)


class VastDBManager:
    """Refactored VastDBManager with modular architecture"""
    
    def __init__(self, endpoints: Union[str, List[str]], 
                 cache_ttl: timedelta = timedelta(minutes=30)):
        """
        Initialize VastDBManager with modular components
        
        Args:
            endpoints: Single endpoint string or list of endpoints
            cache_ttl: Cache time-to-live for table data
        """
        # Convert single endpoint to list for consistency
        if isinstance(endpoints, str):
            self.endpoints = [endpoints]
        else:
            self.endpoints = endpoints
        
        # Initialize modular components
        self.cache_manager = CacheManager(cache_ttl)
        self.predicate_builder = PredicateBuilder()
        self.query_optimizer = QueryOptimizer(self.cache_manager)
        self.query_executor = QueryExecutor(self.cache_manager)
        self.endpoint_manager = EndpointManager(self.endpoints)
        self.load_balancer = LoadBalancer(self.endpoint_manager)
        self.performance_monitor = PerformanceMonitor()
        
        # Initialize analytics components
        self.time_series_analytics = TimeSeriesAnalytics(self.cache_manager)
        self.aggregation_analytics = AggregationAnalytics(self.cache_manager)
        self.hybrid_analytics = HybridAnalytics(self.cache_manager)
        
        # VAST connection and configuration
        self.connection = None
        self.default_query_config = QueryConfig(
            num_splits=4,
            num_sub_splits=4,
            rows_per_split=1_000_000,
            limit_rows_per_sub_split=100_000,
            num_row_groups_per_sub_split=10,
            data_endpoints=None,  # VAST handles internal parallelization
            queue_priority=1
        )
        
        # Background thread for cache updates
        self._stats_update_thread = None
        self._stop_stats_update = threading.Event()
        self._start_stats_update_thread()
        
        logger.info(f"Initialized VastDBManager with {len(self.endpoints)} endpoints")
    
    def _start_stats_update_thread(self):
        """Start background thread for periodic cache updates"""
        if self._stats_update_thread is None or not self._stats_update_thread.is_alive():
            self._stop_stats_update.clear()
            self._stats_update_thread = threading.Thread(
                target=self._stats_update_worker,
                daemon=True,
                name="VastDBManager-StatsUpdate"
            )
            self._stats_update_thread.start()
            logger.info("Started background stats update thread")
    
    def _stats_update_worker(self):
        """Background worker for updating table statistics"""
        while not self._stop_stats_update.is_set():
            try:
                time.sleep(300)  # Update every 5 minutes
                if not self._stop_stats_update.is_set():
                    self._update_all_table_stats()
            except Exception as e:
                logger.error(f"Error in stats update worker: {e}")
    
    def _update_all_table_stats(self):
        """Update statistics for all cached tables"""
        try:
            table_names = self.cache_manager.get_all_table_names()
            if not table_names:
                return
            
            logger.debug(f"Updating stats for {len(table_names)} tables")
            
            for table_name in table_names:
                try:
                    self._update_table_stats(table_name)
                except Exception as e:
                    logger.warning(f"Failed to update stats for table {table_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error updating all table stats: {e}")
    
    def _update_table_stats(self, table_name: str):
        """Update statistics for a specific table"""
        try:
            if not self.connection:
                return
            
            with self.connection.transaction() as tx:
                table = tx.schema.table(table_name)
                stats = table.get_stats()
                
                # Update cache with new statistics
                total_rows = getattr(stats, 'total_rows', 0) or 0
                schema = table.columns()
                
                self.cache_manager.update_table_cache(table_name, schema, total_rows)
                
        except Exception as e:
            logger.warning(f"Failed to update stats for table {table_name}: {e}")
    
    def connect(self, endpoint: Optional[str] = None):
        """Connect to VAST database"""
        try:
            if endpoint is None:
                endpoint = self.load_balancer.get_endpoint("read")
            
            if not endpoint:
                raise RuntimeError("No healthy endpoints available")
            
            self.connection = connect(endpoint)
            logger.info(f"Connected to VAST database at {endpoint}")
            
            # Update endpoint health
            self.endpoint_manager.mark_endpoint_success(endpoint, 0.0)
            
        except Exception as e:
            if endpoint:
                self.endpoint_manager.mark_endpoint_error(endpoint, str(e))
            logger.error(f"Failed to connect to VAST database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from VAST database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from VAST database")
    
    @property
    def tables(self) -> List[str]:
        """Get list of available tables"""
        try:
            if not self.connection:
                return []
            
            # Check cache first
            cached_tables = self.cache_manager.get_all_table_names()
            if cached_tables:
                return cached_tables
            
            # Discover tables if not cached
            self._discover_tables()
            return self.cache_manager.get_all_table_names()
            
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
    
    def _discover_tables(self):
        """Discover available tables and cache their metadata"""
        try:
            if not self.connection:
                return
            
            with self.connection.transaction() as tx:
                schema = tx.schema
                for table_name in schema.table_names():
                    try:
                        table = schema.table(table_name)
                        stats = table.get_stats()
                        schema_info = table.columns()
                        
                        total_rows = getattr(stats, 'total_rows', 0) or 0
                        self.cache_manager.update_table_cache(table_name, schema_info, total_rows)
                        
                    except Exception as e:
                        logger.warning(f"Failed to discover table {table_name}: {e}")
            
            logger.info(f"Discovered {len(self.cache_manager.get_all_table_names())} tables")
            
        except Exception as e:
            logger.error(f"Error discovering tables: {e}")
    
    def get_table_columns(self, table_name: str) -> Optional[Schema]:
        """Get column definitions for a table"""
        try:
            # Check cache first
            columns = self.cache_manager.get_table_columns(table_name)
            if columns is not None:
                return columns
            
            # Fetch from database if not cached
            if self.connection:
                with self.connection.transaction() as tx:
                    table = tx.schema.table(table_name)
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
            if self.connection:
                with self.connection.transaction() as tx:
                    table = tx.schema.table(table_name)
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
    
    def create_table(self, table_name: str, schema: Schema):
        """Create a new table"""
        try:
            if not self.connection:
                raise RuntimeError("Not connected to VAST database")
            
            with self.connection.transaction() as tx:
                table = tx.schema.create_table(table_name, schema)
                
                # Cache the new table
                self.cache_manager.update_table_cache(table_name, schema, 0)
                
                logger.info(f"Created table {table_name}")
                return table
                
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise
    
    def insert_pydict(self, table_name: str, data: Dict[str, Any]):
        """Insert a Python dictionary into a table"""
        try:
            if not self.connection:
                raise RuntimeError("Not connected to VAST database")
            
            start_time = time.time()
            
            with self.connection.transaction() as tx:
                table = tx.schema.table(table_name)
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
            
            # Invalidate cache for this table
            self.cache_manager.invalidate_table_cache(table_name)
            
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
    
    def insert_pylist(self, table_name: str, data: List[Dict[str, Any]]):
        """Insert a list of Python dictionaries into a table"""
        try:
            if not self.connection:
                raise RuntimeError("Not connected to VAST database")
            
            start_time = time.time()
            
            with self.connection.transaction() as tx:
                table = tx.schema.table(table_name)
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
            
            # Invalidate cache for this table
            self.cache_manager.invalidate_table_cache(table_name)
            
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
    
    def query_with_predicates(self, table_name: str, columns: List[str], 
                             predicates: Dict[str, Any], limit: Optional[int] = None):
        """Query table with Python predicates converted to VAST filters"""
        try:
            if not self.connection:
                raise RuntimeError("Not connected to VAST database")
            
            start_time = time.time()
            
            # Convert Python predicates to VAST filter string
            vast_filter = self.predicate_builder.build_vast_predicates(predicates)
            
            # Get table and optimize query config
            with self.connection.transaction() as tx:
                table = tx.schema.table(table_name)
                
                # Create optimized query config
                config = QueryConfig()
                config.__dict__.update(self.default_query_config.__dict__)
                config = self.query_optimizer.optimize_query_config(config, table_name)
                
                # Execute query with optimization
                result = self.query_executor.execute_advanced_query(
                    table, config, columns, vast_filter, limit
                )
            
            execution_time = time.time() - start_time
            rows_returned = len(result) if result else 0
            
            # Record performance metrics
            self.performance_monitor.record_query(
                query_type="query_with_predicates",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=rows_returned,
                splits_used=config.num_splits,
                subsplits_used=config.num_sub_splits,
                success=True
            )
            
            logger.debug(f"Query with predicates on {table_name} returned {rows_returned} rows in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="query_with_predicates",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Error querying table {table_name} with predicates: {e}")
            raise
    
    def get_performance_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance summary"""
        return self.performance_monitor.get_performance_summary(time_window)
    
    def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get endpoint statistics"""
        return self.endpoint_manager.get_endpoint_stats()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_manager.get_cache_stats()
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache_manager.clear_cache()
        logger.info("Cleared all cached data")
    
    def close(self):
        """Cleanup resources"""
        try:
            # Stop background thread
            self._stop_stats_update.set()
            if self._stats_update_thread and self._stats_update_thread.is_alive():
                self._stats_update_thread.join(timeout=5)
            
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

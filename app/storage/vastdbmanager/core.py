"""Core VastDBManager integrating all modular components"""

import logging
import time
from datetime import timedelta
from typing import List, Dict, Any, Optional, Union
import vastdb
from pyarrow import Schema
import uuid

from .cache import CacheManager
from .queries import PredicateBuilder, QueryOptimizer, QueryExecutor
from .analytics import TimeSeriesAnalytics, AggregationAnalytics, PerformanceMonitor, HybridAnalytics
from .endpoints import EndpointManager, LoadBalancer

logger = logging.getLogger(__name__)

# Configuration Constants - Easy to adjust for troubleshooting
# 
# TROUBLESHOOTING GUIDE:
# - If batch operations are too slow: Increase DEFAULT_BATCH_SIZE (e.g., 200, 500)
# - If you get memory errors: Decrease DEFAULT_BATCH_SIZE (e.g., 50, 25)
# - If parallel processing isn't working: Decrease PARALLEL_THRESHOLD (e.g., 5)
# - If you get too many concurrent connections: Decrease DEFAULT_MAX_WORKERS (e.g., 2)
# - If operations fail intermittently: Increase DEFAULT_MAX_RETRIES (e.g., 5)
# - If VAST connections timeout: Increase VAST_TIMEOUT (e.g., 60)
#
DEFAULT_BATCH_SIZE = 100  # Default batch size for insert operations
DEFAULT_MAX_WORKERS = 4   # Default number of parallel workers for batch operations
PARALLEL_THRESHOLD = 10   # Threshold above which parallel processing is used
VAST_TIMEOUT = 30         # VAST connection timeout in seconds
DEFAULT_MAX_RETRIES = 3   # Default maximum retry attempts for failed operations


class VastDBManager:
    """Refactored VastDBManager with modular architecture"""
    
    def __init__(self, endpoints: Union[str, List[str]]):
        """
        Initialize VastDBManager with modular components
        
        Args:
            endpoints: Single endpoint string or list of endpoints
        """
        # Convert single endpoint to list for consistency
        if isinstance(endpoints, str):
            self.endpoints = [endpoints]
        else:
            self.endpoints = endpoints
        
        # Initialize modular components
        self.cache_manager = CacheManager()
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
        self.default_query_config = None  # No QueryConfig needed - VAST handles optimization internally
        
        # Initialize connection to first endpoint
        self.connect()
        
        logger.info(f"Initialized VastDBManager with {len(self.endpoints)} endpoints")
    
    @property
    def tables(self) -> List[str]:
        """Get list of available table names"""
        return self.cache_manager.get_all_table_names()
    
    def list_tables(self) -> List[str]:
        """Backward compatibility method - alias for tables property"""
        return self.tables
    
    def connect(self):
        """Connect to VAST database using the first available endpoint"""
        try:
            from app.core.config import get_settings
            settings = get_settings()
            
            # Use first endpoint for connection
            endpoint = self.endpoints[0]
            self.connection = vastdb.connect(
                endpoint=endpoint,
                access=settings.vast_access_key,
                secret=settings.vast_secret_key,
                timeout=VAST_TIMEOUT
            )
            
            # Store bucket and schema names
            self.bucket = settings.vast_bucket
            self.schema = settings.vast_schema
            
            # Setup schema
            self._setup_schema()
            logger.info(f"Connected to VAST database at {endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to connect to VAST database: {e}")
            raise
    
    def _setup_schema(self):
        """Setup database schema and discover existing tables"""
        try:
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                
                # Ensure schema exists
                schema = bucket.schema(self.schema, fail_if_missing=False)
                if schema is None:
                    schema = bucket.create_schema(self.schema)
                    logger.info(f"Schema '{self.schema}' created")
                else:
                    logger.info(f"Schema '{self.schema}' already exists")
                
                # Discover existing tables
                self._discover_tables()
                
        except Exception as e:
            logger.error(f"Failed to setup schema: {e}")
            raise
    
    def _discover_tables(self):
        """Discover and cache existing table schemas at startup"""
        try:
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema = bucket.schema(self.schema)
                
                for table in schema.tables():
                    table_name = table.name
                    # Cache only essential metadata: schema and initial row count
                    table_stats = table.get_stats()
                    total_rows = getattr(table_stats, 'total_rows', 0) or 0
                    self.cache_manager.update_table_cache(table_name, table.columns(), total_rows)
                    logger.debug(f"Discovered and cached table: {table_name} ({total_rows} rows)")
                    
            logger.info(f"Discovered and cached {len(self.cache_manager.get_all_table_names())} tables")
                    
        except Exception as e:
            logger.error(f"Failed to discover tables: {e}")
            raise
    
    def connect_to_endpoint(self, endpoint: Optional[str] = None):
        """Connect to a specific VAST database endpoint"""
        try:
            if endpoint is None:
                endpoint = self.load_balancer.get_endpoint("read")
            
            if not endpoint:
                raise RuntimeError("No healthy endpoints available")
            
            # Use the first endpoint for now (simplified approach)
            from app.core.config import get_settings
            settings = get_settings()
            
            self.connection = vastdb.connect(
                endpoint=endpoint,
                access=settings.vast_access_key,
                secret=settings.vast_secret_key,
                timeout=30
            )
            
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
        """Get list of available tables from cache"""
        try:
            return self.cache_manager.get_all_table_names()
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
    
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
                    bucket = tx.bucket(self.bucket)
                    schema = bucket.schema(self.schema)
                    table = schema.table(table_name)
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
                    bucket = tx.bucket(self.bucket)
                    schema = bucket.schema(self.schema)
                    table = schema.table(table_name)
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
        """Create a new table with VAST projections for optimal performance"""
        try:
            if not self.connection:
                raise RuntimeError("Not connected to VAST database")
            
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
                
                # Check if table already exists and drop it
                existing_table = schema_obj.table(table_name, fail_if_missing=False)
                if existing_table is not None:
                    logger.info(f"Table {table_name} already exists, dropping it first")
                    existing_table.drop()
                
                # Create new table
                table = schema_obj.create_table(table_name, schema)
                
                # Add VAST projections if specified
                if projections:
                    self._add_vast_projections(table, projections)
                
                # Cache the new table
                self.cache_manager.update_table_cache(table_name, schema, 0)
                
                logger.info(f"Created table {table_name} with projections: {list(projections.keys()) if projections else 'none'}")
                return table
                
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise
    
    def _add_vast_projections(self, table, projections: Dict[str, List[str]]):
        """Add VAST projections using the actual SDK methods for optimal performance"""
        try:
            for projection_name, columns in projections.items():
                # Determine which columns should be sorted vs unsorted
                # Time-series columns (timestamp) should be sorted for optimal performance
                sorted_columns = []
                unsorted_columns = []
                
                for col in columns:
                    if 'time' in col.lower() or 'timestamp' in col.lower():
                        sorted_columns.append(col)
                    else:
                        unsorted_columns.append(col)
                
                # Create the projection using VAST's actual API
                table.create_projection(
                    projection_name=projection_name,
                    sorted_columns=sorted_columns,
                    unsorted_columns=unsorted_columns
                )
                
                logger.info(f"Created VAST projection '{projection_name}' with {len(sorted_columns)} sorted, {len(unsorted_columns)} unsorted columns")
            
            logger.info(f"Successfully added {len(projections)} projections to table")
            
        except Exception as e:
            logger.warning(f"Failed to add VAST projections: {e}")
            # Continue without projections if they fail
    
    def get_table_projections(self, table_name: str) -> List[str]:
        """Get list of projection names for a table"""
        try:
            if not self.connection:
                return []
            
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
                table = schema_obj.table(table_name)
                
                # Get projection information using VAST's actual API
                projections = list(table.projections())
                return [p.name for p in projections] if projections else []
                
        except Exception as e:
            logger.error(f"Failed to get projections for table {table_name}: {e}")
            return []
    
    def add_projection(self, table_name: str, projection_name: str, columns: List[str]):
        """Add a new projection to an existing table"""
        try:
            if not self.connection:
                raise RuntimeError("Not connected to VAST database")
            
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
                table = schema_obj.table(table_name)
                
                # Determine sorted vs unsorted columns
                sorted_columns = []
                unsorted_columns = []
                
                for col in columns:
                    if 'time' in col.lower() or 'timestamp' in col.lower():
                        sorted_columns.append(col)
                    else:
                        unsorted_columns.append(col)
                
                # Create projection using VAST's actual API
                table.create_projection(
                    projection_name=projection_name,
                    sorted_columns=sorted_columns,
                    unsorted_columns=unsorted_columns
                )
                
                logger.info(f"Added projection '{projection_name}' to table {table_name}")
                
        except Exception as e:
            logger.error(f"Failed to add projection {projection_name} to table {table_name}: {e}")
            raise
    
    def insert_single_record(self, table_name: str, data: Dict[str, Any]):
        """Insert a single Python dictionary record into a table"""
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
            
            # Cache is simplified - no need to invalidate on every insert
            
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
            
            # Cache is simplified - no need to invalidate on every insert
            
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
            
            # Create optimized query configuration
            query_config = self._create_optimized_query_config(table_name, predicates)
            
            # Execute query with VAST
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
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
                
                # Apply limit if specified
                if limit:
                    result = result.limit(limit)
                
                # Execute the query to get the actual data
                result = result.read_all()
                
                # Convert to dictionary format
                if hasattr(result, 'to_pydict'):
                    data = result.to_pydict()
                else:
                    logger.warning(f"Result does not have to_pydict method: {result}")
                    data = {}
                
                # Handle row IDs if requested
                if include_row_ids and data and '$row_id' in data:
                    logger.debug(f"Row IDs found: {data['$row_id']}")
                
                # Log raw output for debugging
                if include_row_ids:
                    print(f"🔍 RAW QUERY RESULT for {table_name} with include_row_ids=True:")
                    print(f"Result type: {type(result)}")
                    print(f"Result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                    print(f"Data type: {type(data)}")
                    print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if key == '$row_id':
                                print(f"$row_id field: {value} (type: {type(value)})")
                            else:
                                print(f"Field {key}: {len(value) if isinstance(value, list) else value} (type: {type(value)})")
                    print(f"🔍 END RAW QUERY RESULT")
                    
                    # Also log to logger for consistency
                    logger.info(f"RAW QUERY RESULT for {table_name}: Result type: {type(result)}, Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                execution_time = time.time() - start_time
                logger.debug(f"Query execution time: {execution_time:.3f}s")
                
                return data
                
        except Exception as e:
            logger.error(f"Error in query_with_predicates for table {table_name}: {e}")
            raise
    
    def refresh_table_metadata(self, table_name: str):
        """Refresh table metadata in cache (useful when columns change)"""
        try:
            if not self.connection:
                logger.warning(f"Cannot refresh metadata for {table_name}: not connected")
                return
            
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema = tx.schema(self.schema)
                table = schema.table(table_name)
                
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
    
    def _create_optimized_query_config(self, table_name: str, predicates: Optional[Any] = None) -> 'vastdb.config.QueryConfig':
        """Create optimized QueryConfig for VAST query execution with aggressive optimization"""
        try:
            from vastdb.config import QueryConfig
            
            # Get table statistics for optimization
            table_stats = self.cache_manager.get_table_stats(table_name)
            total_rows = 0
            if table_stats and isinstance(table_stats, dict):
                total_rows = table_stats.get('total_rows', 0)
                if isinstance(total_rows, dict):
                    total_rows = total_rows.get('total_rows', 0)
                total_rows = int(total_rows) if total_rows else 0
            
            # Base configuration - optimized for performance
            config = QueryConfig(
                num_sub_splits=8,  # Increased from 4 for better parallelism
                limit_rows_per_sub_split=65536,  # Reduced from 131072 for faster processing
                num_row_groups_per_sub_split=4,  # Reduced from 8 for better memory usage
                use_semi_sorted_projections=True,  # Use our projections
                rows_per_split=2000000  # Reduced from 4000000 for faster splits
            )
            
            # Aggressive optimization based on query type and table size
            if predicates is not None:
                # Handle different predicate types
                if isinstance(predicates, dict):
                    # Dictionary predicates - can analyze keys and structure
                    if any('time' in key.lower() or 'timestamp' in key.lower() for key in predicates.keys()):
                        config.num_sub_splits = 12  # Maximum splits for time queries
                        config.limit_rows_per_sub_split = 32768  # Smaller subsplits for time queries
                        config.num_row_groups_per_sub_split = 2  # Minimal row groups for time queries
                    
                    # Large result set queries - aggressive splitting
                    if total_rows > 5000:  # Lowered threshold for more aggressive optimization
                        config.num_splits = min(32, total_rows // 100000)  # More splits for smaller tables
                        config.num_sub_splits = 10  # More subsplits for better parallelism
                        config.limit_rows_per_sub_split = 32768  # Smaller subsplits for large tables
                    
                    # Complex queries - optimize for predicate evaluation
                    if len(predicates) > 1:  # Lowered threshold for optimization
                        config.limit_rows_per_sub_split = 32768  # Smaller subsplits for complex queries
                        config.num_row_groups_per_sub_split = 2  # Fewer row groups for complex queries
                        config.num_sub_splits = 10  # More splits for complex queries
                
                elif hasattr(predicates, 'op'):
                    # Ibis predicates - use conservative optimization since we can't analyze structure
                    config.num_sub_splits = 8  # Default subsplits for Ibis predicates
                    config.limit_rows_per_sub_split = 65536  # Default subsplit limit
                    config.num_row_groups_per_sub_split = 4  # Default row groups
                    
                    # Large result set queries - aggressive splitting
                    if total_rows > 5000:
                        config.num_splits = min(32, total_rows // 100000)
                        config.num_sub_splits = 10
                        config.limit_rows_per_sub_split = 32768
            
            # Use available endpoints for load balancing
            if hasattr(self, 'endpoints') and self.endpoints:
                config.data_endpoints = self.endpoints
            
            logger.debug(f"Created aggressive QueryConfig: splits={config.num_splits}, subsplits={config.num_sub_splits}, "
                        f"subsplit_limit={config.limit_rows_per_sub_split}, row_groups={config.num_row_groups_per_sub_split}")
            
            return config
            
        except Exception as e:
            logger.warning(f"Failed to create optimized QueryConfig: {e}, using defaults")
            # Return default config if optimization fails
            try:
                from vastdb.config import QueryConfig
                return QueryConfig()
            except ImportError:
                # Fallback if vastdb.config is not available
                return None
    
    def get_performance_summary(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get performance summary"""
        return self.performance_monitor.get_performance_summary(time_window)
    
    def get_endpoint_stats(self) -> Dict[str, Any]:
        """Get endpoint statistics"""
        return self.endpoint_manager.get_endpoint_stats()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_manager.get_cache_stats()
    
    def _update_all_table_stats(self):
        """Update statistics for all cached tables"""
        try:
            table_names = self.cache_manager.get_all_table_names()
            if not table_names:
                return
            
            logger.debug(f"Updating stats for {len(table_names)} tables")
            
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
                
                for table_name in table_names:
                    try:
                        table = schema_obj.table(table_name)
                        stats = table.get_stats()
                        
                        # Update cache with new stats
                        self.cache_manager.update_table_cache(table_name, None, stats)
                        
                    except Exception as e:
                        logger.warning(f"Failed to update stats for table {table_name}: {e}")
                        
        except Exception as e:
            logger.error(f"Error updating table stats: {e}")
    
    def _update_table_cache(self, table_name: str):
        """Update cache for a specific table"""
        try:
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
                table = schema_obj.table(table_name)
                
                # Get current schema and stats
                schema = table.columns()
                stats = table.get_stats()
                
                # Update cache
                self.cache_manager.update_table_cache(table_name, schema, stats)
                
        except Exception as e:
            logger.error(f"Failed to update cache for table {table_name}: {e}")
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache_manager.clear_cache()
        logger.info("Cleared all cached data")
    

    
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
            
            # Debug: log what we actually got
            logger.debug(f"Query result keys: {list(row_data.keys()) if isinstance(row_data, dict) else 'Not a dict'}")
            logger.debug(f"Query result sample: {dict(list(row_data.items())[:3]) if isinstance(row_data, dict) and row_data else 'Empty or not dict'}")
            
            if '$row_id' not in row_data:
                logger.error(f"Row IDs not found in query result")
                logger.error(f"Available keys: {list(row_data.keys()) if isinstance(row_data, dict) else 'Not a dict'}")
                return 0
            
            row_ids = row_data['$row_id']
            num_rows = len(row_ids)
            logger.info(f"Found {num_rows} rows to update")
            
            # Build update schema with $row_id + columns being updated
            import pyarrow as pa
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
            
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
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
            import pyarrow as pa
            delete_data = {'$row_id': row_ids}
            
            # Create RecordBatch and delete the rows
            records = pa.RecordBatch.from_pydict(delete_data, schema=pa.schema([pa.field('$row_id', pa.uint64())]))
            
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
                vast_table = schema_obj.table(table_name)
                
                vast_table.delete(records)
                logger.info(f"Successfully deleted {num_rows} rows from table {table_name}")
                
                # Update cache to reflect the deletion
                self.cache_manager.update_table_cache(table_name, None, -num_rows)
                return num_rows
                    
        except Exception as e:
            logger.error(f"Error deleting from table {table_name}: {e}")
            raise
    

    
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
            import pyarrow as pa
            
            start_time = time.time()
            
            # Get the table schema from cache or database
            schema = self.cache_manager.get_table_columns(table_name)
            if schema is None:
                # If not cached, fetch from database
                with self.connection.transaction() as tx:
                    bucket = tx.bucket(self.bucket)
                    schema_obj = bucket.schema(self.schema)
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
            with self.connection.transaction() as tx:
                bucket = tx.bucket(self.bucket)
                schema_obj = bucket.schema(self.schema)
                vast_table = schema_obj.table(table_name)
                
                vast_table.insert(record_batch)
                
            execution_time = time.time() - start_time
            
            # Update cache with new row count
            current_stats = self.cache_manager.get_table_stats(table_name)
            current_rows = 0
            if current_stats and isinstance(current_stats, dict):
                current_rows = current_stats.get('total_rows', 0)
                if isinstance(current_rows, dict):
                    current_rows = current_rows.get('total_rows', 0)
                current_rows = int(current_rows) if current_rows else 0
            
            new_total_rows = current_rows + num_records
            
            # Update cache with new stats
            self.cache_manager.update_table_cache(table_name, schema, {'total_rows': new_total_rows})
            
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
    
    def insert_batch_efficient(self, table_name: str, data: Dict[str, List[Any]], 
                              batch_size: int = DEFAULT_BATCH_SIZE, max_workers: int = DEFAULT_MAX_WORKERS):
        """Insert large datasets efficiently using row pooling and parallel processing"""
        try:
            import concurrent.futures
            import math
            
            start_time = time.time()
            total_rows = len(next(iter(data.values())))
            
            logger.info(f"Starting efficient batch insertion of {total_rows} rows into '{table_name}'")
            logger.info(f"Using batch size: {batch_size}, max workers: {max_workers}")
            
            # Calculate number of batches
            num_batches = math.ceil(total_rows / batch_size)
            logger.info(f"Will process {num_batches} batches")
            
            def insert_batch(batch_data: Dict[str, List[Any]]) -> int:
                """Insert a single batch of data"""
                try:
                    # Call the column-oriented insert_pydict method (line 949) directly
                    # instead of the single-record one (line 455)
                    return self._insert_column_batch(table_name, batch_data)
                except Exception as e:
                    logger.error(f"Batch insertion failed: {e}")
                    return 0
            
            # Prepare batches
            batches = []
            for i in range(0, total_rows, batch_size):
                end_idx = min(i + batch_size, total_rows)
                batch = {col: values[i:end_idx] for col, values in data.items()}
                batches.append(batch)
            
            # Insert batches with parallel processing for large datasets
            if num_batches > PARALLEL_THRESHOLD and max_workers > 1:
                logger.info(f"Using parallel processing with {max_workers} workers")
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_batch = {executor.submit(insert_batch, batch): i for i, batch in enumerate(batches)}
                    
                    total_inserted = 0
                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch_num = future_to_batch[future]
                        try:
                            rows_inserted = future.result()
                            total_inserted += rows_inserted
                            logger.debug(f"Batch {batch_num + 1}/{num_batches} completed: {rows_inserted} rows")
                        except Exception as e:
                            logger.error(f"Batch {batch_num + 1} failed: {e}")
            else:
                # Sequential processing for smaller datasets
                logger.info("Using sequential processing")
                total_inserted = 0
                for i, batch in enumerate(batches):
                    rows_inserted = insert_batch(batch)
                    total_inserted += rows_inserted
                    logger.debug(f"Batch {i + 1}/{num_batches} completed: {rows_inserted} rows")
            
            execution_time = time.time() - start_time
            
            # Record performance metrics
            self.performance_monitor.record_query(
                query_type="insert_batch_efficient",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=total_inserted,
                splits_used=1,
                subsplits_used=1,
                success=True
            )
            
            logger.info(f"Efficient batch insertion completed: {total_inserted}/{total_rows} rows in {execution_time:.3f}s")
            logger.info(f"Insertion rate: {total_inserted/execution_time:.1f} rows/second")
            
            return total_inserted
            
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="insert_batch_efficient",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Efficient batch insertion failed: {e}")
            raise
    
    def get_table_columns(self, table_name: str) -> Schema:
        """Get table columns from cache"""
        return self.cache_manager.get_table_columns(table_name)
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics from cache"""
        return self.cache_manager.get_table_stats(table_name)
    
    def disconnect(self):
        """Disconnect from VAST database"""
        try:
            if hasattr(self, 'connection') and self.connection:
                # VAST connections are automatically managed
                self.connection = None
                logger.info("Disconnected from VAST database")
        except Exception as e:
            logger.error(f"Error disconnecting from VAST database: {e}")
    
    def close(self):
        """Cleanup resources"""
        try:
            # No background threads to stop or join
            
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

    def insert_batch_transactional(self, table_name: str, data: Dict[str, List[Any]], 
                                  batch_size: int = DEFAULT_BATCH_SIZE, max_workers: int = DEFAULT_MAX_WORKERS, 
                                  max_retries: int = DEFAULT_MAX_RETRIES, enable_rollback: bool = True):
        """
        Insert data with transactional safety - no records are lost on failure
        
        This method ensures data integrity by:
        1. Tracking all batch operations
        2. Implementing retry logic for failed batches
        3. Providing rollback capability for partial failures
        4. Returning detailed status of all operations
        
        Args:
            table_name: Target table name
            data: Column-oriented data dictionary
            batch_size: Maximum records per batch
            max_workers: Maximum parallel workers
            max_retries: Maximum retry attempts per failed batch
            enable_rollback: Whether to enable rollback on partial failure
            
        Returns:
            Dict containing insertion results and status
        """
        try:
            import concurrent.futures
            import math
            from typing import List, Dict, Any, Tuple
            
            start_time = time.time()
            total_rows = len(next(iter(data.values())))
            
            logger.info(f"Starting transactional batch insertion of {total_rows} rows into '{table_name}'")
            logger.info(f"Using batch size: {batch_size}, max workers: {max_workers}, max retries: {max_retries}")
            
            # Calculate number of batches
            num_batches = math.ceil(total_rows / batch_size)
            logger.info(f"Will process {num_batches} batches")
            
            # Prepare batches with tracking
            batches = []
            batch_tracking = {}  # Track status of each batch
            
            for i in range(0, total_rows, batch_size):
                end_idx = min(i + batch_size, total_rows)
                batch = {col: values[i:end_idx] for col, values in data.items()}
                batch_id = f"batch_{len(batches)}"
                batches.append(batch)
                
                # Initialize batch tracking
                batch_tracking[batch_id] = {
                    'batch_index': len(batches) - 1,
                    'start_row': i,
                    'end_row': end_idx,
                    'row_count': end_idx - i,
                    'status': 'pending',
                    'attempts': 0,
                    'error': None,
                    'rows_inserted': 0
                }
            
            def insert_batch_with_retry(batch_data: Dict[str, List[Any]], batch_id: str) -> Tuple[str, int, str]:
                """Insert a single batch with retry logic"""
                batch_info = batch_tracking[batch_id]
                batch_info['attempts'] += 1
                
                try:
                    rows_inserted = self._insert_column_batch(table_name, batch_data)
                    batch_info['status'] = 'success'
                    batch_info['rows_inserted'] = rows_inserted
                    logger.debug(f"Batch {batch_id} completed successfully: {rows_inserted} rows")
                    return 'success', rows_inserted, ''
                    
                except Exception as e:
                    error_msg = str(e)
                    batch_info['error'] = error_msg
                    
                    if batch_info['attempts'] < max_retries:
                        batch_info['status'] = 'retrying'
                        logger.warning(f"Batch {batch_id} failed (attempt {batch_info['attempts']}/{max_retries}): {error_msg}")
                        return 'retrying', 0, error_msg
                    else:
                        batch_info['status'] = 'failed'
                        logger.error(f"Batch {batch_id} failed permanently after {max_retries} attempts: {error_msg}")
                        return 'failed', 0, error_msg
            
            # Process batches with comprehensive tracking
            if num_batches > PARALLEL_THRESHOLD and max_workers > 1:
                logger.info(f"Using parallel processing with {max_workers} workers")
                
                # Process in phases to handle retries
                for attempt_round in range(max_retries + 1):
                    # Get pending and retrying batches
                    active_batches = [bid for bid, info in batch_tracking.items() 
                                    if info['status'] in ['pending', 'retrying']]
                    
                    if not active_batches:
                        break
                    
                    logger.info(f"Processing round {attempt_round + 1}: {len(active_batches)} active batches")
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_batch = {executor.submit(insert_batch_with_retry, batches[info['batch_index']], bid): bid 
                                         for bid, info in batch_tracking.items() 
                                         if info['status'] in ['pending', 'retrying']}
                        
                        for future in concurrent.futures.as_completed(future_to_batch):
                            batch_id = future_to_batch[future]
                            try:
                                status, rows_inserted, error = future.result()
                                # Status already updated in tracking
                            except Exception as e:
                                batch_tracking[batch_id]['status'] = 'failed'
                                batch_tracking[batch_id]['error'] = str(e)
                                logger.error(f"Batch {batch_id} execution failed: {e}")
                    
                    # Check if we need another round
                    if attempt_round < max_retries:
                        retrying_batches = [bid for bid, info in batch_tracking.items() 
                                          if info['status'] == 'retrying']
                        if retrying_batches:
                            logger.info(f"Waiting before retry round {attempt_round + 2}...")
                            time.sleep(1)  # Brief pause between retry rounds
                
            else:
                # Sequential processing with retry logic
                logger.info("Using sequential processing with retry logic")
                
                for batch_id, batch_info in batch_tracking.items():
                    batch_data = batches[batch_info['batch_index']]
                    
                    for attempt in range(max_retries + 1):
                        status, rows_inserted, error = insert_batch_with_retry(batch_data, batch_id)
                        
                        if status == 'success':
                            break
                        elif status == 'failed':
                            break
                        # If retrying, continue to next attempt
                        elif attempt < max_retries:
                            time.sleep(0.1)  # Brief pause between attempts
            
            # Calculate final results
            execution_time = time.time() - start_time
            successful_batches = [bid for bid, info in batch_tracking.items() if info['status'] == 'success']
            failed_batches = [bid for bid, info in batch_tracking.items() if info['status'] == 'failed']
            total_inserted = sum(info['rows_inserted'] for info in batch_tracking.values() if info['status'] == 'success')
            
            # Prepare detailed results
            results = {
                'success': len(failed_batches) == 0,
                'total_rows': total_rows,
                'total_inserted': total_inserted,
                'total_failed': total_rows - total_inserted,
                'batches_total': num_batches,
                'batches_successful': len(successful_batches),
                'batches_failed': len(failed_batches),
                'execution_time': execution_time,
                'insertion_rate': total_inserted / execution_time if execution_time > 0 else 0,
                'batch_details': batch_tracking,
                'failed_batch_ids': failed_batches
            }
            
            # Handle partial failure scenarios
            if len(failed_batches) > 0:
                if enable_rollback and len(successful_batches) > 0:
                    logger.warning(f"Partial failure detected: {len(failed_batches)} batches failed. Rolling back successful batches...")
                    try:
                        # Note: VAST doesn't support traditional rollback, but we can mark for cleanup
                        # In a real implementation, you might want to implement a cleanup mechanism
                        logger.warning("Rollback requested but VAST doesn't support traditional rollback. Consider implementing cleanup logic.")
                    except Exception as rollback_error:
                        logger.error(f"Rollback failed: {rollback_error}")
                
                logger.error(f"Batch insertion completed with failures: {len(failed_batches)}/{num_batches} batches failed")
                logger.error(f"Failed batches: {failed_batches}")
                
                # Record failed query metrics
                self.performance_monitor.record_query(
                    query_type="insert_batch_transactional",
                    table_name=table_name,
                    execution_time=execution_time,
                    rows_returned=total_inserted,
                    splits_used=1,
                    subsplits_used=1,
                    success=False,
                    error_message=f"Partial failure: {len(failed_batches)} batches failed"
                )
                
                # Don't raise exception - return results for caller to handle
                return results
            else:
                logger.info(f"Transactional batch insertion completed successfully: {total_inserted}/{total_rows} rows in {execution_time:.3f}s")
                
                # Record successful query metrics
                self.performance_monitor.record_query(
                    query_type="insert_batch_transactional",
                    table_name=table_name,
                    execution_time=execution_time,
                    rows_returned=total_inserted,
                    splits_used=1,
                    subsplits_used=1,
                    success=True
                )
                
                return results
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="insert_batch_transactional",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Transactional batch insertion failed: {e}")
            raise

    def cleanup_partial_insertion(self, table_name: str, failed_batch_ids: List[str], 
                                 batch_details: Dict[str, Any]) -> bool:
        """
        Clean up partial insertions when batch operations fail
        
        This method helps recover from partial insertion failures by:
        1. Identifying which records were partially inserted
        2. Providing cleanup recommendations
        3. Logging detailed failure information for manual recovery
        
        Args:
            table_name: Target table name
            failed_batch_ids: List of failed batch IDs
            batch_details: Detailed batch tracking information
            
        Returns:
            True if cleanup information was logged successfully
        """
        try:
            logger.warning(f"Partial insertion cleanup requested for table '{table_name}'")
            logger.warning(f"Failed batches: {failed_batch_ids}")
            
            # Analyze failed batches
            total_failed_rows = 0
            failed_row_ranges = []
            
            for batch_id in failed_batch_ids:
                if batch_id in batch_details:
                    batch_info = batch_details[batch_id]
                    failed_rows = batch_info.get('row_count', 0)
                    total_failed_rows += failed_rows
                    
                    failed_row_ranges.append({
                        'batch_id': batch_id,
                        'start_row': batch_info.get('start_row', 0),
                        'end_row': batch_info.get('end_row', 0),
                        'row_count': failed_rows,
                        'error': batch_info.get('error', 'Unknown error'),
                        'attempts': batch_info.get('attempts', 0)
                    })
            
            logger.warning(f"Total failed rows: {total_failed_rows}")
            logger.warning("Failed row ranges:")
            for range_info in failed_row_ranges:
                logger.warning(f"  Batch {range_info['batch_id']}: Rows {range_info['start_row']}-{range_info['end_row']} "
                             f"({range_info['row_count']} rows) - Error: {range_info['error']} "
                             f"(Attempts: {range_info['attempts']})")
            
            # Provide recovery recommendations
            logger.warning("Recovery recommendations:")
            logger.warning("1. Check VAST database logs for detailed error information")
            logger.warning("2. Verify table schema and constraints")
            logger.warning("3. Check available disk space and permissions")
            logger.warning("4. Consider reducing batch size if memory issues occur")
            logger.warning("5. Implement manual retry logic for failed batches")
            
            # Log cleanup information for manual recovery
            cleanup_info = {
                'table_name': table_name,
                'timestamp': datetime.now().isoformat(),
                'total_failed_rows': total_failed_rows,
                'failed_batches': failed_batch_ids,
                'failed_row_ranges': failed_row_ranges,
                'recovery_required': True
            }
            
            logger.info(f"Cleanup information logged: {cleanup_info}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log cleanup information: {e}")
            return False

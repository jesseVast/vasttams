"""Query execution with splits optimization for VastDBManager"""

import logging
from typing import List, Dict, Any, Optional
from pyarrow import Table

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Executes queries with VAST splits optimization"""
    
    def __init__(self, cache_manager):
        """Initialize query executor with cache manager"""
        self.cache_manager = cache_manager
    
    def execute_with_splits(self, table: Table, config, query_func, *args, **kwargs):
        """Execute query with splits optimization"""
        try:
            # Apply splits optimization
            config = self._apply_splits_optimization(config, table.name)
            
            # Execute the query
            result = query_func(*args, **kwargs)
            
            logger.debug(f"Executed query with {config.num_splits} splits, "
                        f"{config.num_sub_splits} subsplits on table {table.name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query with splits on table {table.name}: {e}")
            raise
    
    def _apply_splits_optimization(self, config, table_name: str):
        """Apply splits optimization to QueryConfig"""
        # Get cached stats for optimization
        stats = self.cache_manager.get_table_stats(table_name)
        total_rows = stats.get('total_rows', 0)
        
        # Ensure minimum splits for parallel processing
        if config.num_splits is None or config.num_splits < 1:
            config.num_splits = max(1, min(8, total_rows // 1_000_000))
        
        # Ensure minimum subsplits for memory efficiency
        if config.num_sub_splits is None or config.num_sub_splits < 1:
            config.num_sub_splits = max(2, min(8, total_rows // 100_000))
        
        # Adjust row limits based on table size
        if total_rows < 100_000:
            config.limit_rows_per_sub_split = min(config.limit_rows_per_sub_split, 10_000)
        
        return config
    
    def execute_advanced_query(self, table: Table, config, columns: List[str], 
                              predicates: str = "", limit: Optional[int] = None):
        """Execute advanced query with optimization"""
        try:
            # Build the query
            query = table.select(columns)
            
            # Apply predicates if provided
            if predicates:
                query = query.filter(predicates)
            
            # Apply limit if specified
            if limit:
                query = query.limit(limit)
            
            # Execute with splits optimization
            return self.execute_with_splits(table, config, query.collect)
            
        except Exception as e:
            logger.error(f"Error executing advanced query on table {table.name}: {e}")
            raise
    
    def execute_time_series_query(self, table: Table, config, columns: List[str],
                                 start_time, end_time, time_column: str = "timestamp"):
        """Execute time-series query with optimization"""
        try:
            # Build time range filter
            time_filter = f"{time_column} BETWEEN '{start_time}' AND '{end_time}'"
            
            # Execute with time-series optimization
            return self.execute_advanced_query(table, config, columns, time_filter)
            
        except Exception as e:
            logger.error(f"Error executing time-series query on table {table.name}: {e}")
            raise
    
    def execute_aggregation_query(self, table: Table, config, columns: List[str],
                                 group_by: List[str], predicates: str = ""):
        """Execute aggregation query with optimization"""
        try:
            # Build the aggregation query
            query = table.select(columns)
            
            # Apply predicates if provided
            if predicates:
                query = query.filter(predicates)
            
            # Apply grouping
            if group_by:
                query = query.group_by(group_by)
            
            # Execute with aggregation optimization
            return self.execute_with_splits(table, config, query.collect)
            
        except Exception as e:
            logger.error(f"Error executing aggregation query on table {table.name}: {e}")
            raise

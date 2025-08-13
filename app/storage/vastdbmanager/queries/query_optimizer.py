"""Query optimization strategies for VastDBManager"""

import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Optimizes QueryConfig for different query types"""
    
    def __init__(self, cache_manager):
        """Initialize query optimizer with cache manager"""
        self.cache_manager = cache_manager
    
    def optimize_query_config(self, config, table_name: str):
        """Optimize QueryConfig using cached table statistics"""
        
        # Get cached stats (no database query)
        stats = self.cache_manager.get_table_stats(table_name)
        total_rows = stats.get('total_rows', 0)
        
        # Auto-calculate splits if not specified
        if config.num_splits is None:
            config.num_splits = max(1, total_rows // config.rows_per_split)
            logger.debug(f"Auto-calculated {config.num_splits} splits for {table_name} "
                        f"({total_rows} rows)")
        
        # Optimize subsplits based on cached row count
        if total_rows > 10_000_000:  # Large table
            config.num_sub_splits = 8  # More subsplits for better parallelism
        elif total_rows > 1_000_000:  # Medium table
            config.num_sub_splits = 4  # Default subsplits
        else:  # Small table
            config.num_sub_splits = 2  # Fewer subsplits to avoid overhead
        
        # Adjust row limits for small tables
        if total_rows < 100_000:
            config.limit_rows_per_sub_split = 10_000
        
        logger.debug(f"Optimized config for {table_name}: "
                    f"{config.num_splits} splits, {config.num_sub_splits} subsplits")
        
        return config
    
    def optimize_time_series_query(self, config, table_name: str, start_time: datetime, end_time: datetime):
        """Optimize QueryConfig for time-series queries"""
        
        # Get cached stats
        stats = self.cache_manager.get_table_stats(table_name)
        total_rows = stats.get('total_rows', 0)
        
        # Time-series queries benefit from more subsplits for parallel processing
        if total_rows > 1_000_000:
            config.num_sub_splits = 8
        else:
            config.num_sub_splits = 4
        
        # Adjust splits based on time range size
        time_diff = (end_time - start_time).total_seconds()
        if time_diff < 3600:  # Less than 1 hour
            config.num_splits = max(1, total_rows // 1_000_000)  # Smaller splits for short time ranges
        else:
            config.num_splits = max(1, total_rows // config.rows_per_split)
        
        logger.debug(f"Optimized time-series config for {table_name}: "
                    f"{config.num_splits} splits, {config.num_sub_splits} subsplits")
        
        return config
    
    def optimize_aggregation_query(self, config, table_name: str, group_by: List[str]):
        """Optimize QueryConfig for aggregation queries"""
        
        # Get cached stats
        stats = self.cache_manager.get_table_stats(table_name)
        total_rows = stats.get('total_rows', 0)
        
        # Aggregation queries benefit from fewer splits but more subsplits
        if total_rows > 10_000_000:
            config.num_splits = 4  # Fewer splits for aggregation
            config.num_sub_splits = 8
        elif total_rows > 1_000_000:
            config.num_splits = 2
            config.num_sub_splits = 6
        else:
            config.num_splits = 1
            config.num_sub_splits = 4
        
        # Reduce row limits for aggregation to improve memory efficiency
        config.limit_rows_per_sub_split = min(config.limit_rows_per_sub_split, 64 * 1024)
        
        logger.debug(f"Optimized aggregation config for {table_name}: "
                    f"{config.num_splits} splits, {config.num_sub_splits} subsplits")
        
        return config

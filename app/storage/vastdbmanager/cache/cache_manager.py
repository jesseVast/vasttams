"""Simplified cache management for VastDBManager - only essential table metadata"""

import logging
from typing import Dict, Any, Optional
from pyarrow import Schema

from .table_cache import TableCacheEntry

logger = logging.getLogger(__name__)


class CacheManager:
    """Simplified cache manager for table metadata only"""
    
    def __init__(self):
        """Initialize simplified cache manager"""
        self.table_cache: Dict[str, TableCacheEntry] = {}
        logger.debug("Initialized simplified cache manager")
    
    def get_table_columns(self, table_name: str) -> Optional[Schema]:
        """Get column definitions for a table from cache"""
        cache_entry = self.table_cache.get(table_name)
        if cache_entry:
            logger.debug(f"Cache hit for table {table_name} columns")
            return cache_entry.schema
        logger.debug(f"Cache miss for table {table_name} columns")
        return None
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics from cache"""
        cache_entry = self.table_cache.get(table_name)
        if cache_entry:
            return {'total_rows': cache_entry.total_rows}
        return {'total_rows': 0}
    
    def update_table_cache(self, table_name: str, schema: Schema, total_rows: int = 0):
        """Update cache for a specific table"""
        self.table_cache[table_name] = TableCacheEntry(
            schema=schema,
            total_rows=total_rows
        )
        logger.debug(f"Updated cache for table {table_name}: {total_rows} rows")
    
    def invalidate_table_cache(self, table_name: str):
        """Invalidate cached data for a table"""
        if table_name in self.table_cache:
            del self.table_cache[table_name]
            logger.debug(f"Invalidated cache for table {table_name}")
    
    def get_all_table_names(self) -> list[str]:
        """Get list of all cached table names"""
        return list(self.table_cache.keys())
    
    def clear_cache(self):
        """Clear all cached data"""
        self.table_cache.clear()
        logger.info("Cleared all table cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get simple cache statistics"""
        return {
            'total_entries': len(self.table_cache),
            'table_names': list(self.table_cache.keys())
        }

"""Cache management for VastDBManager"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from pyarrow import Schema

from .table_cache import TableCacheEntry

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages table cache operations and background updates"""
    
    def __init__(self, cache_ttl: timedelta = timedelta(minutes=30)):
        """Initialize cache manager"""
        self.table_cache: Dict[str, TableCacheEntry] = {}
        self.cache_lock = threading.RLock()
        self.cache_ttl = cache_ttl
        self.stats_update_interval = timedelta(minutes=30)
        self.last_stats_update = datetime.now()
    
    def get_table_columns(self, table_name: str) -> Schema:
        """Get column definitions for a table from cache"""
        with self.cache_lock:
            cache_entry = self.table_cache.get(table_name)
            
            if cache_entry is not None and not cache_entry.is_expired():
                logger.debug(f"Cache hit for table {table_name} columns")
                return cache_entry.schema
            
            logger.debug(f"Cache miss for table {table_name} columns")
            return None
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics from cache"""
        with self.cache_lock:
            cache_entry = self.table_cache.get(table_name)
            
            if cache_entry is not None and not cache_entry.is_expired():
                return {'total_rows': cache_entry.total_rows}
            
            return {'total_rows': 0}
    
    def update_table_cache(self, table_name: str, schema: Schema, total_rows: int):
        """Update cache for a specific table"""
        with self.cache_lock:
            self.table_cache[table_name] = TableCacheEntry(
                schema=schema,
                total_rows=total_rows,
                last_updated=datetime.now(),
                cache_ttl=self.cache_ttl
            )
            logger.debug(f"Updated cache for table {table_name}: {total_rows} rows")
    
    def invalidate_table_cache(self, table_name: str):
        """Invalidate cached data for a table"""
        with self.cache_lock:
            if table_name in self.table_cache:
                del self.table_cache[table_name]
                logger.debug(f"Invalidated cache for table {table_name}")
    
    def get_all_table_names(self) -> list[str]:
        """Get list of all cached table names"""
        with self.cache_lock:
            return list(self.table_cache.keys())
    
    def clear_cache(self):
        """Clear all cached data"""
        with self.cache_lock:
            self.table_cache.clear()
            logger.info("Cleared all table cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        with self.cache_lock:
            total_entries = len(self.table_cache)
            expired_entries = sum(1 for entry in self.table_cache.values() if entry.is_expired())
            active_entries = total_entries - expired_entries
            
            return {
                'total_entries': total_entries,
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'cache_ttl_minutes': self.cache_ttl.total_seconds() / 60,
                'last_stats_update': self.last_stats_update.isoformat()
            }

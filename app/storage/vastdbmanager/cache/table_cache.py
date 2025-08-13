"""Table cache data structures for VastDBManager"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pyarrow import Schema


@dataclass
class TableCacheEntry:
    """Enhanced cache entry containing both schema and stats"""
    schema: Schema
    total_rows: int
    last_updated: datetime
    cache_ttl: timedelta = timedelta(minutes=30)  # 30 minute cache
    
    def is_expired(self) -> bool:
        """Check if cache has expired"""
        return datetime.now() - self.last_updated > self.cache_ttl

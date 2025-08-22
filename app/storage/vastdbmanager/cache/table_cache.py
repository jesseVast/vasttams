"""Simplified table cache for VastDBManager - only stores essential metadata"""

from dataclasses import dataclass
from pyarrow import Schema


@dataclass
class TableCacheEntry:
    """Simple cache entry containing only essential table metadata"""
    schema: Schema
    total_rows: int = 0
    
    def __post_init__(self):
        """Ensure total_rows is always an integer"""
        if self.total_rows is None:
            self.total_rows = 0
        self.total_rows = int(self.total_rows)

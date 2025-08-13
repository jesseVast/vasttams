"""Test the new modular VastDBManager architecture"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pyarrow import Schema, field, table
from typing import List, Dict, Any

# Import the new modular components
from app.storage.vastdbmanager.cache import CacheManager, TableCacheEntry
from app.storage.vastdbmanager.queries import PredicateBuilder, QueryOptimizer, QueryExecutor
from app.storage.vastdbmanager.analytics import TimeSeriesAnalytics, AggregationAnalytics, PerformanceMonitor, HybridAnalytics
from app.storage.vastdbmanager.endpoints import EndpointManager, LoadBalancer
from app.storage.vastdbmanager.core import VastDBManager


class TestTableCacheEntry:
    """Test TableCacheEntry dataclass"""
    
    def test_table_cache_entry_creation(self):
        """Test creating a TableCacheEntry"""
        schema = Schema([field('id', 'int64'), field('name', 'string')])
        entry = TableCacheEntry(
            schema=schema,
            total_rows=1000,
            last_updated=datetime.now()
        )
        
        assert entry.schema == schema
        assert entry.total_rows == 1000
        assert entry.cache_ttl == timedelta(minutes=30)
    
    def test_cache_expiration(self):
        """Test cache expiration logic"""
        # Create entry with very short TTL
        entry = TableCacheEntry(
            schema=Schema([field('id', 'int64')]),
            total_rows=100,
            last_updated=datetime.now() - timedelta(minutes=31),
            cache_ttl=timedelta(minutes=30)
        )
        
        assert entry.is_expired() is True
        
        # Create fresh entry
        fresh_entry = TableCacheEntry(
            schema=Schema([field('id', 'int64')]),
            total_rows=100,
            last_updated=datetime.now(),
            cache_ttl=timedelta(minutes=30)
        )
        
        assert fresh_entry.is_expired() is False


class TestCacheManager:
    """Test CacheManager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cache_manager = CacheManager()
        self.schema = Schema([field('id', 'int64'), field('name', 'string')])
    
    def test_update_table_cache(self):
        """Test updating table cache"""
        self.cache_manager.update_table_cache('test_table', self.schema, 500)
        
        # Verify cache was updated
        stats = self.cache_manager.get_table_stats('test_table')
        assert stats['total_rows'] == 500
        
        columns = self.cache_manager.get_table_columns('test_table')
        assert columns == self.schema
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        # Add entry to cache
        self.cache_manager.update_table_cache('test_table', self.schema, 500)
        assert 'test_table' in self.cache_manager.get_all_table_names()
        
        # Invalidate cache
        self.cache_manager.invalidate_table_cache('test_table')
        assert 'test_table' not in self.cache_manager.get_all_table_names()
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Add multiple entries
        self.cache_manager.update_table_cache('table1', self.schema, 100)
        self.cache_manager.update_table_cache('table2', self.schema, 200)
        
        stats = self.cache_manager.get_cache_stats()
        assert stats['total_entries'] == 2
        assert stats['active_entries'] == 2


class TestPredicateBuilder:
    """Test PredicateBuilder functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.builder = PredicateBuilder()
    
    def test_simple_predicate(self):
        """Test building simple equality predicates"""
        predicates = {'format': 'video', 'width': 1920}
        result = self.builder.build_vast_predicates(predicates)
        
        assert "format = 'video'" in result
        assert "width = 1920" in result
        assert " AND " in result
    
    def test_complex_predicate(self):
        """Test building complex predicates"""
        predicates = {
            'width': {'gte': 1920},
            'height': {'between': [1080, 2160]},
            'tags': {'contains': 'live'}
        }
        result = self.builder.build_vast_predicates(predicates)
        
        assert "width >= 1920" in result
        assert "height BETWEEN 1080 AND 2160" in result
        assert "tags LIKE '%live%'" in result
    
    def test_empty_predicates(self):
        """Test handling empty predicates"""
        result = self.builder.build_vast_predicates({})
        assert result == ""
        
        result = self.builder.build_vast_predicates(None)
        assert result == ""


class TestQueryOptimizer:
    """Test QueryOptimizer functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cache_manager = Mock()
        self.optimizer = QueryOptimizer(self.cache_manager)
        self.config = Mock()
        self.config.num_splits = None
        self.config.rows_per_split = 1_000_000
        self.config.num_sub_splits = None
        self.config.limit_rows_per_sub_split = 100_000
    
    def test_optimize_query_config_large_table(self):
        """Test optimization for large tables"""
        self.cache_manager.get_table_stats.return_value = {'total_rows': 15_000_000}
        
        result = self.optimizer.optimize_query_config(self.config, 'large_table')
        
        assert result.num_splits == 15  # 15M / 1M
        assert result.num_sub_splits == 8  # Large table gets more subsplits
    
    def test_optimize_query_config_small_table(self):
        """Test optimization for small tables"""
        self.cache_manager.get_table_stats.return_value = {'total_rows': 50_000}
        
        result = self.optimizer.optimize_query_config(self.config, 'small_table')
        
        assert result.num_splits == 1  # Small table gets 1 split
        assert result.num_sub_splits == 2  # Small table gets fewer subsplits
        assert result.limit_rows_per_sub_split == 10_000  # Reduced for small tables


class TestEndpointManager:
    """Test EndpointManager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.endpoints = ['http://endpoint1', 'http://endpoint2', 'http://endpoint3']
        self.manager = EndpointManager(self.endpoints)
    
    def test_healthy_endpoints(self):
        """Test getting healthy endpoints"""
        healthy = self.manager.get_healthy_endpoints()
        assert len(healthy) == 3  # All endpoints start as healthy
        
        # Mark one endpoint as unhealthy
        self.manager.mark_endpoint_error('http://endpoint1', 'Connection failed')
        self.manager.mark_endpoint_error('http://endpoint1', 'Timeout')
        self.manager.mark_endpoint_error('http://endpoint1', 'Error')
        
        healthy = self.manager.get_healthy_endpoints()
        assert len(healthy) == 2  # One endpoint marked as unhealthy
        assert 'http://endpoint1' not in healthy
    
    def test_endpoint_stats(self):
        """Test endpoint statistics"""
        stats = self.manager.get_endpoint_stats()
        
        assert stats['total_endpoints'] == 3
        assert stats['healthy_endpoints'] == 3
        assert stats['health_percentage'] == 100.0


class TestLoadBalancer:
    """Test LoadBalancer functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.endpoint_manager = Mock()
        self.endpoint_manager.get_healthy_endpoints.return_value = ['http://endpoint1', 'http://endpoint2']
        self.load_balancer = LoadBalancer(self.endpoint_manager)
    
    def test_endpoint_selection(self):
        """Test endpoint selection"""
        endpoint = self.load_balancer.get_endpoint('read')
        assert endpoint in ['http://endpoint1', 'http://endpoint2']
    
    def test_no_healthy_endpoints(self):
        """Test behavior when no healthy endpoints"""
        self.endpoint_manager.get_healthy_endpoints.return_value = []
        
        endpoint = self.load_balancer.get_endpoint('read')
        assert endpoint is None


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.monitor = PerformanceMonitor()
    
    def test_record_query(self):
        """Test recording query metrics"""
        self.monitor.record_query(
            query_type='select',
            table_name='test_table',
            execution_time=1.5,
            rows_returned=1000,
            splits_used=4,
            subsplits_used=8,
            success=True
        )
        
        summary = self.monitor.get_performance_summary()
        assert summary['total_queries'] == 1
        assert summary['successful_queries'] == 1
        assert summary['avg_execution_time'] == 1.5
    
    def test_slow_query_detection(self):
        """Test slow query detection"""
        # Record a slow query
        self.monitor.record_query(
            query_type='select',
            table_name='test_table',
            execution_time=6.0,  # Above 5 second threshold
            rows_returned=10000,
            splits_used=8,
            subsplits_used=16,
            success=True
        )
        
        slow_queries = self.monitor.get_slow_queries()
        assert len(slow_queries) == 1
        assert slow_queries[0]['execution_time'] == 6.0


class TestVastDBManager:
    """Test the main VastDBManager integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.endpoints = ['http://endpoint1', 'http://endpoint2']
        self.manager = VastDBManager(self.endpoints)
    
    def test_initialization(self):
        """Test VastDBManager initialization"""
        assert len(self.manager.endpoints) == 2
        assert self.manager.cache_manager is not None
        assert self.manager.predicate_builder is not None
        assert self.manager.query_optimizer is not None
        assert self.manager.query_executor is not None
        assert self.manager.endpoint_manager is not None
        assert self.manager.load_balancer is not None
        assert self.manager.performance_monitor is not None
    
    def test_cache_integration(self):
        """Test cache integration"""
        # Test that cache operations work through the manager
        stats = self.manager.get_cache_stats()
        assert isinstance(stats, dict)
        assert 'total_entries' in stats
    
    def test_endpoint_integration(self):
        """Test endpoint management integration"""
        stats = self.manager.get_endpoint_stats()
        assert isinstance(stats, dict)
        assert 'total_endpoints' in stats
        assert stats['total_endpoints'] == 2
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration"""
        summary = self.manager.get_performance_summary()
        assert isinstance(summary, dict)
        assert 'total_queries' in summary
    
    def teardown_method(self):
        """Clean up after tests"""
        if hasattr(self, 'manager'):
            self.manager.close()


class TestHybridAnalytics:
    """Test HybridAnalytics functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cache_manager = Mock()
        self.analytics = HybridAnalytics(self.cache_manager)
    
    def test_initialization(self):
        """Test HybridAnalytics initialization"""
        # Note: This test may fail if DuckDB is not available
        # In a real environment, you'd want to mock DuckDB
        assert hasattr(self.analytics, 'cache_manager')
    
    def teardown_method(self):
        """Clean up after tests"""
        if hasattr(self, 'analytics'):
            self.analytics.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

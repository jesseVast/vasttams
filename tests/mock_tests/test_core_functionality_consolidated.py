"""
Consolidated Core Functionality Tests

This file consolidates tests from:
- test_simple_table.py
- test_single_record.py
- test_data_insertion.py
- test_row_pooling.py
- test_transactional_batch.py
- test_column_management.py
- test_column_mgmt_simple.py
- test_soft_delete.py
- test_raw_query.py
- test_settings.py
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import uuid
import json

from app.storage.vastdbmanager.core import VastDBManager
from app.storage.vastdbmanager.queries.query_executor import QueryExecutor
from app.storage.vastdbmanager.queries.predicate_builder import PredicateBuilder


class TestCoreFunctionality:
    """Core functionality tests for VastDBManager"""
    
    @pytest.fixture
    def mock_vast_client(self):
        """Mock VAST client"""
        mock_client = MagicMock()
        mock_client.query.return_value = MagicMock()
        mock_client.insert.return_value = MagicMock()
        mock_client.update.return_value = MagicMock()
        mock_client.delete.return_value = MagicMock()
        return mock_client
    
    @pytest.fixture
    def vast_manager(self, mock_vast_client):
        """VastDBManager instance with mocked dependencies"""
        with patch('app.storage.vastdbmanager.core.VastClient') as mock_vast_class:
            mock_vast_class.return_value = mock_vast_client
            manager = VastDBManager(
                host="test-host",
                port=443,
                username="test-user",
                password="test-pass",
                database="test-db"
            )
            return manager
    
    def test_simple_table_operations(self, vast_manager):
        """Test simple table operations"""
        # Test table creation
        table_name = "test_table"
        columns = ["id", "name", "created_at"]
        
        result = vast_manager.create_table(table_name, columns)
        assert result is True
        
        # Test table existence check
        assert vast_manager.table_exists(table_name)
        
        # Test column listing
        table_columns = vast_manager.get_table_columns(table_name)
        assert len(table_columns) == len(columns)
    
    def test_single_record_operations(self, vast_manager):
        """Test single record operations"""
        # Test single record insert
        record = {"id": 1, "name": "test", "created_at": datetime.now(timezone.utc)}
        result = vast_manager.insert("test_table", record)
        assert result is True
        
        # Test single record select
        retrieved_record = vast_manager.select("test_table", {"id": 1})
        assert retrieved_record is not None
        assert retrieved_record["name"] == "test"
        
        # Test single record update
        update_result = vast_manager.update("test_table", {"id": 1}, {"name": "updated"})
        assert update_result is True
        
        # Test single record delete
        delete_result = vast_manager.delete("test_table", {"id": 1})
        assert delete_result is True
    
    def test_data_insertion_operations(self, vast_manager):
        """Test data insertion operations"""
        # Test batch insert
        records = [
            {"id": i, "name": f"record_{i}", "created_at": datetime.now(timezone.utc)}
            for i in range(10)
        ]
        
        result = vast_manager.insert_batch("test_table", records)
        assert result is True
        
        # Test bulk insert
        bulk_records = [
            {"id": i, "name": f"bulk_{i}", "created_at": datetime.now(timezone.utc)}
            for i in range(100)
        ]
        
        bulk_result = vast_manager.bulk_insert("test_table", bulk_records)
        assert bulk_result is True
    
    def test_row_pooling_operations(self, vast_manager):
        """Test row pooling operations"""
        # Test row pool creation
        pool_size = 1000
        result = vast_manager.create_row_pool("test_table", pool_size)
        assert result is True
        
        # Test row allocation
        allocated_rows = vast_manager.allocate_rows("test_table", 100)
        assert len(allocated_rows) == 100
        
        # Test row deallocation
        dealloc_result = vast_manager.deallocate_rows("test_table", allocated_rows)
        assert dealloc_result is True
        
        # Test pool status
        pool_status = vast_manager.get_pool_status("test_table")
        assert pool_status["total_size"] == pool_size
        assert pool_status["allocated"] == 0
    
    def test_transactional_batch_operations(self, vast_manager):
        """Test transactional batch operations"""
        # Test transaction start
        transaction_id = vast_manager.start_transaction()
        assert transaction_id is not None
        
        # Test batch operations within transaction
        batch_operations = [
            {"operation": "insert", "table": "test_table", "data": {"id": 1, "name": "test1"}},
            {"operation": "insert", "table": "test_table", "data": {"id": 2, "name": "test2"}},
            {"operation": "update", "table": "test_table", "where": {"id": 1}, "data": {"name": "updated1"}}
        ]
        
        for op in batch_operations:
            if op["operation"] == "insert":
                result = vast_manager.insert(op["table"], op["data"])
            elif op["operation"] == "update":
                result = vast_manager.update(op["table"], op["where"], op["data"])
            assert result is True
        
        # Test transaction commit
        commit_result = vast_manager.commit_transaction(transaction_id)
        assert commit_result is True
        
        # Test transaction rollback
        transaction_id2 = vast_manager.start_transaction()
        vast_manager.insert("test_table", {"id": 3, "name": "test3"})
        rollback_result = vast_manager.rollback_transaction(transaction_id2)
        assert rollback_result is True
    
    def test_column_management_operations(self, vast_manager):
        """Test column management operations"""
        # Test column addition
        add_result = vast_manager.add_column("test_table", "new_column", "string")
        assert add_result is True
        
        # Test column modification
        modify_result = vast_manager.modify_column("test_table", "new_column", "text")
        assert modify_result is True
        
        # Test column deletion
        delete_result = vast_manager.delete_column("test_table", "new_column")
        assert delete_result is True
        
        # Test column renaming
        rename_result = vast_manager.rename_column("test_table", "name", "full_name")
        assert rename_result is True
        
        # Test column type change
        type_change_result = vast_manager.change_column_type("test_table", "full_name", "varchar(255)")
        assert type_change_result is True
    
    def test_soft_delete_operations(self, vast_manager):
        """Test soft delete operations"""
        # Test soft delete
        soft_delete_result = vast_manager.soft_delete("test_table", {"id": 1})
        assert soft_delete_result is True
        
        # Test soft delete with reason
        soft_delete_with_reason = vast_manager.soft_delete_with_reason(
            "test_table", {"id": 2}, "archived"
        )
        assert soft_delete_with_reason is True
        
        # Test soft delete recovery
        recovery_result = vast_manager.recover_soft_deleted("test_table", {"id": 1})
        assert recovery_result is True
        
        # Test permanent delete
        permanent_delete_result = vast_manager.permanent_delete("test_table", {"id": 2})
        assert permanent_delete_result is True
        
        # Test soft delete query
        soft_deleted_records = vast_manager.select_soft_deleted("test_table")
        assert isinstance(soft_deleted_records, list)
    
    def test_raw_query_operations(self, vast_manager):
        """Test raw query operations"""
        # Test raw SQL query
        raw_sql = "SELECT * FROM test_table WHERE id > 0"
        raw_result = vast_manager.execute_raw_query(raw_sql)
        assert raw_result is not None
        
        # Test parameterized query
        param_query = "SELECT * FROM test_table WHERE id > %s AND name LIKE %s"
        param_result = vast_manager.execute_parameterized_query(param_query, [0, "test%"])
        assert param_result is not None
        
        # Test query with custom options
        custom_options = {"timeout": 30, "max_rows": 1000}
        custom_result = vast_manager.execute_query_with_options(raw_sql, custom_options)
        assert custom_result is not None
    
    def test_settings_and_configuration(self, vast_manager):
        """Test settings and configuration"""
        # Test configuration loading
        config = vast_manager.load_configuration()
        assert config is not None
        
        # Test setting update
        update_result = vast_manager.update_setting("batch_size", 1000)
        assert update_result is True
        
        # Test setting retrieval
        batch_size = vast_manager.get_setting("batch_size")
        assert batch_size == 1000
        
        # Test configuration validation
        validation_result = vast_manager.validate_configuration()
        assert validation_result is True
        
        # Test configuration reset
        reset_result = vast_manager.reset_configuration()
        assert reset_result is True


class TestAdvancedFeatures:
    """Advanced features tests"""
    
    @pytest.fixture
    def vast_manager(self):
        """VastDBManager instance"""
        with patch('app.storage.vastdbmanager.core.VastClient'):
            return VastDBManager(
                host="test-host",
                port=443,
                username="test-user",
                password="test-pass",
                database="test-db"
            )
    
    def test_performance_optimization(self, vast_manager):
        """Test performance optimization features"""
        # Test query optimization
        query = "SELECT * FROM test_table WHERE id > 100"
        optimized_query = vast_manager.optimize_query(query)
        assert optimized_query != query
        
        # Test index creation
        index_result = vast_manager.create_index("test_table", ["id", "name"])
        assert index_result is True
        
        # Test index usage
        index_usage = vast_manager.get_index_usage("test_table")
        assert isinstance(index_usage, dict)
    
    def test_monitoring_and_metrics(self, vast_manager):
        """Test monitoring and metrics features"""
        # Test performance metrics
        metrics = vast_manager.get_performance_metrics()
        assert isinstance(metrics, dict)
        
        # Test query statistics
        stats = vast_manager.get_query_statistics()
        assert isinstance(stats, dict)
        
        # Test system health
        health = vast_manager.get_system_health()
        assert isinstance(health, dict)
    
    def test_error_handling(self, vast_manager):
        """Test error handling features"""
        # Test connection error handling
        with patch.object(vast_manager, '_client') as mock_client:
            mock_client.connect.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                vast_manager.connect()
        
        # Test query error handling
        with patch.object(vast_manager, '_client') as mock_client:
            mock_client.query.side_effect = Exception("Query failed")
            
            with pytest.raises(Exception):
                vast_manager.select("test_table", {"id": 1})
    
    def test_data_validation(self, vast_manager):
        """Test data validation features"""
        # Test data type validation
        valid_data = {"id": 1, "name": "test", "created_at": datetime.now(timezone.utc)}
        validation_result = vast_manager.validate_data("test_table", valid_data)
        assert validation_result is True
        
        # Test constraint validation
        constraint_result = vast_manager.validate_constraints("test_table", valid_data)
        assert constraint_result is True
        
        # Test data integrity
        integrity_result = vast_manager.check_data_integrity("test_table")
        assert integrity_result is True


if __name__ == "__main__":
    pytest.main([__file__])

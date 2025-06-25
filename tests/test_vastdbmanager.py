"""
Test suite for VastDBManager

This module provides comprehensive tests for the VastDBManager class,
demonstrating proper usage patterns and verifying functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pyarrow as pa
from pyarrow import Schema, Table, RecordBatch
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestVastDBManager(unittest.TestCase):
    """Test cases for VastDBManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.mock_transaction = Mock()
        self.mock_bucket = Mock()
        self.mock_schema = Mock()
        self.mock_table = Mock()
        
        # Configure mock chain
        self.mock_session.transaction.return_value.__enter__.return_value = self.mock_transaction
        self.mock_transaction.bucket.return_value = self.mock_bucket
        self.mock_bucket.schema.return_value = self.mock_schema
        self.mock_schema.table.return_value = self.mock_table
        
        # Test configuration
        self.config = {
            'endpoint': 'http://localhost:8080',
            'access_key': 'test_access_key',
            'secret_key': 'test_secret_key',
            'bucket': 'test_bucket',
            'schema': 'test_schema',
            'timeout': 30
        }
        
        # Sample table schema
        self.sample_schema = Schema([
            pa.field('id', pa.int64()),
            pa.field('name', pa.string()),
            pa.field('value', pa.float64())
        ])
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_initialization(self, mock_connect):
        """Test VastDBManager initialization."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = None  # Schema doesn't exist initially
        
        from app.vastdbmanager import VastDBManager
        
        manager = VastDBManager(**self.config)
        
        # Verify connection was established
        mock_connect.assert_called_once_with(
            endpoint=self.config['endpoint'],
            access=self.config['access_key'],
            secret=self.config['secret_key'],
            timeout=30
        )
        
        # Verify schema setup was called
        self.mock_bucket.create_schema.assert_called_once_with(self.config['schema'])
        
        # Verify manager is ready
        self.assertTrue(manager.is_ready)
        self.assertEqual(manager.endpoint, self.config['endpoint'])
        self.assertEqual(manager.bucket, self.config['bucket'])
        self.assertEqual(manager.schema, self.config['schema'])
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_create_table(self, mock_connect):
        """Test table creation."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = self.mock_schema
        self.mock_schema.table.return_value = None  # Table doesn't exist
        
        from app.vastdbmanager import VastDBManager
        
        manager = VastDBManager(**self.config)
        manager.create_table('test_table', self.sample_schema)
        
        # Verify table creation
        self.mock_schema.create_table.assert_called_once_with('test_table', self.sample_schema)
        self.assertIn('test_table', manager.table_schemas)
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_list_tables(self, mock_connect):
        """Test listing tables."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = self.mock_schema
        
        # Mock table objects
        mock_table1 = Mock()
        mock_table1.name = 'table1'
        mock_table2 = Mock()
        mock_table2.name = 'table2'
        self.mock_schema.tables.return_value = [mock_table1, mock_table2]
        
        from app.vastdbmanager import VastDBManager
        
        manager = VastDBManager(**self.config)
        tables = manager.list_tables()
        
        self.assertEqual(tables, ['table1', 'table2'])
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_select_operation(self, mock_connect):
        """Test select operation."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = self.mock_schema
        
        # Mock select result
        mock_select_result = Mock()
        mock_table_data = Table.from_pydict({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'value': [10.5, 20.3, 30.7]
        })
        mock_select_result.read_all.return_value = mock_table_data
        self.mock_table.select.return_value = mock_select_result
        
        from app.vastdbmanager import VastDBManager
        
        manager = VastDBManager(**self.config)
        manager.table_schemas['test_table'] = self.sample_schema
        
        # Test select with row output
        result = manager.select('test_table', output_by_row=True)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['name'], 'Alice')
        
        # Test select with column output
        result = manager.select('test_table', output_by_row=False)
        self.assertEqual(len(result['id']), 3)
        self.assertEqual(result['name'][0], 'Alice')
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_insert_operations(self, mock_connect):
        """Test insert operations."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = self.mock_schema
        
        from app.vastdbmanager import VastDBManager
        
        manager = VastDBManager(**self.config)
        manager.table_schemas['test_table'] = self.sample_schema
        
        # Test pydict insert
        pydict_data = {
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'value': [10.5, 20.3, 30.7]
        }
        result = manager.insert_pydict('test_table', pydict_data)
        self.assertEqual(result, 3)
        self.mock_table.insert.assert_called_once()
        
        # Test pylist insert
        pylist_data = [
            {'id': 1, 'name': 'Alice', 'value': 10.5},
            {'id': 2, 'name': 'Bob', 'value': 20.3}
        ]
        result = manager.insert_pylist('test_table', pylist_data)
        self.assertEqual(result, 2)
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_delete_operation(self, mock_connect):
        """Test delete operation."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = self.mock_schema
        
        # Mock select result for row IDs
        mock_select_result = Mock()
        mock_row_data = Table.from_pydict({
            'id': [1, 2],
            '$row_id': [100, 101]
        })
        mock_select_result.read_all.return_value = mock_row_data
        self.mock_table.select.return_value = mock_select_result
        
        from app.vastdbmanager import VastDBManager
        
        manager = VastDBManager(**self.config)
        manager.table_schemas['test_table'] = self.sample_schema
        
        result = manager.delete('test_table', 'id > 0')
        self.assertEqual(result, 2)
        self.mock_table.delete.assert_called_once()
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_update_operation(self, mock_connect):
        """Test update operation."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = self.mock_schema
        
        # Mock select result for row IDs
        mock_select_result = Mock()
        mock_row_data = Table.from_pydict({
            'id': [1],
            '$row_id': [100]
        })
        mock_select_result.read_all.return_value = mock_row_data
        self.mock_table.select.return_value = mock_select_result
        
        from app.vastdbmanager import VastDBManager
        
        manager = VastDBManager(**self.config)
        manager.table_schemas['test_table'] = self.sample_schema
        
        update_data = {'name': 'Updated Name', 'value': 99.9}
        result = manager.update('test_table', update_data, 'id = 1')
        self.assertEqual(result, 1)
        self.mock_table.update.assert_called_once()
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_context_manager(self, mock_connect):
        """Test context manager functionality."""
        mock_connect.return_value = self.mock_session
        self.mock_bucket.schema.return_value = self.mock_schema
        
        from app.vastdbmanager import VastDBManager
        
        with VastDBManager(**self.config) as manager:
            self.assertTrue(manager.is_ready)
            self.assertIsNotNone(manager.session)
        
        # Verify session was closed
        self.mock_session.close.assert_called_once()
    
    @patch('app.vastdbmanager.vastdb.connect')
    def test_error_handling(self, mock_connect):
        """Test error handling."""
        mock_connect.side_effect = Exception("Connection failed")
        
        from app.vastdbmanager import VastDBManager
        
        with self.assertRaises(Exception):
            VastDBManager(**self.config)
    
    def test_get_smallest_column(self):
        """Test smallest column detection."""
        from app.vastdbmanager import VastDBManager
        
        # Create manager without connection for this test
        manager = VastDBManager.__new__(VastDBManager)
        manager.table_schemas = {
            'test_table': Schema([
                pa.field('id', pa.int64()),      # 8 bytes
                pa.field('name', pa.string()),   # variable width
                pa.field('value', pa.float64()), # 8 bytes
                pa.field('flag', pa.bool_())     # 1 byte
            ])
        }
        
        smallest = manager._get_smallest_column('test_table')
        self.assertEqual(smallest, 'flag')  # bool should be smallest
    
    def test_type_validation(self):
        """Test type validation in insert method."""
        from app.vastdbmanager import VastDBManager
        
        # Create manager without connection for this test
        manager = VastDBManager.__new__(VastDBManager)
        
        # Test invalid type for pydict
        with self.assertRaises(TypeError):
            manager.insert('test_table', [{'id': 1}], as_pydict=True)
        
        # Test invalid type for pylist
        with self.assertRaises(TypeError):
            manager.insert('test_table', {'id': [1]}, as_pydict=False)


if __name__ == '__main__':
    unittest.main() 
"""Simple test to isolate VastDBManager data insertion issues"""

import pytest
import time
import logging
from datetime import datetime, timedelta
import random

# Import the VastDBManager
from app.storage.vastdbmanager import VastDBManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVastDBManagerSimple:
    """Simple tests to isolate VastDBManager issues"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Initialize with multiple endpoints
        self.endpoints = [
            "http://172.200.204.90",
            "http://172.200.204.91", 
            "http://172.200.204.93",
            "http://172.200.204.92"
        ]
        
        self.manager = VastDBManager(self.endpoints)
        self.test_table_name = f"simple_test_{int(time.time())}"
        
        logger.info(f"Setting up simple test with table: {self.test_table_name}")
    
    def teardown_method(self):
        """Clean up after tests"""
        try:
            if hasattr(self, 'manager'):
                self.manager.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def test_simple_table_creation(self):
        """Test simple table creation with basic schema"""
        try:
            import pyarrow as pa
            
            # Create a very simple schema with basic types
            schema = pa.schema([
                pa.field('id', 'string'),
                pa.field('name', 'string'),
                pa.field('value', 'int64')
            ])
            
            # Connect and create table
            self.manager.connect()
            table = self.manager.create_table(self.test_table_name, schema)
            
            logger.info(f"Successfully created simple table: {self.test_table_name}")
            assert table is not None
            
        except Exception as e:
            logger.error(f"Failed to create simple table: {e}")
            raise
    
    def test_simple_data_insertion(self):
        """Test simple data insertion with basic types"""
        try:
            import pyarrow as pa
            
            # Create a very simple schema
            schema = pa.schema([
                pa.field('id', 'string'),
                pa.field('name', 'string'),
                pa.field('value', 'int64')
            ])
            
            # Connect and create table
            self.manager.connect()
            self.manager.create_table(self.test_table_name, schema)
            
            # Generate simple test data
            test_data = {
                'id': ['row1', 'row2', 'row3'],
                'name': ['test1', 'test2', 'test3'],
                'value': [100, 200, 300]
            }
            
            # Insert data
            self.manager.insert_pydict(self.test_table_name, test_data)
            
            logger.info(f"Successfully inserted simple data into table: {self.test_table_name}")
            
        except Exception as e:
            logger.error(f"Failed to insert simple data: {e}")
            raise
    
    def test_media_schema_creation(self):
        """Test media schema creation without data insertion"""
        try:
            import pyarrow as pa
            
            # Create media schema similar to stress test but simplified
            schema = pa.schema([
                pa.field('id', 'string'),
                pa.field('timestamp', 'string'),
                pa.field('format', 'string'),
                pa.field('duration', 'float64'),
                pa.field('bitrate', 'int64'),
                pa.field('file_size', 'int64')
            ])
            
            # Connect and create table
            self.manager.connect()
            table = self.manager.create_table(self.test_table_name, schema)
            
            logger.info(f"Successfully created media schema table: {self.test_table_name}")
            assert table is not None
            
        except Exception as e:
            logger.error(f"Failed to create media schema table: {e}")
            raise


if __name__ == "__main__":
    # Run simple tests
    pytest.main([__file__, "-v", "-s"])

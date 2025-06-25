"""
Example usage of VastDBManager

This module demonstrates how to use the improved VastDBManager class
for common database operations.
"""

import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Demonstrate basic VastDBManager usage."""
    
    # Configuration
    config = {
        'endpoint': 'http://localhost:8080',
        'access_key': 'your_access_key',
        'secret_key': 'your_secret_key',
        'bucket': 'your_bucket',
        'schema': 'your_schema',
        'timeout': 30
    }
    
    try:
        # Import the manager (only if vastdb is available)
        from app.vastdbmanager import VastDBManager
        
        # Create manager instance
        with VastDBManager(**config) as manager:
            logger.info("VAST DB Manager initialized successfully")
            
            # List existing tables
            tables = manager.list_tables()
            logger.info(f"Existing tables: {tables}")
            
            # Example operations (commented out as they require actual data)
            # create_example_table(manager)
            # insert_example_data(manager)
            # query_example_data(manager)
            
    except ImportError:
        logger.warning("vastdb package not available - this is a demonstration only")
    except Exception as e:
        logger.error(f"Error using VastDBManager: {e}")


def create_example_table(manager):
    """Example of creating a table."""
    try:
        import pyarrow as pa
        from pyarrow import Schema
        
        # Define table schema
        schema = Schema([
            pa.field('id', pa.int64()),
            pa.field('name', pa.string()),
            pa.field('value', pa.float64()),
            pa.field('timestamp', pa.timestamp('us'))
        ])
        
        # Create table
        manager.create_table('example_table', schema)
        logger.info("Example table created successfully")
        
    except ImportError:
        logger.warning("pyarrow not available - skipping table creation example")


def insert_example_data(manager):
    """Example of inserting data."""
    try:
        # Column-oriented data (pydict format)
        pydict_data = {
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
            'value': [10.5, 20.3, 30.7, 40.1, 50.9],
            'timestamp': [1234567890000, 1234567891000, 1234567892000, 1234567893000, 1234567894000]
        }
        
        rows_inserted = manager.insert_pydict('example_table', pydict_data)
        logger.info(f"Inserted {rows_inserted} rows using pydict format")
        
        # Row-oriented data (pylist format)
        pylist_data = [
            {'id': 6, 'name': 'Frank', 'value': 60.2, 'timestamp': 1234567895000},
            {'id': 7, 'name': 'Grace', 'value': 70.8, 'timestamp': 1234567896000}
        ]
        
        rows_inserted = manager.insert_pylist('example_table', pylist_data)
        logger.info(f"Inserted {rows_inserted} rows using pylist format")
        
    except Exception as e:
        logger.error(f"Error inserting data: {e}")


def query_example_data(manager):
    """Example of querying data."""
    try:
        # Select all data
        all_data = manager.select('example_table')
        logger.info(f"Retrieved {len(all_data)} rows")
        
        # Select specific columns
        specific_columns = manager.select('example_table', column_names=['id', 'name'])
        logger.info(f"Retrieved {len(specific_columns)} rows with specific columns")
        
        # Select with predicate
        filtered_data = manager.select('example_table', predicate='value > 30.0')
        logger.info(f"Retrieved {len(filtered_data)} rows with value > 30.0")
        
        # Get column-oriented output
        column_data = manager.select('example_table', output_by_row=False)
        logger.info(f"Column data: {list(column_data.keys())}")
        
    except Exception as e:
        logger.error(f"Error querying data: {e}")


def update_example_data(manager):
    """Example of updating data."""
    try:
        # Update specific rows
        update_data = {'value': 99.9, 'name': 'Updated Name'}
        rows_updated = manager.update('example_table', update_data, 'id = 1')
        logger.info(f"Updated {rows_updated} rows")
        
    except Exception as e:
        logger.error(f"Error updating data: {e}")


def delete_example_data(manager):
    """Example of deleting data."""
    try:
        # Delete specific rows
        rows_deleted = manager.delete('example_table', 'value < 20.0')
        logger.info(f"Deleted {rows_deleted} rows")
        
    except Exception as e:
        logger.error(f"Error deleting data: {e}")


def get_table_info(manager):
    """Example of getting table information."""
    try:
        # Get table statistics
        stats = manager.get_table_stats('example_table')
        logger.info(f"Table stats: {stats}")
        
        # Get table columns
        columns = manager.get_table_columns('example_table')
        logger.info(f"Table columns: {columns}")
        
    except Exception as e:
        logger.error(f"Error getting table info: {e}")


if __name__ == '__main__':
    example_basic_usage() 
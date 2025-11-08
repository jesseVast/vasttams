"""
Storage Backend PyArrow Schemas

This module defines PyArrow schemas for storage backend tables.
"""

import pyarrow as pa
from typing import List


def get_storage_backends_schema() -> pa.Schema:
    """Get PyArrow schema for storage_backends table"""
    return pa.schema([
        pa.field('id', pa.string()),
        pa.field('label', pa.string()),
        pa.field('store_type', pa.string()),
        pa.field('provider', pa.string()),
        pa.field('store_product', pa.string()),
        pa.field('region', pa.string()),
        pa.field('availability_zone', pa.string()),
        pa.field('endpoint_url', pa.string()),
        pa.field('access_key', pa.string()),
        pa.field('secret_key', pa.string()),
        pa.field('bucket_name', pa.string()),
        pa.field('root_path', pa.string()),
        pa.field('use_ssl', pa.bool_()),
        pa.field('default_storage', pa.bool_()),
        pa.field('created_at', pa.timestamp('ns', tz='UTC')),
        pa.field('updated_at', pa.timestamp('ns', tz='UTC')),
    ])


def get_storage_backends_projections() -> List[List[str]]:
    """Get projections for storage_backends table"""
    return [
        ['id'],  # Base projection
        ['id', 'label', 'store_type', 'provider', 'endpoint_url'],  # Common query projection
        ['id', 'default_storage'],  # Default storage lookup
    ]


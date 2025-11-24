"""
VAST table schemas for TAMS.

This module defines PyArrow schemas for VAST-specific tables that are not part of the TAMS specification.
Vector operations are managed separately from TAMS objects.
"""

import pyarrow as pa
from typing import List


def _create_fixed_size_list(value_type, size: int):
    """Create a fixed-size list type, compatible with PyArrow 16.1.0+ and 16.2.0+
    
    Uses the same syntax as vastdbmanager/vaststore:
    pa.list_(pa.field("item", type=pa.float32(), nullable=False), dimension)
    """
    # Create field for list item (required by VAST)
    item_field = pa.field(name="item", type=value_type, nullable=False)
    # Try fixed_size_list first (PyArrow 16.2.0+)
    if hasattr(pa, 'fixed_size_list'):
        return pa.fixed_size_list(item_field, size)
    # Fallback to list_ with field and size parameter (PyArrow 16.1.0+)
    return pa.list_(item_field, size)


def get_vectors_schema(model_dimension: int = 1536) -> pa.Schema:
    """Get vectors table schema - Universal table for vector embeddings
    
    This table supports vectors for any entity type (objects, flows, sources, segments).
    With vastdbmanager 1.1.10+, vectors are stored in a separate table to allow
    automatic query routing. Vector operations use ADBC (via vector_client),
    while regular queries use Trino.
    
    Note: Vectors are not part of the TAMS specification and are managed by the vast module.
    
    Args:
        model_dimension: Dimension of the embedding vector (default: 1536)
    """
    return pa.schema([
        pa.field("entity_id", pa.string(), nullable=True),  # ID of the entity (object, flow, source, segment)
        pa.field("entity_type", pa.string(), nullable=True),  # Type of entity: "object", "flow", "source", "segment"
        pa.field("vector", _create_fixed_size_list(pa.float32(), model_dimension), nullable=True),  # Vector embedding
        pa.field("summary", pa.string(), nullable=True),  # Text summary
        pa.field("embedding_date", pa.timestamp("ns"), nullable=True),  # Date of embedding
        pa.field("embedding_model", pa.string(), nullable=True),  # Embedding model name
    ])


def get_vectors_projections() -> List[List[str]]:
    """Get vectors table projection definitions"""
    return [
        ["entity_id"],
        ["entity_type"],
        ["entity_id", "entity_type"]
    ]


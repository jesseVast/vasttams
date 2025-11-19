"""
VAST Vector Models

This module contains models for vector embedding operations.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ObjectVectorPut(BaseModel):
    """Request model for updating/inserting object vector"""
    vector: List[float] = Field(..., description="768-dimensional vector embedding")
    summary: Optional[str] = Field(None, description="Text summary of the object")
    embedding_model: Optional[str] = Field(default="nomic-embed-1.5", description="Embedding model name")
    
    @field_validator('vector')
    @classmethod
    def validate_vector_length(cls, v: List[float]) -> List[float]:
        if len(v) != 768:
            raise ValueError(f"Vector must be exactly 768 dimensions, got {len(v)}")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Vector must contain only numeric values")
        return v


class VectorSearchRequest(BaseModel):
    """Request model for vector similarity search"""
    vector: List[float] = Field(..., description="768-dimensional query vector")
    num_matches: Optional[int] = Field(None, description="Number of matches to return (defaults to config)")
    distance_metric: Optional[str] = Field(None, description="Distance metric (cosine, euclidean, dot_product) (defaults to config)")
    distance_numerical_value: Optional[float] = Field(None, description="Distance numerical value/threshold (defaults to config, 0.75 for cosine)")
    
    @field_validator('vector')
    @classmethod
    def validate_vector_length(cls, v: List[float]) -> List[float]:
        if len(v) != 768:
            raise ValueError(f"Vector must be exactly 768 dimensions, got {len(v)}")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Vector must contain only numeric values")
        return v


class VectorSearchMatch(BaseModel):
    """Individual match result from vector search"""
    object_id: str = Field(..., description="Matching object ID")
    segment_id: Optional[str] = Field(None, description="Segment ID associated with this object")
    flow_id: Optional[str] = Field(None, description="Flow ID associated with this segment")
    source_id: Optional[str] = Field(None, description="Source ID associated with this flow")
    distance: Optional[float] = Field(None, description="Distance score for this match")


class VectorSearchResult(BaseModel):
    """Response model for vector search results"""
    matches: List[VectorSearchMatch] = Field(..., description="List of matches with object-segment-flow-source relationships")


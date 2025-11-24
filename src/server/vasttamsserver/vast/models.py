"""
VAST Vector Models

This module contains models for vector embedding operations.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ObjectVectorPut(BaseModel):
    """Request model for updating/inserting object vector"""
    vector: List[float] = Field(..., description="Vector embedding (dimension determined by configured model)")
    summary: Optional[str] = Field(None, description="Text summary of the object")
    embedding_model: Optional[str] = Field(default=None, description="Embedding model name (defaults to configured model)")
    
    @field_validator('vector')
    @classmethod
    def validate_vector(cls, v: List[float]) -> List[float]:
        """Validate vector contains only numeric values"""
        if not v:
            raise ValueError("Vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Vector must contain only numeric values")
        return v
    
    @model_validator(mode='after')
    def validate_vector_dimension(self) -> 'ObjectVectorPut':
        """Validate vector dimension matches configured embedding model dimension"""
        from ..core.config import get_settings
        settings = get_settings()
        expected_dim = settings.embedding_model_dimension
        
        if len(self.vector) != expected_dim:
            raise ValueError(
                f"Vector must be exactly {expected_dim} dimensions (configured for model '{settings.embedding_model_name}'), "
                f"got {len(self.vector)} dimensions"
            )
        return self


class VectorSearchRequest(BaseModel):
    """Request model for vector similarity search"""
    vector: List[float] = Field(..., description="Query vector (dimension determined by configured model)")
    num_matches: Optional[int] = Field(None, description="Number of matches to return (defaults to config)")
    distance_metric: Optional[str] = Field(None, description="Distance metric (cosine, euclidean, dot_product) (defaults to config)")
    distance_numerical_value: Optional[float] = Field(None, description="Distance numerical value/threshold (defaults to config)")
    entity_types: Optional[List[str]] = Field(None, description="Optional list of entity types to filter by (object, flow, source, segment)")
    
    @field_validator('vector')
    @classmethod
    def validate_vector(cls, v: List[float]) -> List[float]:
        """Validate vector contains only numeric values (dimension validation done in service/router)"""
        if not v:
            raise ValueError("Vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Vector must contain only numeric values")
        return v


class VectorSearchMatch(BaseModel):
    """Individual match result from vector search"""
    entity_id: str = Field(..., description="Matching entity ID")
    entity_type: str = Field(..., description="Type of entity (object, flow, source, segment)")
    object_id: Optional[str] = Field(None, description="Object ID (if entity is object or segment)")
    segment_id: Optional[str] = Field(None, description="Segment ID (if entity is segment)")
    flow_id: Optional[str] = Field(None, description="Flow ID (if entity is flow or segment)")
    source_id: Optional[str] = Field(None, description="Source ID (if entity is source or flow)")
    distance: Optional[float] = Field(None, description="Distance score for this match")


class VectorSearchResult(BaseModel):
    """Response model for vector search results"""
    matches: List[VectorSearchMatch] = Field(..., description="List of matches with object-segment-flow-source relationships")


class TextIngestionRequest(BaseModel):
    """Request model for ingesting text and converting to vector"""
    text: str = Field(..., description="Text to embed and store")
    entity_id: str = Field(..., description="Entity ID to associate with the vector (object, flow, source, or segment ID)")
    entity_type: str = Field(..., description="Type of entity (object, flow, source, segment)")
    embedding_model: Optional[str] = Field(None, description="Embedding model name (defaults to configured model)")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty"""
        if not v or not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()
    
    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type is one of the supported types"""
        valid_types = ["object", "flow", "source", "segment"]
        if v not in valid_types:
            raise ValueError(f"entity_type must be one of: {', '.join(valid_types)}")
        return v


class TextIngestionResponse(BaseModel):
    """Response model for text ingestion"""
    entity_id: str = Field(..., description="Entity ID associated with the vector")
    entity_type: str = Field(..., description="Type of entity")
    embedding_model: str = Field(..., description="Embedding model used")
    embedding_date: datetime = Field(..., description="Date when embedding was created")
    dimension: int = Field(..., description="Vector dimension")


class TextSearchRequest(BaseModel):
    """Request model for text-based vector search"""
    text: str = Field(..., description="Search query text")
    entity_types: Optional[List[str]] = Field(None, description="Optional list of entity types to filter by (object, flow, source, segment)")
    limit: Optional[int] = Field(None, description="Number of results to return (defaults to config)")
    distance_threshold: Optional[float] = Field(None, description="Distance threshold (defaults to config)")
    distance_metric: Optional[str] = Field(None, description="Distance metric (cosine, euclidean, dot_product) (defaults to config)")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty"""
        if not v or not v.strip():
            raise ValueError("Search text cannot be empty")
        return v.strip()


class TextSearchResult(BaseModel):
    """Response model for text search results"""
    query_text: str = Field(..., description="Original search query text")
    embedding_model: str = Field(..., description="Embedding model used")
    distance_algorithm: str = Field(..., description="Distance algorithm used")
    distance_threshold: float = Field(..., description="Distance threshold used")
    results: List[VectorSearchMatch] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results found")


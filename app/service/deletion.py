"""
TAMS Deletion Request Models

This module contains models related to deletion requests in the TAMS API.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, RootModel, field_validator, field_serializer, ConfigDict

from .core import TimeRange, validate_tams_uuid


class DeletionRequest(BaseModel):
    """Flow deletion request - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., description="Deletion Request ID")
    flow_id: str = Field(..., description="ID of the flow to which the deletion request relates")
    timerange_to_delete: TimeRange = Field(..., description="The timerange of FlowSegments to be deleted in this request")
    delete_flow: bool = Field(..., description="Whether the Flow should be deleted once the timerange has been")
    status: str = Field(..., description="Status of the delete request")
    timerange_remaining: Optional[TimeRange] = Field(None, description="The timerange of FlowSegments not yet deleted by this request")
    created: Optional[datetime] = Field(None, description="Date/Time when this deletion request was created")
    created_by: Optional[str] = Field(None, description="Entity that created the deletion request")
    updated: Optional[datetime] = Field(None, description="Date/Time when this deletion request was updated")
    expiry: Optional[datetime] = Field(None, description="Date/Time when this deletion request will be deleted")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information for error status")
    
    @field_validator('id', 'flow_id')
    @classmethod
    def validate_uuids(cls, v: str) -> str:
        return validate_tams_uuid(v)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = ['created', 'started', 'done', 'error']
        if v not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {valid_statuses}')
        return v
    
    @field_serializer('created', 'updated', 'expiry')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class DeletionRequestsList(RootModel[list[DeletionRequest]]):
    """List of deletion requests"""
    pass

"""
TAMS Response Models

This module contains response wrapper models for the TAMS API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .service import Service
from .sources import Source
from .flows import Flow
from .webhooks import Webhook
from .deletion import DeletionRequestsList


class PagingInfo(BaseModel):
    """Paging information"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    limit: Optional[int] = Field(None, description="Current limit being used for paging")
    next_key: Optional[str] = Field(None, description="Opaque string for next page")


class ServiceResponse(BaseModel):
    """Service response wrapper"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    data: Service


class SourcesResponse(BaseModel):
    """Sources list response"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    data: List[Source]
    paging: Optional[PagingInfo] = None


class FlowsResponse(BaseModel):
    """Flows list response"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    data: List[Flow]
    paging: Optional[PagingInfo] = None


class WebhooksResponse(BaseModel):
    """Webhooks list response"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    data: List[Webhook]


class DeletionRequestsResponse(BaseModel):
    """Deletion requests list response"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    data: DeletionRequestsList

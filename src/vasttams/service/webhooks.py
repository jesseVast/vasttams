"""
TAMS Webhook Models

This module contains models related to webhooks in the TAMS API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..common.models import validate_tams_uuid, Tags


class Webhook(BaseModel):
    """Webhook configuration - TAMS 8.0 compliant with tag support"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    url: str = Field(..., description="The URL to which the API should make HTTP POST requests with event data")
    api_key_name: str = Field(..., description="The HTTP header name that is added to the event POST")
    api_key_value: Optional[str] = Field(None, description="The value that the HTTP header 'api_key_name' will be set to")
    events: List[str] = Field(..., description="List of event types to receive")
    tags: Optional[Tags] = Field(None, description="Tags for filtering and organizing webhooks (TAMS 8.0)")
    
    # TAMS-specific filtering fields
    flow_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to Flows in the given list of Flow IDs")
    source_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to Sources in the given list of Source IDs")
    flow_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to those with Flow that is collected by a Flow Collection in the given list of Flow Collection IDs")
    source_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to those with Source that is collected by a Source Collection in the given list of Source Collection IDs")
    
    # TAMS-specific get_urls filtering fields
    accept_get_urls: Optional[List[str]] = Field(None, description="List of labels of URLs to include in the get_urls property in flows/segments_added events")
    accept_storage_ids: Optional[List[str]] = Field(None, description="List of labels of storage_ids to include in the get_urls property in flows/segments_added events")
    presigned: Optional[bool] = Field(None, description="Whether to include presigned/non-presigned URLs in the get_urls property in flows/segments_added events")
    verbose_storage: Optional[bool] = Field(None, description="Whether to include storage metadata in the get_urls property in flows/segments_added events")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @field_validator('flow_ids', 'source_ids', 'flow_collected_by_ids', 'source_collected_by_ids', 'accept_storage_ids')
    @classmethod
    def validate_uuid_lists(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            for uuid_str in v:
                validate_tams_uuid(uuid_str)
        return v


class WebhookPost(BaseModel):
    """Webhook registration request - TAMS compliant"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    url: str = Field(..., description="The URL to which the API should make HTTP POST requests with event data")
    api_key_name: str = Field(..., description="The HTTP header name that is added to the event POST")
    api_key_value: str = Field(..., description="The value that the HTTP header 'api_key_name' will be set to")
    events: List[str] = Field(..., description="List of event types to receive")
    
    # TAMS-specific filtering fields
    flow_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to Flows in the given list of Flow IDs")
    source_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to Sources in the given list of Source IDs")
    flow_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow and Flow Segment events to those with Flow that is collected by a Flow Collection in the given list of Flow Collection IDs")
    source_collected_by_ids: Optional[List[str]] = Field(None, description="Limit Flow, Flow Segment and Source events to those with Source that is collected by a Source Collection in the given list of Source Collection IDs")
    
    # TAMS-specific get_urls filtering fields
    accept_get_urls: Optional[List[str]] = Field(None, description="List of labels of URLs to include in the get_urls property in flows/segments_added events")
    accept_storage_ids: Optional[List[str]] = Field(None, description="List of labels of storage_ids to include in the get_urls property in flows/segments_added events")
    presigned: Optional[bool] = Field(None, description="Whether to include presigned/non-presigned URLs in the get_urls property in flows/segments_added events")
    verbose_storage: Optional[bool] = Field(None, description="Whether to include storage metadata in the get_urls property in flows/segments_added events")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @field_validator('flow_ids', 'source_ids', 'flow_collected_by_ids', 'source_collected_by_ids', 'accept_storage_ids')
    @classmethod
    def validate_uuid_lists(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            for uuid_str in v:
                validate_tams_uuid(uuid_str)
        return v

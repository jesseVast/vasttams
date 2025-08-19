"""
Core module for TAMS API
Contains configuration, dependencies, utilities, and telemetry
"""

from .config import Settings, get_settings, update_settings
# Import dependencies separately to avoid circular imports
from .utils import (
    generate_uuid,
    validate_timerange,
    validate_uuid,
    validate_tams_uuid,
    validate_mime_type,
    validate_tams_timestamp,
    validate_content_format,
    send_webhook_notification,
    send_webhook_notifications,
    create_deletion_request,
    update_deletion_request_status,
    parse_query_filters,
    build_paging_response,
    make_request,
)
from .telemetry import TelemetryManager
from .event_manager import EventManager

__all__ = [
    "Settings",
    "get_settings", 
    "update_settings",
    "TelemetryManager",
    
    # Utils functions
    "generate_uuid",
    "validate_timerange",
    "validate_uuid",
    "validate_tams_uuid",
    "validate_mime_type",
    "validate_tams_timestamp",
    "validate_content_format",
    "send_webhook_notification",
    "send_webhook_notifications",
    "create_deletion_request",
    "update_deletion_request_status",
    "parse_query_filters",
    "build_paging_response",
    "make_request",
    "EventManager",
] 
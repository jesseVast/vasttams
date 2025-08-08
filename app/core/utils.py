"""
Utility functions for the TAMS FastAPI service
"""

import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx
from ..models.models import Webhook, DeletionRequest
# Note: database imports removed as they're not in the new structure
from sqlalchemy.orm import Session
from uuid import UUID


def generate_uuid() -> str:
    """Generate a valid RFC4122 UUIDv4 for TAMS"""
    return str(uuid.uuid4())


def validate_timerange(timerange: str) -> bool:
    """Validate timerange format"""
    pattern = r'^(\[|\()?(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?(_(-?(0|[1-9][0-9]*):(0|[1-9][0-9]{0,8}))?)?(\]|\))?$'
    return bool(re.match(pattern, timerange))


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUIDv4 format only"""
    try:
        UUID(uuid_str)
        return True
    except Exception:
        return False


def validate_mime_type(mime_type: str) -> bool:
    """Validate MIME type format"""
    pattern = r'.*/.*'
    return bool(re.match(pattern, mime_type))


def validate_content_format(format_str: str) -> bool:
    """Validate content format URN"""
    valid_formats = [
        "urn:x-nmos:format:video",
        "urn:x-tam:format:image", 
        "urn:x-nmos:format:audio",
        "urn:x-nmos:format:data",
        "urn:x-nmos:format:multi"
    ]
    return format_str in valid_formats


async def send_webhook_notification(
    webhook: Webhook,
    event_type: str,
    event_data: Dict[str, Any],
    timeout: int = 30
) -> bool:
    """
    Send webhook notification
    
    Args:
        webhook: Webhook configuration
        event_type: Type of event (e.g., 'flows/created')
        event_data: Event data to send
        timeout: Request timeout in seconds
    
    Returns:
        bool: True if successful, False otherwise
    """
    payload = {
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "event": event_data
    }
    
    headers = {
        "Content-Type": "application/json",
        webhook.api_key_name: webhook.api_key_value or ""
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(webhook.url, json=payload, headers=headers)
            return response.status_code in [200, 201, 202]
    except Exception as e:
        print(f"Webhook notification failed: {e}")
        return False


async def send_webhook_notifications(
    db: Session,
    event_type: str,
    event_data: Dict[str, Any]
) -> None:
    """
    Send webhook notifications to all registered webhooks for an event type
    
    Args:
        db: Database session
        event_type: Type of event
        event_data: Event data to send
    """
    webhooks = db.query(WebhookModel).filter(
        WebhookModel.events.contains([event_type])
    ).all()
    
    for webhook_model in webhooks:
        webhook = Webhook(
            url=webhook_model.url,
            api_key_name=webhook_model.api_key_name,
            api_key_value=webhook_model.api_key_value,
            events=webhook_model.events
        )
        await send_webhook_notification(webhook, event_type, event_data)


def create_deletion_request(
    db: Session,
    flow_id: str,
    timerange: str
) -> DeletionRequest:
    """
    Create a new deletion request
    
    Args:
        db: Database session
        flow_id: Flow ID to delete
        timerange: Timerange to delete
    
    Returns:
        DeletionRequest: Created deletion request
    """
    request_id = f"delete_{generate_uuid()}"
    
    deletion_request = DeletionRequestModel(
        id=request_id,
        flow_id=flow_id,
        timerange=timerange,
        status="pending"
    )
    
    db.add(deletion_request)
    db.commit()
    db.refresh(deletion_request)
    
    return DeletionRequest(
        request_id=deletion_request.id,
        flow_id=deletion_request.flow_id,
        timerange=deletion_request.timerange,
        status=deletion_request.status,
        created=deletion_request.created,
        updated=deletion_request.updated
    )


def update_deletion_request_status(
    db: Session,
    request_id: str,
    status: str
) -> Optional[DeletionRequest]:
    """
    Update deletion request status
    
    Args:
        db: Database session
        request_id: Request ID to update
        status: New status
    
    Returns:
        DeletionRequest: Updated deletion request or None if not found
    """
    deletion_request = db.query(DeletionRequestModel).filter(
        DeletionRequestModel.id == request_id
    ).first()
    
    if not deletion_request:
        return None
    
    deletion_request.status = status
    deletion_request.updated = datetime.now(timezone.utc)
    db.commit()
    db.refresh(deletion_request)
    
    return DeletionRequest(
        request_id=deletion_request.id,
        flow_id=deletion_request.flow_id,
        timerange=deletion_request.timerange,
        status=deletion_request.status,
        created=deletion_request.created,
        updated=deletion_request.updated
    )


def parse_query_filters(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse query parameters for filtering
    
    Args:
        query_params: Query parameters from request
    
    Returns:
        Dict: Parsed filters
    """
    filters = {}
    
    # Handle tag filters
    tag_filters = {}
    tag_exists_filters = {}
    
    for key, value in query_params.items():
        if key.startswith("tag."):
            tag_name = key[4:]  # Remove "tag." prefix
            tag_filters[tag_name] = value
        elif key.startswith("tag_exists."):
            tag_name = key[11:]  # Remove "tag_exists." prefix
            tag_exists_filters[tag_name] = value.lower() == "true"
    
    if tag_filters:
        filters["tag_filters"] = tag_filters
    if tag_exists_filters:
        filters["tag_exists_filters"] = tag_exists_filters
    
    # Handle other filters
    for key in ["label", "format", "codec", "source_id", "timerange", "frame_width", "frame_height"]:
        if key in query_params:
            filters[key] = query_params[key]
    
    return filters


def build_paging_response(
    items: List[Any],
    limit: Optional[int] = None,
    page: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build response with paging information
    
    Args:
        items: List of items
        limit: Page limit
        page: Page token
    
    Returns:
        Dict: Response with paging info
    """
    response = {"data": items}
    
    if limit and len(items) == limit:
        # There might be more pages
        next_key = generate_uuid()  # In real implementation, encode cursor
        response["paging"] = {
            "limit": limit,
            "next_key": next_key
        }
    
    return response
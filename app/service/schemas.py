"""
Service table schemas for TAMS.

This module defines the PyArrow schemas for service-related tables (webhooks, deletion requests, auth).
"""

import pyarrow as pa


def get_webhooks_schema() -> pa.Schema:
    """Get webhooks table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("url", pa.string(), nullable=True),
        pa.field("api_key_name", pa.string(), nullable=True),
        pa.field("api_key_value", pa.string(), nullable=True),
        pa.field("events", pa.string(), nullable=True),  # JSON array string
        pa.field("flow_ids", pa.string(), nullable=True),  # JSON array string
        pa.field("source_ids", pa.string(), nullable=True),  # JSON array string
        pa.field("flow_collected_by_ids", pa.string(), nullable=True),  # JSON array string
        pa.field("source_collected_by_ids", pa.string(), nullable=True),  # JSON array string
        pa.field("accept_get_urls", pa.string(), nullable=True),  # JSON array string
        pa.field("accept_storage_ids", pa.string(), nullable=True),  # JSON array string
        pa.field("presigned", pa.bool_(), nullable=True),
        pa.field("verbose_storage", pa.bool_(), nullable=True),
        pa.field("tags", pa.string(), nullable=True),  # JSON string - TAMS 8.0
        pa.field("enabled", pa.bool_(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("updated", pa.timestamp("ns"), nullable=True),
    ])


def get_deletion_requests_schema() -> pa.Schema:
    """Get deletion_requests table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("flow_id", pa.string(), nullable=True),
        pa.field("timerange_to_delete", pa.string(), nullable=True),
        pa.field("delete_flow", pa.bool_(), nullable=True),
        pa.field("status", pa.string(), nullable=True),
        pa.field("timerange_remaining", pa.string(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("created_by", pa.string(), nullable=True),
        pa.field("updated", pa.timestamp("ns"), nullable=True),
        pa.field("expiry", pa.timestamp("ns"), nullable=True),
        pa.field("error", pa.string(), nullable=True),  # JSON string
    ])


def get_users_schema() -> pa.Schema:
    """Get users table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("username", pa.string(), nullable=True),
        pa.field("email", pa.string(), nullable=True),
        pa.field("password_hash", pa.string(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
        pa.field("updated", pa.timestamp("ns"), nullable=True),
    ])


def get_api_tokens_schema() -> pa.Schema:
    """Get api_tokens table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),
        pa.field("token_hash", pa.string(), nullable=True),
        pa.field("expires_at", pa.timestamp("ns"), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def get_refresh_tokens_schema() -> pa.Schema:
    """Get refresh_tokens table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),
        pa.field("token_hash", pa.string(), nullable=True),
        pa.field("expires_at", pa.timestamp("ns"), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


def get_auth_logs_schema() -> pa.Schema:
    """Get auth_logs table schema"""
    return pa.schema([
        pa.field("id", pa.string(), nullable=True),  # VAST requires nullable strings
        pa.field("user_id", pa.string(), nullable=True),
        pa.field("event_type", pa.string(), nullable=True),
        pa.field("ip_address", pa.string(), nullable=True),
        pa.field("user_agent", pa.string(), nullable=True),
        pa.field("created", pa.timestamp("ns"), nullable=True),
    ])


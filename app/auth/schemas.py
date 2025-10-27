"""
Authentication table schemas for TAMS.

This module defines the PyArrow schemas for authentication-related tables.
"""

import pyarrow as pa


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


#!/usr/bin/env python3
"""
Tests for Authentication Schemas

Tests auth schema definitions and projections.
"""

import pytest
import sys
from pathlib import Path
import pyarrow as pa

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.auth.schemas import (
    get_users_schema,
    get_api_tokens_schema,
    get_refresh_tokens_schema,
    get_auth_logs_schema,
    get_auth_provider_configs_schema,
    get_users_projections,
    get_api_tokens_projections,
    get_refresh_tokens_projections,
    get_auth_logs_projections,
    get_auth_provider_configs_projections
)


class TestAuthSchemas:
    """Test authentication schemas"""
    
    def test_get_users_schema(self):
        """Test get_users_schema returns correct schema"""
        schema = get_users_schema()
        
        assert isinstance(schema, pa.Schema)
        assert len(schema) == 7
        
        # Check required fields
        field_names = [field.name for field in schema]
        assert "id" in field_names
        assert "username" in field_names
        assert "email" in field_names
        assert "password_hash" in field_names
        assert "role" in field_names
        assert "created" in field_names
        assert "updated" in field_names
        
        # Check field types
        assert schema.field("id").type == pa.string()
        assert schema.field("username").type == pa.string()
        assert schema.field("role").type == pa.string()
        assert schema.field("created").type == pa.timestamp("ns")
    
    def test_get_api_tokens_schema(self):
        """Test get_api_tokens_schema returns correct schema"""
        schema = get_api_tokens_schema()
        
        assert isinstance(schema, pa.Schema)
        assert len(schema) == 5
        
        field_names = [field.name for field in schema]
        assert "id" in field_names
        assert "user_id" in field_names
        assert "token_hash" in field_names
        assert "expires_at" in field_names
        assert "created" in field_names
    
    def test_get_refresh_tokens_schema(self):
        """Test get_refresh_tokens_schema returns correct schema"""
        schema = get_refresh_tokens_schema()
        
        assert isinstance(schema, pa.Schema)
        assert len(schema) == 5
        
        field_names = [field.name for field in schema]
        assert "id" in field_names
        assert "user_id" in field_names
        assert "token_hash" in field_names
        assert "expires_at" in field_names
        assert "created" in field_names
    
    def test_get_auth_logs_schema(self):
        """Test get_auth_logs_schema returns correct schema"""
        schema = get_auth_logs_schema()
        
        assert isinstance(schema, pa.Schema)
        assert len(schema) == 6
        
        field_names = [field.name for field in schema]
        assert "id" in field_names
        assert "user_id" in field_names
        assert "event_type" in field_names
        assert "ip_address" in field_names
        assert "user_agent" in field_names
        assert "created" in field_names
    
    def test_get_auth_provider_configs_schema(self):
        """Test get_auth_provider_configs_schema returns correct schema"""
        schema = get_auth_provider_configs_schema()
        
        assert isinstance(schema, pa.Schema)
        # Schema has 10 fields (including 'updated')
        assert len(schema) == 10
        
        field_names = [field.name for field in schema]
        assert "method" in field_names
        assert "enabled" in field_names
        assert "config" in field_names
        assert "jwt_secret" in field_names
        assert "jwt_algorithm" in field_names
        assert "jwt_expire_minutes" in field_names
        assert "description" in field_names
        assert "order" in field_names
        assert "created" in field_names
        
        # Check field types
        assert schema.field("enabled").type == pa.bool_()
        assert schema.field("jwt_expire_minutes").type == pa.int64()
        assert schema.field("order").type == pa.int64()


class TestAuthProjections:
    """Test authentication table projections"""
    
    def test_get_users_projections(self):
        """Test get_users_projections returns correct projections"""
        projections = get_users_projections()
        
        assert isinstance(projections, list)
        assert len(projections) == 4
        
        # Check projection contents
        assert ["id"] in projections
        assert ["username"] in projections
        assert ["email"] in projections
        assert ["role"] in projections
    
    def test_get_api_tokens_projections(self):
        """Test get_api_tokens_projections returns correct projections"""
        projections = get_api_tokens_projections()
        
        assert isinstance(projections, list)
        assert len(projections) == 3
        
        assert ["id"] in projections
        assert ["user_id"] in projections
        assert ["token_hash"] in projections
    
    def test_get_refresh_tokens_projections(self):
        """Test get_refresh_tokens_projections returns correct projections"""
        projections = get_refresh_tokens_projections()
        
        assert isinstance(projections, list)
        assert len(projections) == 3
        
        assert ["id"] in projections
        assert ["user_id"] in projections
        assert ["token_hash"] in projections
    
    def test_get_auth_logs_projections(self):
        """Test get_auth_logs_projections returns correct projections"""
        projections = get_auth_logs_projections()
        
        assert isinstance(projections, list)
        assert len(projections) == 4
        
        assert ["id"] in projections
        assert ["user_id"] in projections
        assert ["event_type"] in projections
        assert ["created"] in projections
    
    def test_get_auth_provider_configs_projections(self):
        """Test get_auth_provider_configs_projections returns correct projections"""
        projections = get_auth_provider_configs_projections()
        
        assert isinstance(projections, list)
        assert len(projections) == 3
        
        assert ["method"] in projections
        assert ["enabled"] in projections
        assert ["order"] in projections


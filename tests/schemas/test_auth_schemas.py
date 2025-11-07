#!/usr/bin/env python3
"""
Tests for Auth Schemas

Tests the auth schema functions in src/vasttams/auth/schemas.py
"""

import pytest
import sys
import pyarrow as pa
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.auth.schemas import (
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


class TestUsersSchema:
    """Test users schema functions"""
    
    def test_get_users_schema_returns_schema(self):
        """Test that get_users_schema returns a PyArrow Schema"""
        schema = get_users_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_users_schema_has_expected_fields(self):
        """Test that users schema has expected fields"""
        schema = get_users_schema()
        field_names = [field.name for field in schema]
        expected_fields = ["id", "username", "email", "password_hash", "role", "created", "updated"]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in users schema"
    
    def test_get_users_projections_returns_list(self):
        """Test that get_users_projections returns a list"""
        projections = get_users_projections()
        assert isinstance(projections, list)
        assert len(projections) > 0


class TestAPITokensSchema:
    """Test API tokens schema functions"""
    
    def test_get_api_tokens_schema_returns_schema(self):
        """Test that get_api_tokens_schema returns a PyArrow Schema"""
        schema = get_api_tokens_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_api_tokens_schema_has_expected_fields(self):
        """Test that api_tokens schema has expected fields"""
        schema = get_api_tokens_schema()
        field_names = [field.name for field in schema]
        expected_fields = ["id", "user_id", "token_hash", "expires_at", "created"]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in api_tokens schema"
    
    def test_get_api_tokens_projections_returns_list(self):
        """Test that get_api_tokens_projections returns a list"""
        projections = get_api_tokens_projections()
        assert isinstance(projections, list)


class TestRefreshTokensSchema:
    """Test refresh tokens schema functions"""
    
    def test_get_refresh_tokens_schema_returns_schema(self):
        """Test that get_refresh_tokens_schema returns a PyArrow Schema"""
        schema = get_refresh_tokens_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_refresh_tokens_projections_returns_list(self):
        """Test that get_refresh_tokens_projections returns a list"""
        projections = get_refresh_tokens_projections()
        assert isinstance(projections, list)


class TestAuthLogsSchema:
    """Test auth logs schema functions"""
    
    def test_get_auth_logs_schema_returns_schema(self):
        """Test that get_auth_logs_schema returns a PyArrow Schema"""
        schema = get_auth_logs_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_auth_logs_schema_has_expected_fields(self):
        """Test that auth_logs schema has expected fields"""
        schema = get_auth_logs_schema()
        field_names = [field.name for field in schema]
        expected_fields = ["id", "user_id", "event_type", "ip_address", "user_agent", "created"]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in auth_logs schema"
    
    def test_get_auth_logs_projections_returns_list(self):
        """Test that get_auth_logs_projections returns a list"""
        projections = get_auth_logs_projections()
        assert isinstance(projections, list)


class TestAuthProviderConfigsSchema:
    """Test auth provider configs schema functions"""
    
    def test_get_auth_provider_configs_schema_returns_schema(self):
        """Test that get_auth_provider_configs_schema returns a PyArrow Schema"""
        schema = get_auth_provider_configs_schema()
        assert isinstance(schema, pa.Schema)
    
    def test_get_auth_provider_configs_schema_has_expected_fields(self):
        """Test that auth_provider_configs schema has expected fields"""
        schema = get_auth_provider_configs_schema()
        field_names = [field.name for field in schema]
        expected_fields = ["method", "enabled", "jwt_secret", "jwt_algorithm", 
                          "jwt_expire_minutes", "description", "order"]
        for field in expected_fields:
            assert field in field_names, f"Field {field} not found in auth_provider_configs schema"
    
    def test_get_auth_provider_configs_projections_returns_list(self):
        """Test that get_auth_provider_configs_projections returns a list"""
        projections = get_auth_provider_configs_projections()
        assert isinstance(projections, list)
    
    def test_get_users_schema_field_types(self):
        """Test that users schema fields have correct types"""
        schema = get_users_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["username"] == pa.string()
        assert field_dict["role"] == pa.string()
        assert isinstance(field_dict["created"], pa.TimestampType)
    
    def test_get_api_tokens_schema_field_types(self):
        """Test that api_tokens schema fields have correct types"""
        schema = get_api_tokens_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["user_id"] == pa.string()
        assert field_dict["token_hash"] == pa.string()
        assert isinstance(field_dict["created"], pa.TimestampType)
    
    def test_get_refresh_tokens_schema_field_types(self):
        """Test that refresh_tokens schema fields have correct types"""
        schema = get_refresh_tokens_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["user_id"] == pa.string()
        assert isinstance(field_dict["expires_at"], pa.TimestampType)
    
    def test_get_auth_logs_schema_field_types(self):
        """Test that auth_logs schema fields have correct types"""
        schema = get_auth_logs_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["id"] == pa.string()
        assert field_dict["event_type"] == pa.string()
        assert field_dict["ip_address"] == pa.string()
        assert isinstance(field_dict["created"], pa.TimestampType)
    
    def test_get_auth_provider_configs_schema_field_types(self):
        """Test that auth_provider_configs schema fields have correct types"""
        schema = get_auth_provider_configs_schema()
        field_dict = {field.name: field.type for field in schema}
        
        assert field_dict["method"] == pa.string()
        assert field_dict["enabled"] == pa.bool_()
        assert field_dict["jwt_algorithm"] == pa.string()
        assert field_dict["jwt_expire_minutes"] == pa.int64()
    
    def test_get_users_projections_are_lists(self):
        """Test that users projections are lists of column names"""
        projections = get_users_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_api_tokens_projections_are_lists(self):
        """Test that api_tokens projections are lists of column names"""
        projections = get_api_tokens_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_refresh_tokens_projections_are_lists(self):
        """Test that refresh_tokens projections are lists of column names"""
        projections = get_refresh_tokens_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_auth_logs_projections_are_lists(self):
        """Test that auth_logs projections are lists of column names"""
        projections = get_auth_logs_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)
    
    def test_get_auth_provider_configs_projections_are_lists(self):
        """Test that auth_provider_configs projections are lists of column names"""
        projections = get_auth_provider_configs_projections()
        for proj in projections:
            assert isinstance(proj, list)
            assert all(isinstance(col, str) for col in proj)


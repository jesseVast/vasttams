#!/usr/bin/env python3
"""
Tests for Role-Based Access Control (RBAC)

Tests RBAC functions and role requirements.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock
from fastapi import HTTPException, Depends

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttams.auth.rbac import (
    require_role,
    require_admin,
    require_editor,
    require_viewer,
    check_permission
)
from vasttams.auth.models import UserSession, UserRole, AuthMethod
from datetime import datetime, timezone


class TestRBACFunctions:
    """Test RBAC functions"""
    
    def test_require_admin_success(self):
        """Test require_admin with admin user"""
        user_session = UserSession(
            user_id="admin1",
            username="admin",
            role=UserRole.ADMIN,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        result = require_admin(user_session)
        
        assert result == user_session
    
    def test_require_admin_failure(self):
        """Test require_admin raises exception for non-admin"""
        user_session = UserSession(
            user_id="user1",
            username="viewer",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user_session)
        
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail
    
    def test_require_editor_success_admin(self):
        """Test require_editor with admin user"""
        user_session = UserSession(
            user_id="admin1",
            username="admin",
            role=UserRole.ADMIN,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        result = require_editor(user_session)
        
        assert result == user_session
    
    def test_require_editor_success_editor(self):
        """Test require_editor with editor user"""
        user_session = UserSession(
            user_id="editor1",
            username="editor",
            role=UserRole.EDITOR,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        result = require_editor(user_session)
        
        assert result == user_session
    
    def test_require_editor_failure(self):
        """Test require_editor raises exception for viewer"""
        user_session = UserSession(
            user_id="user1",
            username="viewer",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            require_editor(user_session)
        
        assert exc_info.value.status_code == 403
        assert "Editor or admin access required" in exc_info.value.detail
    
    def test_require_viewer_success(self):
        """Test require_viewer with any authenticated user"""
        user_session = UserSession(
            user_id="user1",
            username="viewer",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        result = require_viewer(user_session)
        
        assert result == user_session
    
    @pytest.mark.asyncio
    async def test_require_role_success(self):
        """Test require_role with matching role"""
        role_checker = require_role([UserRole.VIEWER, UserRole.EDITOR])
        
        user_session = UserSession(
            user_id="user1",
            username="editor",
            role=UserRole.EDITOR,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        result = await role_checker(user_session)
        
        assert result == user_session
    
    @pytest.mark.asyncio
    async def test_require_role_failure(self):
        """Test require_role raises exception for non-matching role"""
        role_checker = require_role([UserRole.ADMIN])
        
        user_session = UserSession(
            user_id="user1",
            username="viewer",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await role_checker(user_session)
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail


class TestCheckPermission:
    """Test check_permission function"""
    
    def test_check_permission_admin_read(self):
        """Test check_permission for admin read operation"""
        user_session = UserSession(
            user_id="admin1",
            username="admin",
            role=UserRole.ADMIN,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        assert check_permission(user_session, "read", "source") is True
        assert check_permission(user_session, "write", "source") is True
        assert check_permission(user_session, "delete", "source") is True
    
    def test_check_permission_editor_read_write(self):
        """Test check_permission for editor read/write operations"""
        user_session = UserSession(
            user_id="editor1",
            username="editor",
            role=UserRole.EDITOR,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        assert check_permission(user_session, "read", "source") is True
        assert check_permission(user_session, "write", "source") is True
        assert check_permission(user_session, "delete", "source") is False
    
    def test_check_permission_viewer_read_only(self):
        """Test check_permission for viewer read-only access"""
        user_session = UserSession(
            user_id="viewer1",
            username="viewer",
            role=UserRole.VIEWER,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        assert check_permission(user_session, "read", "source") is True
        assert check_permission(user_session, "write", "source") is False
        assert check_permission(user_session, "delete", "source") is False
    
    def test_check_permission_different_resources(self):
        """Test check_permission with different resource types"""
        user_session = UserSession(
            user_id="editor1",
            username="editor",
            role=UserRole.EDITOR,
            auth_method=AuthMethod.BEARER,
            created_at=datetime.now(timezone.utc)
        )
        
        # Editor can read/write all resource types
        assert check_permission(user_session, "read", "source") is True
        assert check_permission(user_session, "read", "flow") is True
        assert check_permission(user_session, "read", "segment") is True
        assert check_permission(user_session, "read", "object") is True
        assert check_permission(user_session, "write", "source") is True
        assert check_permission(user_session, "write", "flow") is True
        assert check_permission(user_session, "delete", "source") is False


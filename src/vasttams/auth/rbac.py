"""
Role-Based Access Control (RBAC) for TAMS API

Defines permission checks and role-based dependencies for FastAPI endpoints.
"""

import logging
from typing import List
from fastapi import Depends, HTTPException
from .models import UserSession, UserRole
from .middleware import require_authentication

logger = logging.getLogger(__name__)


def require_role(allowed_roles: List[UserRole]):
    """Factory function to create a dependency that requires specific roles"""
    async def role_checker(user_session: UserSession = Depends(require_authentication)) -> UserSession:
        if user_session.role not in allowed_roles:
            logger.warning(
                "User %s with role %s attempted to access resource requiring %s",
                user_session.username, user_session.role, allowed_roles
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        
        logger.debug("Role check passed for user %s with role %s", user_session.username, user_session.role)
        return user_session
    
    return role_checker


def require_admin(user_session: UserSession = Depends(require_authentication)) -> UserSession:
    """Require admin role"""
    if user_session.role != UserRole.ADMIN:
        logger.warning(
            "User %s with role %s attempted admin-only operation",
            user_session.username, user_session.role
        )
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user_session


def require_editor(user_session: UserSession = Depends(require_authentication)) -> UserSession:
    """Require editor or admin role (allows write operations)"""
    if user_session.role not in [UserRole.EDITOR, UserRole.ADMIN]:
        logger.warning(
            "User %s with role %s attempted editor-level operation",
            user_session.username, user_session.role
        )
        raise HTTPException(status_code=403, detail="Editor or admin access required")
    
    return user_session


def require_viewer(user_session: UserSession = Depends(require_authentication)) -> UserSession:
    """Require any authenticated user (viewer, editor, or admin)"""
    # All authenticated users can view
    return user_session


def check_permission(user_session: UserSession, operation: str, resource: str) -> bool:
    """
    Check if user has permission for operation on resource
    
    Roles:
    - ADMIN: Full access to all operations
    - EDITOR: Read + write (no delete) on sources/flows/segments/objects
    - VIEWER: Read-only access
    
    Args:
        user_session: User session with role
        operation: Operation type (read, write, delete)
        resource: Resource type (source, flow, segment, object)
    
    Returns:
        bool: True if permission granted
    """
    role = user_session.role
    
    # Admin has full access
    if role == UserRole.ADMIN:
        return True
    
    # Viewer can only read
    if role == UserRole.VIEWER:
        return operation == "read"
    
    # Editor can read and write (but not delete)
    if role == UserRole.EDITOR:
        return operation in ["read", "write"]
    
    return False


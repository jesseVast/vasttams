"""
Authentication dependencies for TAMS API 7.0
"""

from typing import Optional
from fastapi import Depends, Request

from .core import AuthManager
from .providers.jwt import JWTProvider
from .providers.basic import BasicAuthProvider
from .providers.url_token import URLTokenProvider
from .middleware import get_current_user_session, require_authentication
from .models import UserSession

# Global auth manager instance
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
        
        # Add providers
        _auth_manager.add_provider(JWTProvider())
        _auth_manager.add_provider(BasicAuthProvider())
        _auth_manager.add_provider(URLTokenProvider())
    
    return _auth_manager

def get_jwt_provider() -> JWTProvider:
    """Get JWT provider instance"""
    return JWTProvider()

def get_basic_provider() -> BasicAuthProvider:
    """Get Basic auth provider instance"""
    return BasicAuthProvider()

def get_url_token_provider() -> URLTokenProvider:
    """Get URL token provider instance"""
    return URLTokenProvider()

# Re-export middleware functions
get_current_user = get_current_user_session
require_auth = require_authentication 
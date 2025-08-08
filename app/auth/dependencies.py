"""
Authentication dependencies for TAMS API 7.0 with database support
"""

from typing import Optional
from fastapi import Depends, Request

from .core import AuthManager
from .providers.jwt import JWTProvider
from .providers.basic import BasicAuthProvider
from .providers.url_token import URLTokenProvider
from .middleware import get_current_user_session, require_authentication
from .models import UserSession
from ..core.dependencies import get_vast_store

# Global auth manager instance
_auth_manager = None

def get_auth_manager(vast_store=Depends(get_vast_store)) -> AuthManager:
    """Get the global auth manager instance with database support"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
        
        # Add providers with database support
        _auth_manager.add_provider(JWTProvider())
        _auth_manager.add_provider(BasicAuthProvider(vast_store=vast_store))
        _auth_manager.add_provider(URLTokenProvider(vast_store=vast_store))
    
    return _auth_manager

def get_jwt_provider() -> JWTProvider:
    """Get JWT provider instance"""
    return JWTProvider()

def get_basic_provider(vast_store=Depends(get_vast_store)) -> BasicAuthProvider:
    """Get Basic auth provider instance with database support"""
    return BasicAuthProvider(vast_store=vast_store)

def get_url_token_provider(vast_store=Depends(get_vast_store)) -> URLTokenProvider:
    """Get URL token provider instance with database support"""
    return URLTokenProvider(vast_store=vast_store)

# Re-export middleware functions
get_current_user = get_current_user_session
require_auth = require_authentication 
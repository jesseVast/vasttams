"""
Core authentication interfaces for TAMS API 7.0
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from fastapi import Request

from .models import AuthResult, AuthMethod

logger = logging.getLogger(__name__)

class AuthProvider(ABC):
    """Base authentication provider interface"""
    
    @abstractmethod
    async def authenticate(self, request: Request) -> AuthResult:
        """Authenticate a request"""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if this provider is enabled"""
        pass
    
    @abstractmethod
    def get_method(self) -> AuthMethod:
        """Get the authentication method this provider handles"""
        pass

class AuthManager:
    """Manages multiple authentication providers"""
    
    def __init__(self):
        self.providers: list[AuthProvider] = []
        logger.debug("AuthManager initialized with %d providers", len(self.providers))
    
    def add_provider(self, provider: AuthProvider):
        """Add an authentication provider"""
        self.providers.append(provider)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Added auth provider: %s", provider.__class__.__name__)
    
    async def authenticate(self, request: Request) -> AuthResult:
        """Try all enabled providers until one succeeds"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Attempting authentication with %d providers", len(self.providers))
        
        for provider in self.providers:
            if provider.is_enabled():
                try:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Trying provider: %s", provider.__class__.__name__)
                    
                    result = await provider.authenticate(request)
                    if result.success:
                        result.auth_method = provider.get_method()
                        logger.info("Authentication successful with provider: %s", provider.__class__.__name__)
                        return result
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Provider %s failed: %s", provider.__class__.__name__, result.error)
                except Exception as e:
                    logger.warning("Provider %s raised exception: %s", provider.__class__.__name__, e)
                    continue
        
        logger.warning("All authentication providers failed")
        return AuthResult(success=False, error="Authentication failed") 
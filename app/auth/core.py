"""
Core authentication interfaces for TAMS API 7.0
"""

from abc import ABC, abstractmethod
from typing import Optional
from fastapi import Request

from .models import AuthResult, AuthMethod

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
    
    def add_provider(self, provider: AuthProvider):
        """Add an authentication provider"""
        self.providers.append(provider)
    
    async def authenticate(self, request: Request) -> AuthResult:
        """Try all enabled providers until one succeeds"""
        for provider in self.providers:
            if provider.is_enabled():
                try:
                    result = await provider.authenticate(request)
                    if result.success:
                        result.auth_method = provider.get_method()
                        return result
                except Exception as e:
                    continue
        
        return AuthResult(success=False, error="Authentication failed") 
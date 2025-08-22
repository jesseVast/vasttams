"""
Base authentication provider interface
"""

from abc import ABC, abstractmethod
from typing import Optional
from fastapi import Request

from ..models import AuthResult, AuthMethod

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
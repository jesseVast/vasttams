"""
Authentication Service

This module provides services for managing auth provider configurations.
"""

import logging
from typing import List, Optional, Dict, Any
from .models import AuthMethod
from .provider_config import AuthProviderConfig, AuthProviderConfigList

logger = logging.getLogger(__name__)


class AuthProviderService:
    """Service for managing auth provider configurations"""
    
    def __init__(self, vast_db, auth_manager=None):
        self.vast_db = vast_db
        self.auth_manager = auth_manager
    
    async def get_provider_configs(self) -> List[AuthProviderConfig]:
        """Get all provider configurations"""
        try:
            # Query auth_provider_configs table
            result = self.vast_db.query("auth_provider_configs").select("*").execute()
            
            if result and result.get('data'):
                configs = []
                for row in result['data']:
                    config = AuthProviderConfig(
                        method=AuthMethod(row['method']),
                        enabled=row.get('enabled', True),
                        config=row.get('config', {}),
                        jwt_secret=row.get('jwt_secret'),
                        jwt_algorithm=row.get('jwt_algorithm'),
                        jwt_expire_minutes=row.get('jwt_expire_minutes'),
                        description=row.get('description'),
                        order=row.get('order', 0)
                    )
                    configs.append(config)
                
                # Sort by order
                configs.sort(key=lambda x: x.order)
                return configs
            
            return self._get_default_configs()
            
        except Exception as e:
            logger.error("Failed to get provider configs: %s", e)
            return self._get_default_configs()
    
    def _get_default_configs(self) -> List[AuthProviderConfig]:
        """Get default provider configurations (hard-coded fallback)"""
        return [
            AuthProviderConfig(
                method=AuthMethod.BEARER,
                enabled=True,
                description="JWT Bearer token authentication",
                order=1,
                jwt_secret="your-secret-key",
                jwt_algorithm="HS256",
                jwt_expire_minutes=30
            ),
            AuthProviderConfig(
                method=AuthMethod.BASIC,
                enabled=True,
                description="HTTP Basic authentication",
                order=2,
                requires_vast_store=True
            ),
            AuthProviderConfig(
                method=AuthMethod.URL_TOKEN,
                enabled=True,
                description="URL token authentication",
                order=3,
                requires_vast_store=True
            ),
        ]
    
    async def update_provider_config(self, method: AuthMethod, config: AuthProviderConfig) -> bool:
        """Update a provider configuration"""
        try:
            # Check if record exists
            existing = self.vast_db.query("auth_provider_configs").select("*").where(
                f"method = '{method.value}'"
            ).execute()
            
            data = {
                'method': method.value,
                'enabled': config.enabled,
                'config': config.config,
                'jwt_secret': config.jwt_secret,
                'jwt_algorithm': config.jwt_algorithm,
                'jwt_expire_minutes': config.jwt_expire_minutes,
                'description': config.description,
                'order': config.order
            }
            
            if existing and existing.get('data'):
                # Update existing
                self.vast_db.query("auth_provider_configs").update(data).where(
                    f"method = '{method.value}'"
                ).execute()
            else:
                # Insert new
                self.vast_db.query("auth_provider_configs").insert(data).execute()
            
            # Reload auth manager if provided
            if self.auth_manager:
                await self._reload_auth_manager()
            
            return True
            
        except Exception as e:
            logger.error("Failed to update provider config: %s", e)
            return False
    
    async def _reload_auth_manager(self):
        """Reload auth manager with new configurations"""
        if not self.auth_manager:
            return
        
        try:
            configs = await self.get_provider_configs()
            
            # Clear existing providers
            self.auth_manager.providers.clear()
            
            # Re-register providers based on config
            for config in configs:
                if not config.enabled:
                    continue
                
                if config.method == AuthMethod.BEARER:
                    from .providers.jwt import JWTProvider
                    provider = JWTProvider(
                        jwt_secret=config.jwt_secret or "your-secret-key",
                        jwt_algorithm=config.jwt_algorithm or "HS256",
                        jwt_expire_minutes=config.jwt_expire_minutes or 30
                    )
                    self.auth_manager.add_provider(provider)
                
                elif config.method == AuthMethod.BASIC:
                    from .providers.basic import BasicAuthProvider
                    provider = BasicAuthProvider(vast_store=self.vast_db)
                    self.auth_manager.add_provider(provider)
                
                elif config.method == AuthMethod.URL_TOKEN:
                    from .providers.url_token import URLTokenProvider
                    provider = URLTokenProvider(vast_store=self.vast_db)
                    self.auth_manager.add_provider(provider)
            
            logger.info("Auth manager reloaded with %d providers", len(self.auth_manager.providers))
            
        except Exception as e:
            logger.error("Failed to reload auth manager: %s", e)


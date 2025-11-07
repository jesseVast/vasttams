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
                    import json
                    
                    config_dict = {}
                    if row.get('config'):
                        try:
                            config_dict = json.loads(row['config']) if isinstance(row['config'], str) else row['config']
                        except (json.JSONDecodeError, TypeError):
                            config_dict = {}
                    
                    config = AuthProviderConfig(
                        method=AuthMethod(row['method']),
                        enabled=row.get('enabled', True),
                        config=config_dict,
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
            
            import json
            
            data = {
                'method': method.value,
                'enabled': config.enabled,
                'config': json.dumps(config.config) if config.config else None,
                'jwt_secret': config.jwt_secret,
                'jwt_algorithm': config.jwt_algorithm,
                'jwt_expire_minutes': config.jwt_expire_minutes,
                'description': config.description,
                'order': config.order
            }
            
            if existing and existing.get('data'):
                # Update existing using SQL
                from ..common.storage.timestamp_utils import prepare_data_for_sql
                update_data = prepare_data_for_sql(data)
                
                set_clauses = []
                for column, value in update_data.items():
                    # Quote column names to handle reserved keywords like 'order'
                    quoted_column = f'"{column}"'
                    if isinstance(value, str):
                        escaped_value = value.replace("'", "''")
                        set_clauses.append(f"{quoted_column} = '{escaped_value}'")
                    elif value is None:
                        set_clauses.append(f"{quoted_column} = NULL")
                    else:
                        set_clauses.append(f"{quoted_column} = {value}")
                
                if set_clauses:
                    table = self.vast_db.get_qualified_table_name("auth_provider_configs")
                    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE method = '{method.value}'"
                    self.vast_db.execute_sql(sql)
            else:
                # Insert new record
                from ..common.storage.timestamp_utils import prepare_data_for_pyarrow
                insert_data = prepare_data_for_pyarrow(data)
                self.vast_db.insert_record("auth_provider_configs", insert_data)
            
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
            
            logger.debug("Auth manager reloaded with %d providers", len(self.auth_manager.providers))
            
        except Exception as e:
            logger.error("Failed to reload auth manager: %s", e)


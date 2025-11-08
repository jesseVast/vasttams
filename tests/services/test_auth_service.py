#!/usr/bin/env python3
"""
Service Layer Tests for Auth Provider Service

Tests auth/service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.auth.service import AuthProviderService
from vasttamsserver.auth.models import AuthMethod
from vasttamsserver.auth.provider_config import AuthProviderConfig


class TestAuthProviderService:
    """Test AuthProviderService"""
    
    def test_init(self):
        """Test service initialization"""
        mock_db = Mock()
        mock_auth_manager = Mock()
        service = AuthProviderService(mock_db, mock_auth_manager)
        assert service.vast_db == mock_db
        assert service.auth_manager == mock_auth_manager
    
    def test_init_without_auth_manager(self):
        """Test service initialization without auth manager"""
        mock_db = Mock()
        service = AuthProviderService(mock_db)
        assert service.vast_db == mock_db
        assert service.auth_manager is None
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_with_data(self):
        """Test get_provider_configs with database data"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'method': 'bearer',
                    'enabled': True,
                    'config': '{"key": "value"}',
                    'jwt_secret': 'secret123',
                    'jwt_algorithm': 'HS256',
                    'jwt_expire_minutes': 60,
                    'description': 'Test JWT',
                    'order': 1
                },
                {
                    'method': 'basic',
                    'enabled': False,
                    'config': None,
                    'jwt_secret': None,
                    'jwt_algorithm': None,
                    'jwt_expire_minutes': None,
                    'description': 'Test Basic',
                    'order': 2
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 2
        assert configs[0].method == AuthMethod.BEARER
        assert configs[0].enabled is True
        assert configs[0].jwt_secret == 'secret123'
        assert configs[0].config == {'key': 'value'}
        assert configs[1].method == AuthMethod.BASIC
        assert configs[1].enabled is False
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_with_json_string_config(self):
        """Test get_provider_configs with JSON string config"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'method': 'bearer',
                    'enabled': True,
                    'config': '{"setting": "value"}',
                    'jwt_secret': 'secret',
                    'jwt_algorithm': 'HS256',
                    'jwt_expire_minutes': 30,
                    'description': 'Test',
                    'order': 1
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 1
        assert configs[0].config == {'setting': 'value'}
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_with_dict_config(self):
        """Test get_provider_configs with dict config"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'method': 'bearer',
                    'enabled': True,
                    'config': {'setting': 'value'},
                    'jwt_secret': 'secret',
                    'jwt_algorithm': 'HS256',
                    'jwt_expire_minutes': 30,
                    'description': 'Test',
                    'order': 1
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 1
        assert configs[0].config == {'setting': 'value'}
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_with_invalid_json(self):
        """Test get_provider_configs with invalid JSON config"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'method': 'bearer',
                    'enabled': True,
                    'config': 'invalid json{',
                    'jwt_secret': 'secret',
                    'jwt_algorithm': 'HS256',
                    'jwt_expire_minutes': 30,
                    'description': 'Test',
                    'order': 1
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 1
        assert configs[0].config == {}
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_sorted_by_order(self):
        """Test get_provider_configs sorts by order"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'method': 'basic',
                    'enabled': True,
                    'config': {},
                    'jwt_secret': None,
                    'jwt_algorithm': None,
                    'jwt_expire_minutes': None,
                    'description': 'Second',
                    'order': 2
                },
                {
                    'method': 'bearer',
                    'enabled': True,
                    'config': {},
                    'jwt_secret': 'secret',
                    'jwt_algorithm': 'HS256',
                    'jwt_expire_minutes': 30,
                    'description': 'First',
                    'order': 1
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 2
        assert configs[0].order == 1
        assert configs[0].method == AuthMethod.BEARER
        assert configs[1].order == 2
        assert configs[1].method == AuthMethod.BASIC
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_no_data_returns_defaults(self):
        """Test get_provider_configs returns defaults when no data"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {'data': []}
        mock_db.query.return_value = mock_query
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 3
        assert configs[0].method == AuthMethod.BEARER
        assert configs[1].method == AuthMethod.BASIC
        assert configs[2].method == AuthMethod.URL_TOKEN
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_none_result_returns_defaults(self):
        """Test get_provider_configs returns defaults when result is None"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = None
        mock_db.query.return_value = mock_query
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 3
    
    @pytest.mark.asyncio
    async def test_get_provider_configs_exception_returns_defaults(self):
        """Test get_provider_configs returns defaults on exception"""
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database error")
        
        service = AuthProviderService(mock_db)
        configs = await service.get_provider_configs()
        
        assert len(configs) == 3
    
    def test_get_default_configs(self):
        """Test _get_default_configs returns default configurations"""
        mock_db = Mock()
        service = AuthProviderService(mock_db)
        configs = service._get_default_configs()
        
        assert len(configs) == 3
        assert configs[0].method == AuthMethod.BEARER
        assert configs[0].enabled is True
        assert configs[0].jwt_secret == "your-secret-key"
        assert configs[0].jwt_algorithm == "HS256"
        assert configs[0].jwt_expire_minutes == 30
        assert configs[0].order == 1
        
        assert configs[1].method == AuthMethod.BASIC
        assert configs[1].enabled is True
        assert configs[1].requires_vast_store is True
        assert configs[1].order == 2
        
        assert configs[2].method == AuthMethod.URL_TOKEN
        assert configs[2].enabled is True
        assert configs[2].requires_vast_store is True
        assert configs[2].order == 3
    
    @pytest.mark.asyncio
    async def test_update_provider_config_update_existing(self):
        """Test update_provider_config updates existing config"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': [{'method': 'bearer'}]}
        mock_db.query.return_value = mock_query
        mock_db.get_qualified_table_name.return_value = "public.auth_provider_configs"
        mock_db.execute_sql = Mock()
        
        config = AuthProviderConfig(
            method=AuthMethod.BEARER,
            enabled=True,
            config={'key': 'value'},
            jwt_secret='new_secret',
            jwt_algorithm='HS256',
            jwt_expire_minutes=60,
            description='Updated',
            order=1
        )
        
        service = AuthProviderService(mock_db)
        result = await service.update_provider_config(AuthMethod.BEARER, config)
        
        assert result is True
        assert mock_db.execute_sql.called
    
    @pytest.mark.asyncio
    async def test_update_provider_config_insert_new(self):
        """Test update_provider_config inserts new config"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': []}  # No existing
        mock_db.query.return_value = mock_query
        mock_db.insert_record = Mock()
        
        config = AuthProviderConfig(
            method=AuthMethod.BEARER,
            enabled=True,
            config={'key': 'value'},
            jwt_secret='secret',
            jwt_algorithm='HS256',
            jwt_expire_minutes=30,
            description='New',
            order=1
        )
        
        service = AuthProviderService(mock_db)
        result = await service.update_provider_config(AuthMethod.BEARER, config)
        
        assert result is True
        assert mock_db.insert_record.called
    
    @pytest.mark.asyncio
    async def test_update_provider_config_with_none_config(self):
        """Test update_provider_config with None config dict"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': []}
        mock_db.query.return_value = mock_query
        mock_db.insert_record = Mock()
        
        config = AuthProviderConfig(
            method=AuthMethod.BASIC,
            enabled=True,
            config={},
            description='Basic Auth',
            order=2
        )
        
        service = AuthProviderService(mock_db)
        result = await service.update_provider_config(AuthMethod.BASIC, config)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_provider_config_reloads_auth_manager(self):
        """Test update_provider_config reloads auth manager"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.execute.return_value = {'data': []}
        mock_db.query.return_value = mock_query
        mock_db.insert_record = Mock()
        
        mock_auth_manager = Mock()
        mock_auth_manager.providers = {}
        mock_auth_manager.add_provider = Mock()
        
        config = AuthProviderConfig(
            method=AuthMethod.BEARER,
            enabled=True,
            jwt_secret='secret',
            jwt_algorithm='HS256',
            jwt_expire_minutes=30,
            description='Test',
            order=1
        )
        
        service = AuthProviderService(mock_db, mock_auth_manager)
        
        with patch.object(service, '_reload_auth_manager', new_callable=AsyncMock) as mock_reload:
            result = await service.update_provider_config(AuthMethod.BEARER, config)
            
            assert result is True
            mock_reload.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_provider_config_exception_returns_false(self):
        """Test update_provider_config returns False on exception"""
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database error")
        
        config = AuthProviderConfig(
            method=AuthMethod.BEARER,
            enabled=True,
            description='Test',
            order=1
        )
        
        service = AuthProviderService(mock_db)
        result = await service.update_provider_config(AuthMethod.BEARER, config)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_reload_auth_manager_no_auth_manager(self):
        """Test _reload_auth_manager does nothing without auth manager"""
        mock_db = Mock()
        service = AuthProviderService(mock_db)
        
        # Should not raise exception
        await service._reload_auth_manager()
    
    @pytest.mark.asyncio
    async def test_reload_auth_manager_with_providers(self):
        """Test _reload_auth_manager reloads providers"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'method': 'bearer',
                    'enabled': True,
                    'config': {},
                    'jwt_secret': 'secret',
                    'jwt_algorithm': 'HS256',
                    'jwt_expire_minutes': 30,
                    'description': 'JWT',
                    'order': 1
                },
                {
                    'method': 'basic',
                    'enabled': True,
                    'config': {},
                    'jwt_secret': None,
                    'jwt_algorithm': None,
                    'jwt_expire_minutes': None,
                    'description': 'Basic',
                    'order': 2
                },
                {
                    'method': 'url_token',
                    'enabled': False,  # Disabled
                    'config': {},
                    'jwt_secret': None,
                    'jwt_algorithm': None,
                    'jwt_expire_minutes': None,
                    'description': 'URL Token',
                    'order': 3
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        mock_auth_manager = Mock()
        mock_auth_manager.providers = {}
        mock_auth_manager.add_provider = Mock()
        
        service = AuthProviderService(mock_db, mock_auth_manager)
        
        with patch('vasttams.auth.providers.jwt.JWTProvider') as mock_jwt, \
             patch('vasttams.auth.providers.basic.BasicAuthProvider') as mock_basic, \
             patch('vasttams.auth.providers.url_token.URLTokenProvider') as mock_url:
            
            mock_jwt_instance = Mock()
            mock_jwt.return_value = mock_jwt_instance
            
            mock_basic_instance = Mock()
            mock_basic.return_value = mock_basic_instance
            
            await service._reload_auth_manager()
            
            # Should add 2 providers (bearer and basic, but not url_token since disabled)
            assert mock_auth_manager.add_provider.call_count == 2
            mock_auth_manager.add_provider.assert_any_call(mock_jwt_instance)
            mock_auth_manager.add_provider.assert_any_call(mock_basic_instance)
    
    @pytest.mark.asyncio
    async def test_reload_auth_manager_exception_handling(self):
        """Test _reload_auth_manager handles exceptions gracefully"""
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database error")
        
        mock_auth_manager = Mock()
        mock_auth_manager.providers = {}
        
        service = AuthProviderService(mock_db, mock_auth_manager)
        
        # Should not raise exception
        await service._reload_auth_manager()


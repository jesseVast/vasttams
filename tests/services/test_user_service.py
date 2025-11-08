#!/usr/bin/env python3
"""
Service Layer Tests for User Service

Tests auth/user_service.py to achieve coverage.
Uses mocks to test business logic without database dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import uuid

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.auth.user_service import UserService
from vasttamsserver.auth.models import User, UserRole


class TestUserService:
    """Test UserService"""
    
    def test_init(self):
        """Test service initialization"""
        mock_db = Mock()
        service = UserService(mock_db)
        assert service.vast_db == mock_db
    
    def test_hash_password(self):
        """Test hash_password creates valid hash"""
        mock_db = Mock()
        service = UserService(mock_db)
        
        password = "test_password_123"
        hashed = service.hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0
        # Bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
    
    def test_hash_password_different_hashes(self):
        """Test hash_password produces different hashes for same password"""
        mock_db = Mock()
        service = UserService(mock_db)
        
        password = "same_password"
        hash1 = service.hash_password(password)
        hash2 = service.hash_password(password)
        
        # Should be different due to salt
        assert hash1 != hash2
    
    def test_verify_password_valid(self):
        """Test verify_password with valid password"""
        mock_db = Mock()
        service = UserService(mock_db)
        
        password = "test_password"
        hashed = service.hash_password(password)
        
        result = service.verify_password(password, hashed)
        
        assert result is True
    
    def test_verify_password_invalid(self):
        """Test verify_password with invalid password"""
        mock_db = Mock()
        service = UserService(mock_db)
        
        password = "test_password"
        wrong_password = "wrong_password"
        hashed = service.hash_password(password)
        
        result = service.verify_password(wrong_password, hashed)
        
        assert result is False
    
    def test_verify_password_exception_handling(self):
        """Test verify_password handles exceptions gracefully"""
        mock_db = Mock()
        service = UserService(mock_db)
        
        # Invalid hash format
        result = service.verify_password("password", "invalid_hash")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test create_user creates user successfully"""
        mock_db = Mock()
        mock_db.insert_record = Mock()
        
        service = UserService(mock_db)
        
        with patch('vasttamsserver.auth.user_service.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
            
            user = await service.create_user("testuser", "password123", UserRole.EDITOR)
            
            assert user is not None
            assert user.username == "testuser"
            assert user.role == UserRole.EDITOR
            assert user.user_id == "12345678-1234-5678-1234-567812345678"
            assert user.password_hash is not None
            assert user.created_at is not None
            assert user.updated_at is not None
            
            # Verify password is hashed
            assert service.verify_password("password123", user.password_hash) is True
            
            # Verify database insert was called
            assert mock_db.insert_record.called
            call_args = mock_db.insert_record.call_args
            assert call_args[0][0] == "users"
            assert call_args[0][1]["username"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_create_user_default_role(self):
        """Test create_user uses VIEWER as default role"""
        mock_db = Mock()
        mock_db.insert_record = Mock()
        
        service = UserService(mock_db)
        
        with patch('vasttamsserver.auth.user_service.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
            
            user = await service.create_user("testuser", "password123")
            
            assert user.role == UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_create_user_exception(self):
        """Test create_user raises exception on database error"""
        mock_db = Mock()
        mock_db.insert_record.side_effect = Exception("Database error")
        
        service = UserService(mock_db)
        
        with pytest.raises(Exception):
            await service.create_user("testuser", "password123")
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_found_row_format(self):
        """Test get_user_by_username finds user in row format"""
        mock_db = Mock()
        mock_db.execute_sql.return_value = {
            'data': [
                {
                    'id': 'user-123',
                    'username': 'testuser',
                    'password_hash': '$2b$12$hash',
                    'role': 'editor',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            ]
        }
        
        service = UserService(mock_db)
        user = await service.get_user_by_username("testuser")
        
        assert user is not None
        assert user.username == "testuser"
        assert user.user_id == "user-123"
        assert user.role == UserRole.EDITOR
        assert user.password_hash == "$2b$12$hash"
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_found_columnar_format(self):
        """Test get_user_by_username finds user in columnar format"""
        mock_db = Mock()
        mock_db.execute_sql.return_value = {
            'data': {
                'id': ['user-123'],
                'username': ['testuser'],
                'password_hash': ['$2b$12$hash'],
                'role': ['admin'],
                'created': [datetime.now(timezone.utc)],
                'updated': [datetime.now(timezone.utc)]
            }
        }
        
        service = UserService(mock_db)
        user = await service.get_user_by_username("testuser")
        
        assert user is not None
        assert user.username == "testuser"
        assert user.user_id == "user-123"
        assert user.role == UserRole.ADMIN
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self):
        """Test get_user_by_username returns None when user not found"""
        mock_db = Mock()
        mock_db.execute_sql.return_value = {'data': []}
        
        service = UserService(mock_db)
        user = await service.get_user_by_username("nonexistent")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_invalid_role_defaults_to_viewer(self):
        """Test get_user_by_username defaults to VIEWER for invalid role"""
        mock_db = Mock()
        mock_db.execute_sql.return_value = {
            'data': [
                {
                    'id': 'user-123',
                    'username': 'testuser',
                    'password_hash': '$2b$12$hash',
                    'role': 'invalid_role',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            ]
        }
        
        service = UserService(mock_db)
        user = await service.get_user_by_username("testuser")
        
        assert user is not None
        assert user.role == UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_exception_returns_none(self):
        """Test get_user_by_username returns None on exception"""
        mock_db = Mock()
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        service = UserService(mock_db)
        user = await service.get_user_by_username("testuser")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user_password(self):
        """Test update_user_password updates password"""
        mock_db = Mock()
        mock_db.execute_sql = Mock()
        
        service = UserService(mock_db)
        result = await service.update_user_password("testuser", "new_password")
        
        assert result is True
        assert mock_db.execute_sql.called
        
        # Verify SQL contains password hash
        sql = mock_db.execute_sql.call_args[0][0]
        assert "UPDATE users" in sql
        assert "testuser" in sql
        assert "password_hash" in sql
    
    @pytest.mark.asyncio
    async def test_update_user_password_exception_returns_false(self):
        """Test update_user_password returns False on exception"""
        mock_db = Mock()
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        service = UserService(mock_db)
        result = await service.update_user_password("testuser", "new_password")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_user_role(self):
        """Test update_user_role updates role"""
        mock_db = Mock()
        mock_db.execute_sql = Mock()
        
        service = UserService(mock_db)
        result = await service.update_user_role("testuser", UserRole.ADMIN)
        
        assert result is True
        assert mock_db.execute_sql.called
        
        # Verify SQL contains role
        sql = mock_db.execute_sql.call_args[0][0]
        assert "UPDATE users" in sql
        assert "testuser" in sql
        assert "admin" in sql
    
    @pytest.mark.asyncio
    async def test_update_user_role_exception_returns_false(self):
        """Test update_user_role returns False on exception"""
        mock_db = Mock()
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        service = UserService(mock_db)
        result = await service.update_user_role("testuser", UserRole.ADMIN)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_user(self):
        """Test delete_user deletes user"""
        mock_db = Mock()
        mock_db.execute_sql = Mock()
        
        service = UserService(mock_db)
        result = await service.delete_user("testuser")
        
        assert result is True
        assert mock_db.execute_sql.called
        
        # Verify SQL is DELETE
        sql = mock_db.execute_sql.call_args[0][0]
        assert "DELETE FROM users" in sql
        assert "testuser" in sql
    
    @pytest.mark.asyncio
    async def test_delete_user_exception_returns_false(self):
        """Test delete_user returns False on exception"""
        mock_db = Mock()
        mock_db.execute_sql.side_effect = Exception("Database error")
        
        service = UserService(mock_db)
        result = await service.delete_user("testuser")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_users_empty(self):
        """Test list_users returns empty list when no users"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {'data': []}
        mock_db.query.return_value = mock_query
        
        service = UserService(mock_db)
        users = await service.list_users()
        
        assert isinstance(users, list)
        assert len(users) == 0
    
    @pytest.mark.asyncio
    async def test_list_users_row_format(self):
        """Test list_users with row format data"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'id': 'user-1',
                    'username': 'user1',
                    'password_hash': '$2b$12$hash1',
                    'role': 'admin',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                },
                {
                    'id': 'user-2',
                    'username': 'user2',
                    'password_hash': '$2b$12$hash2',
                    'role': 'viewer',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        service = UserService(mock_db)
        users = await service.list_users()
        
        assert len(users) == 2
        assert users[0].username == "user1"
        assert users[0].role == UserRole.ADMIN
        assert users[1].username == "user2"
        assert users[1].role == UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_list_users_columnar_format(self):
        """Test list_users with columnar format data"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': {
                'id': ['user-1', 'user-2'],
                'username': ['user1', 'user2'],
                'password_hash': ['$2b$12$hash1', '$2b$12$hash2'],
                'role': ['editor', 'viewer'],
                'created': [datetime.now(timezone.utc), datetime.now(timezone.utc)],
                'updated': [datetime.now(timezone.utc), datetime.now(timezone.utc)]
            }
        }
        mock_db.query.return_value = mock_query
        
        service = UserService(mock_db)
        users = await service.list_users()
        
        assert len(users) == 2
        assert users[0].username == "user1"
        assert users[0].role == UserRole.EDITOR
        assert users[1].username == "user2"
        assert users[1].role == UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_list_users_invalid_role_defaults_to_viewer(self):
        """Test list_users defaults to VIEWER for invalid roles"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = {
            'data': [
                {
                    'id': 'user-1',
                    'username': 'user1',
                    'password_hash': '$2b$12$hash1',
                    'role': 'invalid',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            ]
        }
        mock_db.query.return_value = mock_query
        
        service = UserService(mock_db)
        users = await service.list_users()
        
        assert len(users) == 1
        assert users[0].role == UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_list_users_exception_returns_empty(self):
        """Test list_users returns empty list on exception"""
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database error")
        
        service = UserService(mock_db)
        users = await service.list_users()
        
        assert isinstance(users, list)
        assert len(users) == 0
    
    @pytest.mark.asyncio
    async def test_verify_user_password_valid(self):
        """Test verify_user_password with valid password"""
        mock_db = Mock()
        password = "test_password"
        hashed = UserService(mock_db).hash_password(password)
        
        mock_db.execute_sql.return_value = {
            'data': [
                {
                    'id': 'user-123',
                    'username': 'testuser',
                    'password_hash': hashed,
                    'role': 'viewer',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            ]
        }
        
        service = UserService(mock_db)
        result = await service.verify_user_password("testuser", password)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_user_password_invalid(self):
        """Test verify_user_password with invalid password"""
        mock_db = Mock()
        password = "test_password"
        hashed = UserService(mock_db).hash_password(password)
        
        mock_db.execute_sql.return_value = {
            'data': [
                {
                    'id': 'user-123',
                    'username': 'testuser',
                    'password_hash': hashed,
                    'role': 'viewer',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            ]
        }
        
        service = UserService(mock_db)
        result = await service.verify_user_password("testuser", "wrong_password")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_user_password_user_not_found(self):
        """Test verify_user_password returns False when user not found"""
        mock_db = Mock()
        mock_db.execute_sql.return_value = {'data': []}
        
        service = UserService(mock_db)
        result = await service.verify_user_password("nonexistent", "password")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_user_password_no_password_hash(self):
        """Test verify_user_password returns False when user has no password hash"""
        mock_db = Mock()
        mock_db.execute_sql.return_value = {
            'data': [
                {
                    'id': 'user-123',
                    'username': 'testuser',
                    'password_hash': None,
                    'role': 'viewer',
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            ]
        }
        
        service = UserService(mock_db)
        result = await service.verify_user_password("testuser", "password")
        
        assert result is False


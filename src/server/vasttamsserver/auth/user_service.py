"""
User service for managing users, passwords, and roles in the database
"""

import logging
import bcrypt
import uuid
from datetime import datetime, timezone
from typing import Optional
from .models import User, UserRole
from ..core.dependencies import get_vast_db

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users in the database"""
    
    def __init__(self, vast_db):
        self.vast_db = vast_db
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Hashing password")
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Password hashed successfully")
        
        return hashed
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            is_valid = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Password verification result: %s", "valid" if is_valid else "invalid")
            return is_valid
        except Exception as e:
            logger.warning("Error during password verification: %s", e)
            return False
    
    async def create_user(self, username: str, password: str, role: UserRole = UserRole.VIEWER) -> User:
        """Create a new user in the database"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Creating user: %s with role: %s", username, role)
        
        user_id = str(uuid.uuid4())
        password_hash = self.hash_password(password)
        now = datetime.now(timezone.utc)
        
        user_data = {
            "id": user_id,
            "username": username,
            "password_hash": password_hash,
            "role": role.value,
            "created": now,
            "updated": now
        }
        
        try:
            self.vast_db.insert_record("users", user_data)
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("User created successfully: %s", username)
            
            return User(
                user_id=user_id,
                username=username,
                password_hash=password_hash,
                role=role,
                created_at=now,
                updated_at=now
            )
        except Exception as e:
            logger.error("Failed to create user %s: %s", username, e)
            raise
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieve a user by username"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Getting user by username: %s", username)
        
        try:
            # Use SQL query instead of lambda-based filtering
            sql = f"SELECT id, username, password_hash, role, created, updated FROM users WHERE username = '{username}'"
            result = self.vast_db.execute_sql(sql)
            
            if result and result.get('data'):
                # Handle both columnar and row-oriented formats
                if isinstance(result['data'], list):
                    rows = result['data']
                elif isinstance(result['data'], dict):
                    # Columnar format - convert to rows
                    cols = result['data']
                    if not cols or not any(cols.values()):
                        return None
                    rows = []
                    for i in range(len(list(cols.values())[0])):
                        row = {k: vals[i] for k, vals in cols.items()}
                        rows.append(row)
                else:
                    return None
                
                if len(rows) > 0:
                    row = rows[0]
                    
                    # Convert role string to UserRole enum
                    role_str = row.get('role', 'viewer')
                    try:
                        role = UserRole(role_str)
                    except ValueError:
                        role = UserRole.VIEWER
                    
                    user = User(
                        user_id=row.get('id'),
                        username=row.get('username'),
                        password_hash=row.get('password_hash'),
                        role=role,
                        created_at=row.get('created'),
                        updated_at=row.get('updated')
                    )
                    
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("User found: %s", username)
                    
                    return user
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("User not found: %s", username)
            
            return None
        except Exception as e:
            logger.error("Error retrieving user %s: %s", username, e)
            return None
    
    async def update_user_password(self, username: str, password: str) -> bool:
        """Update a user's password"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Updating password for user: %s", username)
        
        try:
            password_hash = self.hash_password(password)
            now = datetime.now(timezone.utc)
            
            update_data = {
                "password_hash": password_hash,
                "updated": now
            }
            
            # Use SQL UPDATE
            sql = f"""
            UPDATE users
            SET password_hash = '{password_hash}',
                updated = '{now}'
            WHERE username = '{username}'
            """
            
            self.vast_db.execute_sql(sql)
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Password updated successfully for user: %s", username)
            
            return True
        except Exception as e:
            logger.error("Failed to update password for user %s: %s", username, e)
            return False
    
    async def update_user_role(self, username: str, role: UserRole) -> bool:
        """Update a user's role"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Updating role for user %s to %s", username, role)
        
        try:
            now = datetime.now(timezone.utc)
            
            # Use SQL UPDATE
            sql = f"""
            UPDATE users
            SET role = '{role.value}',
                updated = '{now}'
            WHERE username = '{username}'
            """
            
            self.vast_db.execute_sql(sql)
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Role updated successfully for user: %s", username)
            
            return True
        except Exception as e:
            logger.error("Failed to update role for user %s: %s", username, e)
            return False
    
    async def delete_user(self, username: str) -> bool:
        """Delete a user from the database"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Deleting user: %s", username)
        
        try:
            # Use SQL DELETE
            sql = f"DELETE FROM users WHERE username = '{username}'"
            self.vast_db.execute_sql(sql)
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("User deleted successfully: %s", username)
            
            return True
        except Exception as e:
            logger.error("Failed to delete user %s: %s", username, e)
            return False
    
    async def list_users(self) -> list[User]:
        """List all users"""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Listing all users")
        
        try:
            result = self.vast_db.query("users").select("id, username, password_hash, role, created, updated").execute()
            
            if not result or not result.get('data'):
                return []
            
            # Handle both columnar and row-oriented formats
            if isinstance(result['data'], list):
                rows = result['data']
            elif isinstance(result['data'], dict):
                # Columnar format - convert to rows
                cols = result['data']
                if not cols or not any(cols.values()):
                    return []
                rows = []
                for i in range(len(list(cols.values())[0])):
                    row = {k: vals[i] for k, vals in cols.items()}
                    rows.append(row)
            else:
                return []
            
            users = []
            for row in rows:
                # Convert role string to UserRole enum
                role_str = row.get('role', 'viewer')
                try:
                    role = UserRole(role_str)
                except ValueError:
                    role = UserRole.VIEWER
                
                users.append(User(
                    user_id=row.get('id'),
                    username=row.get('username'),
                    password_hash=row.get('password_hash'),
                    role=role,
                    created_at=row.get('created'),
                    updated_at=row.get('updated')
                ))
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Listed %d users", len(users))
            
            return users
        except Exception as e:
            logger.error("Error listing users: %s", e)
            return []
    
    async def verify_user_password(self, username: str, password: str) -> bool:
        """Verify a user's password"""
        user = await self.get_user_by_username(username)
        if not user or not user.password_hash:
            return False
        
        return self.verify_password(password, user.password_hash)


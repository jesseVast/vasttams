#!/usr/bin/env python3
"""
TAMS User Management CLI

A command-line interface for managing users in the TAMS authentication system.
Supports adding, removing, changing passwords, and suspending users.
"""

import asyncio
import argparse
import sys
import os
import uuid
import bcrypt
from datetime import datetime, timezone
from typing import Optional

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.storage.vast_store import VASTStore
from app.models.models import User, UserCreate, UserUpdate, UserPasswordChange
from app.core.config import get_settings


class UserManager:
    """User management class for CLI operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.store = None
    
    async def initialize(self):
        """Initialize the VAST store connection"""
        try:
            self.store = VASTStore(
                endpoint=self.settings.vast_endpoint,
                access_key=self.settings.vast_access_key,
                secret_key=self.settings.vast_secret_key,
                bucket=self.settings.vast_bucket,
                schema=self.settings.vast_schema,
                s3_endpoint_url=self.settings.s3_endpoint_url,
                s3_access_key_id=self.settings.s3_access_key_id,
                s3_secret_access_key=self.settings.s3_secret_access_key,
                s3_bucket_name=self.settings.s3_bucket_name,
                s3_use_ssl=self.settings.s3_use_ssl
            )
            print("✅ Connected to VAST database")
        except Exception as e:
            print(f"❌ Failed to connect to VAST database: {e}")
            sys.exit(1)
    
    async def close(self):
        """Close the VAST store connection"""
        if self.store:
            await self.store.close()
    
    def hash_password(self, password: str) -> tuple[str, str]:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8'), salt.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    async def add_user(self, username: str, password: str, email: Optional[str] = None, 
                      full_name: Optional[str] = None, is_admin: bool = False) -> bool:
        """Add a new user"""
        try:
            # Check if user already exists
            existing_user = await self.store.get_user_by_username(username)
            if existing_user:
                print(f"❌ User '{username}' already exists")
                return False
            
            # Hash the password
            password_hash, password_salt = self.hash_password(password)
            
            # Create user
            user = User(
                user_id=str(uuid.uuid4()),
                username=username,
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                password_salt=password_salt,
                is_admin=is_admin,
                is_active=True,
                created_by="cli",
                created=datetime.now(timezone.utc),
                updated=datetime.now(timezone.utc)
            )
            
            success = await self.store.create_user(user)
            if success:
                print(f"✅ User '{username}' created successfully")
                print(f"   User ID: {user.user_id}")
                print(f"   Admin: {'Yes' if is_admin else 'No'}")
                return True
            else:
                print(f"❌ Failed to create user '{username}'")
                return False
                
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return False
    
    async def remove_user(self, username: str, hard_delete: bool = False) -> bool:
        """Remove a user"""
        try:
            # Find the user
            user = await self.store.get_user_by_username(username)
            if not user:
                print(f"❌ User '{username}' not found")
                return False
            
            # Delete the user
            success = await self.store.delete_user(
                user.user_id, 
                soft_delete=not hard_delete, 
                deleted_by="cli"
            )
            
            if success:
                delete_type = "hard deleted" if hard_delete else "soft deleted"
                print(f"✅ User '{username}' {delete_type} successfully")
                return True
            else:
                print(f"❌ Failed to delete user '{username}'")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting user: {e}")
            return False
    
    async def change_password(self, username: str, new_password: str) -> bool:
        """Change a user's password"""
        try:
            # Find the user
            user = await self.store.get_user_by_username(username)
            if not user:
                print(f"❌ User '{username}' not found")
                return False
            
            # Hash the new password
            password_hash, password_salt = self.hash_password(new_password)
            
            # Update the user
            user.password_hash = password_hash
            user.password_salt = password_salt
            user.password_changed_at = datetime.now(timezone.utc)
            user.updated_by = "cli"
            user.updated = datetime.now(timezone.utc)
            
            success = await self.store.update_user(user.user_id, user)
            if success:
                print(f"✅ Password changed successfully for user '{username}'")
                return True
            else:
                print(f"❌ Failed to change password for user '{username}'")
                return False
                
        except Exception as e:
            print(f"❌ Error changing password: {e}")
            return False
    
    async def suspend_user(self, username: str, suspend: bool = True) -> bool:
        """Suspend or activate a user"""
        try:
            # Find the user
            user = await self.store.get_user_by_username(username)
            if not user:
                print(f"❌ User '{username}' not found")
                return False
            
            # Update the user status
            user.is_active = not suspend
            user.updated_by = "cli"
            user.updated = datetime.now(timezone.utc)
            
            success = await self.store.update_user(user.user_id, user)
            if success:
                status = "suspended" if suspend else "activated"
                print(f"✅ User '{username}' {status} successfully")
                return True
            else:
                action = "suspend" if suspend else "activate"
                print(f"❌ Failed to {action} user '{username}'")
                return False
                
        except Exception as e:
            print(f"❌ Error updating user status: {e}")
            return False
    
    async def list_users(self, show_inactive: bool = False) -> bool:
        """List all users"""
        try:
            filters = {}
            if not show_inactive:
                filters['is_active'] = True
            
            users = await self.store.list_users(filters=filters)
            
            if not users:
                print("No users found")
                return True
            
            print(f"\n{'Username':<20} {'Email':<30} {'Full Name':<25} {'Admin':<6} {'Status':<8}")
            print("-" * 95)
            
            for user in users:
                status = "Active" if user.is_active else "Inactive"
                admin = "Yes" if user.is_admin else "No"
                email = user.email or ""
                full_name = user.full_name or ""
                
                print(f"{user.username:<20} {email:<30} {full_name:<25} {admin:<6} {status:<8}")
            
            print(f"\nTotal users: {len(users)}")
            return True
            
        except Exception as e:
            print(f"❌ Error listing users: {e}")
            return False
    
    async def show_user(self, username: str) -> bool:
        """Show detailed information about a user"""
        try:
            user = await self.store.get_user_by_username(username)
            if not user:
                print(f"❌ User '{username}' not found")
                return False
            
            print(f"\nUser Details for '{username}':")
            print("-" * 50)
            print(f"User ID:           {user.user_id}")
            print(f"Username:          {user.username}")
            print(f"Email:             {user.email or 'Not set'}")
            print(f"Full Name:         {user.full_name or 'Not set'}")
            print(f"Admin:             {'Yes' if user.is_admin else 'No'}")
            print(f"Active:            {'Yes' if user.is_active else 'No'}")
            print(f"Created:           {user.created}")
            print(f"Last Updated:      {user.updated}")
            print(f"Last Login:        {user.last_login_at or 'Never'}")
            print(f"Failed Logins:     {user.failed_login_attempts}")
            print(f"Locked Until:      {user.locked_until or 'Not locked'}")
            print(f"Created By:        {user.created_by or 'Unknown'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error showing user details: {e}")
            return False


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="TAMS User Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python user_cli.py add admin admin123 --email admin@example.com --admin
  python user_cli.py add user user123 --email user@example.com --full-name "John Doe"
  python user_cli.py list
  python user_cli.py show admin
  python user_cli.py change-password admin newpassword123
  python user_cli.py suspend user
  python user_cli.py activate user
  python user_cli.py remove user
  python user_cli.py remove user --hard
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add user command
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('username', help='Username')
    add_parser.add_argument('password', help='Password')
    add_parser.add_argument('--email', help='Email address')
    add_parser.add_argument('--full-name', help='Full name')
    add_parser.add_argument('--admin', action='store_true', help='Make user an admin')
    
    # Remove user command
    remove_parser = subparsers.add_parser('remove', help='Remove a user')
    remove_parser.add_argument('username', help='Username to remove')
    remove_parser.add_argument('--hard', action='store_true', help='Hard delete (permanent)')
    
    # Change password command
    change_pwd_parser = subparsers.add_parser('change-password', help='Change user password')
    change_pwd_parser.add_argument('username', help='Username')
    change_pwd_parser.add_argument('new_password', help='New password')
    
    # Suspend user command
    suspend_parser = subparsers.add_parser('suspend', help='Suspend a user')
    suspend_parser.add_argument('username', help='Username to suspend')
    
    # Activate user command
    activate_parser = subparsers.add_parser('activate', help='Activate a suspended user')
    activate_parser.add_argument('username', help='Username to activate')
    
    # List users command
    list_parser = subparsers.add_parser('list', help='List all users')
    list_parser.add_argument('--all', action='store_true', help='Show inactive users too')
    
    # Show user command
    show_parser = subparsers.add_parser('show', help='Show user details')
    show_parser.add_argument('username', help='Username to show')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize user manager
    manager = UserManager()
    await manager.initialize()
    
    try:
        if args.command == 'add':
            success = await manager.add_user(
                username=args.username,
                password=args.password,
                email=args.email,
                full_name=args.full_name,
                is_admin=args.admin
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'remove':
            success = await manager.remove_user(
                username=args.username,
                hard_delete=args.hard
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'change-password':
            success = await manager.change_password(
                username=args.username,
                new_password=args.new_password
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'suspend':
            success = await manager.suspend_user(
                username=args.username,
                suspend=True
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'activate':
            success = await manager.suspend_user(
                username=args.username,
                suspend=False
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'list':
            success = await manager.list_users(show_inactive=args.all)
            sys.exit(0 if success else 1)
            
        elif args.command == 'show':
            success = await manager.show_user(username=args.username)
            sys.exit(0 if success else 1)
            
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main()) 
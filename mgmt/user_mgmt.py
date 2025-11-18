#!/usr/bin/env python3
"""
User Management CLI

Manage users, roles, and passwords for TAMS authentication.
"""

import sys
import os
import getpass
import argparse
from pathlib import Path

# Add src to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src" / "server"))

# Change to root directory to load config correctly
# In container, config is at /etc/tams/config.yaml, in dev it's at config/config.yaml
# The Settings class handles this automatically, so we just need to be in the right directory
os.chdir(str(root_dir))

from vasttamsserver.core.dependencies import get_vast_db
from vasttamsserver.auth.user_service import UserService
from vasttamsserver.auth.models import UserRole


async def init_default_users(vast_db):
    """Initialize default users with password 'vastdata'"""
    service = UserService(vast_db)
    
    default_users = [
        ("admin", UserRole.ADMIN),
        ("editor", UserRole.EDITOR),
        ("viewer", UserRole.VIEWER)
    ]
    
    password = "vastdata"
    
    print("Creating default users...")
    for username, role in default_users:
        try:
            # Check if user already exists
            existing = await service.get_user_by_username(username)
            if existing:
                print(f"  User '{username}' already exists, skipping")
                continue
            
            await service.create_user(username, password, role)
            print(f"  Created user '{username}' with role '{role.value}' and password 'vastdata'")
        except Exception as e:
            print(f"  Error creating user '{username}': {e}")
    
    print("Default users initialized successfully")


async def create_user(vast_db, username, role_str, password=None):
    """Create a new user"""
    try:
        role = UserRole(role_str.lower())
    except ValueError:
        print(f"Invalid role: {role_str}. Must be one of: admin, editor, viewer")
        return
    
    if password is None:
        password = getpass.getpass("Enter password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match")
            return
    
    service = UserService(vast_db)
    
    try:
        await service.create_user(username, password, role)
        print(f"User '{username}' created successfully with role '{role.value}'")
    except Exception as e:
        print(f"Error creating user: {e}")


async def delete_user(vast_db, username):
    """Delete a user"""
    service = UserService(vast_db)
    
    try:
        success = await service.delete_user(username)
        if success:
            print(f"User '{username}' deleted successfully")
        else:
            print(f"Failed to delete user '{username}'")
    except Exception as e:
        print(f"Error deleting user: {e}")


async def update_password(vast_db, username):
    """Update a user's password"""
    service = UserService(vast_db)
    
    password = getpass.getpass("Enter new password: ")
    confirm = getpass.getpass("Confirm new password: ")
    if password != confirm:
        print("Passwords do not match")
        return
    
    try:
        success = await service.update_user_password(username, password)
        if success:
            print(f"Password updated successfully for user '{username}'")
        else:
            print(f"Failed to update password for user '{username}'")
    except Exception as e:
        print(f"Error updating password: {e}")


async def update_role(vast_db, username, role_str):
    """Update a user's role"""
    try:
        role = UserRole(role_str.lower())
    except ValueError:
        print(f"Invalid role: {role_str}. Must be one of: admin, editor, viewer")
        return
    
    service = UserService(vast_db)
    
    try:
        success = await service.update_user_role(username, role)
        if success:
            print(f"Role updated to '{role.value}' for user '{username}'")
        else:
            print(f"Failed to update role for user '{username}'")
    except Exception as e:
        print(f"Error updating role: {e}")


async def list_users(vast_db):
    """List all users"""
    service = UserService(vast_db)
    
    try:
        users = await service.list_users()
        if not users:
            print("No users found")
            return
        
        print(f"\n{'Username':<15} {'Role':<15} {'Created':<20}")
        print("-" * 50)
        for user in users:
            created = user.created_at.isoformat() if user.created_at else "N/A"
            print(f"{user.username:<15} {user.role.value:<15} {created:<20}")
        print()
    except Exception as e:
        print(f"Error listing users: {e}")


async def main():
    parser = argparse.ArgumentParser(description="TAMS User Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Init default users command
    init_parser = subparsers.add_parser("init-default-users", help="Create admin, editor, viewer users with password 'vastdata'")
    
    # Create user command
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("username", help="Username")
    create_parser.add_argument("role", help="Role (admin, editor, viewer)")
    create_parser.add_argument("--password", help="Password (will prompt if not provided)")
    
    # Delete user command
    delete_parser = subparsers.add_parser("delete", help="Delete a user")
    delete_parser.add_argument("username", help="Username")
    
    # Update password command
    update_password_parser = subparsers.add_parser("update-password", help="Update a user's password")
    update_password_parser.add_argument("username", help="Username")
    
    # Update role command
    update_role_parser = subparsers.add_parser("update-role", help="Update a user's role")
    update_role_parser.add_argument("username", help="Username")
    update_role_parser.add_argument("role", help="New role (admin, editor, viewer)")
    
    # List users command
    list_parser = subparsers.add_parser("list", help="List all users")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Get VAST database connection
    vast_db = get_vast_db()
    
    # Execute command
    if args.command == "init-default-users":
        await init_default_users(vast_db)
    elif args.command == "create":
        await create_user(vast_db, args.username, args.role, args.password)
    elif args.command == "delete":
        await delete_user(vast_db, args.username)
    elif args.command == "update-password":
        await update_password(vast_db, args.username)
    elif args.command == "update-role":
        await update_role(vast_db, args.username, args.role)
    elif args.command == "list":
        await list_users(vast_db)
    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


"""
MedClaim — User Management Service

Handles user CRUD operations, role assignment, and profile management.
Admin-only access for user creation and modification.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from supabase import Client

from backend.db.client import get_supabase_client

logger = structlog.get_logger("medclaim.user_service")


async def create_user(
    email: str,
    password: str,
    full_name: str,
    role: str,
    department: str | None = None,
    created_by: str | None = None
) -> dict[str, Any]:
    """
    Create a new user in Supabase Auth and user_profiles table.
    
    This function should only be called by admins.
    """
    client = get_supabase_client()
    
    try:
        # Create user in Supabase Auth
        auth_response = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email for admin-created users
        })
        
        if not auth_response.user:
            raise RuntimeError("Failed to create user in Supabase Auth")
        
        user_id = auth_response.user.id
        
        # Create user profile
        profile_data = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "department": department,
        }
        
        profile_response = client.table("user_profiles").insert(profile_data).execute()
        
        if not profile_response.data:
            # Rollback: delete auth user if profile creation fails
            client.auth.admin.delete_user(user_id)
            raise RuntimeError("Failed to create user profile")
        
        logger.info("user.created | user_id=%s email=%s role=%s created_by=%s", 
                    user_id, email, role, created_by)
        
        return profile_response.data[0]
        
    except Exception as e:
        logger.error("user.create_failed | email=%s error=%s", email, str(e))
        raise


async def get_user(user_id: str) -> dict[str, Any] | None:
    """Fetch user profile by ID."""
    client = get_supabase_client()
    
    try:
        result = client.table("user_profiles").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("user.get_failed | user_id=%s error=%s", user_id, str(e))
        raise


async def list_users(
    role: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[dict[str, Any]]:
    """List all users with optional role filter."""
    client = get_supabase_client()
    
    try:
        query = client.table("user_profiles").select("*")
        
        if role:
            query = query.eq("role", role)
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        return result.data or []
    except Exception as e:
        logger.error("user.list_failed | error=%s", str(e))
        raise


async def update_user(
    user_id: str,
    full_name: str | None = None,
    role: str | None = None,
    department: str | None = None,
    updated_by: str | None = None
) -> dict[str, Any]:
    """Update user profile."""
    client = get_supabase_client()
    
    try:
        update_data: dict[str, Any] = {}
        
        if full_name is not None:
            update_data["full_name"] = full_name
        if role is not None:
            update_data["role"] = role
        if department is not None:
            update_data["department"] = department
        
        if not update_data:
            raise ValueError("No fields to update")
        
        result = client.table("user_profiles").update(update_data).eq("id", user_id).execute()
        
        if not result.data:
            raise RuntimeError("Failed to update user")
        
        logger.info("user.updated | user_id=%s updated_by=%s changes=%s", 
                    user_id, updated_by, list(update_data.keys()))
        
        return result.data[0]
        
    except Exception as e:
        logger.error("user.update_failed | user_id=%s error=%s", user_id, str(e))
        raise


async def delete_user(user_id: str, deleted_by: str | None = None) -> None:
    """
    Delete user from both Supabase Auth and user_profiles table.
    This is a destructive operation.
    """
    client = get_supabase_client()
    
    try:
        # Delete from user_profiles (will cascade due to FK)
        client.table("user_profiles").delete().eq("id", user_id).execute()
        
        # Delete from Supabase Auth
        client.auth.admin.delete_user(user_id)
        
        logger.info("user.deleted | user_id=%s deleted_by=%s", user_id, deleted_by)
        
    except Exception as e:
        logger.error("user.delete_failed | user_id=%s error=%s", user_id, str(e))
        raise


async def invite_user(
    email: str,
    role: str,
    full_name: str,
    department: str | None = None,
    invited_by: str | None = None
) -> dict[str, Any]:
    """
    Invite a new user by email. Creates user with temporary password.
    In production, this would send an email with set password link.
    """
    import secrets
    import string
    
    # Generate temporary password
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    
    # Create user with temporary password
    user = await create_user(
        email=email,
        password=temp_password,
        full_name=full_name,
        role=role,
        department=department,
        created_by=invited_by
    )
    
    logger.info("user.invited | user_id=%s email=%s invited_by=%s", 
                user["id"], email, invited_by)
    
    # In production, send email with temp password and reset link
    # For now, return temp_password for testing
    return {**user, "temp_password": temp_password}

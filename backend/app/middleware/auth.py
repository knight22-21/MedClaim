"""
MedClaim — Authentication Middleware

Implements Supabase JWT validation and role-based access control.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from backend.app.config import settings

logger = structlog.get_logger("medclaim.auth")

security = HTTPBearer(auto_error=False)


def get_supabase_client() -> Client:
    """Get Supabase client for auth operations."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    """
    Validate JWT token and return current user.

    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    if credentials is None:
        return None

    try:
        supabase = get_supabase_client()
        token = credentials.credentials

        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        # Get user profile with role
        user_id = user_response.user.id
        profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()

        if not profile_response.data:
            logger.warning("auth.user_profile_not_found | user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User profile not found"
            )

        profile = profile_response.data[0]

        return {
            "id": str(profile["id"]),
            "email": profile["email"],
            "full_name": profile.get("full_name"),
            "role": profile["role"],
            "department": profile.get("department"),
        }

    except Exception as e:
        logger.error("auth.validation_failed | error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials"
        )


async def require_auth(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """
    Require authentication. Returns user data.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return current_user


def require_role(allowed_roles: list[str]):
    """
    Dependency factory for role-based access control.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_role(["admin"]))])
    """

    async def role_checker(current_user: dict[str, Any] = Depends(require_auth)) -> dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user['role']} not authorized. Required: {allowed_roles}",
            )
        return current_user

    return role_checker


async def require_admin(current_user: dict[str, Any] = Depends(require_auth)) -> dict[str, Any]:
    """Require admin role."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user


async def require_billing_specialist_or_admin(
    current_user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Require billing specialist or admin role."""
    if current_user["role"] not in ["billing_specialist", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing specialist or admin role required",
        )
    return current_user

"""
MedClaim — Authentication Router

Handles login, logout, and user profile endpoints using Supabase Auth.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from backend.app.middleware.auth import (
    get_supabase_client,
    require_auth,
)
from backend.app.models.responses import APIResponse

logger = structlog.get_logger("medclaim.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict[str, Any]


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    department: str | None


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(request: LoginRequest) -> APIResponse[LoginResponse]:
    """
    Authenticate user with email/password using Supabase Auth.
    Returns access token and user profile.
    """
    try:
        supabase = get_supabase_client()

        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        # Get user profile with role
        user_id = auth_response.user.id
        profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()

        # Auto-create profile if not found
        if not profile_response.data:
            logger.info(
                "auth.login.profile_not_found | user_id=%s | auto_creating_profile", user_id
            )

            # Create default profile
            new_profile = {
                "id": user_id,
                "email": auth_response.user.email,
                "full_name": auth_response.user.user_metadata.get("full_name")
                or auth_response.user.email.split("@")[0],
                "role": "viewer",  # Default role
                "department": None,
            }

            supabase.table("user_profiles").insert(new_profile).execute()

            # Fetch the newly created profile
            profile_response = (
                supabase.table("user_profiles").select("*").eq("id", user_id).execute()
            )

            if not profile_response.data:
                logger.error("auth.login.profile_creation_failed | user_id=%s", user_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user profile",
                )

        profile = profile_response.data[0]

        user_data = {
            "id": str(profile["id"]),
            "email": profile["email"],
            "full_name": profile.get("full_name"),
            "role": profile["role"],
            "department": profile.get("department"),
        }

        logger.info(
            "auth.login.success | user_id=%s email=%s role=%s",
            user_id,
            request.email,
            profile["role"],
        )

        return APIResponse(
            success=True,
            data=LoginResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                user=user_data,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("auth.login.failed | email=%s error=%s", request.email, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication failed"
        )


@router.post("/logout")
async def logout(current_user: dict[str, Any] = Depends(require_auth)) -> APIResponse[dict]:
    """
    Logout current user by invalidating session.
    """
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()

        logger.info("auth.logout.success | user_id=%s", current_user["id"])

        return APIResponse(success=True, data={"message": "Logged out successfully"})

    except Exception as e:
        logger.error("auth.logout.failed | user_id=%s error=%s", current_user["id"], str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.get("/me", response_model=APIResponse[UserProfile])
async def get_current_user_profile(
    current_user: dict[str, Any] = Depends(require_auth),
) -> APIResponse[UserProfile]:
    """
    Get current user profile.
    """
    return APIResponse(success=True, data=UserProfile(**current_user))


@router.post("/refresh")
async def refresh_token(refresh_token: str) -> APIResponse[LoginResponse]:
    """
    Refresh access token using refresh token.
    """
    try:
        supabase = get_supabase_client()

        # Refresh session
        auth_response = supabase.auth.refresh_session(refresh_token)

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Get user profile
        user_id = auth_response.user.id
        profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()

        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User profile not found"
            )

        profile = profile_response.data[0]

        user_data = {
            "id": str(profile["id"]),
            "email": profile["email"],
            "full_name": profile.get("full_name"),
            "role": profile["role"],
            "department": profile.get("department"),
        }

        logger.info("auth.refresh.success | user_id=%s", user_id)

        return APIResponse(
            success=True,
            data=LoginResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                user=user_data,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("auth.refresh.failed | error=%s", str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed")

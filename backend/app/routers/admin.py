"""
MedClaim — Admin Router

Handles admin-only endpoints for user management, workflow configuration,
blog management, and lead management.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from backend.app.middleware.auth import require_admin
from backend.app.models.responses import APIResponse
from backend.app.services.user_service import (
    create_user,
    delete_user,
    get_user,
    invite_user,
    list_users,
    update_user,
)

logger = structlog.get_logger("medclaim.admin")

router = APIRouter(prefix="/admin", tags=["Admin"])


# Request/Response Models
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str
    department: str | None = None


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = None
    department: str | None = None


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    department: str | None = None


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    department: str | None
    created_at: str


# User Management Endpoints
@router.get("/users", response_model=APIResponse[list[UserProfileResponse]])
async def get_all_users(
    role: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[list[UserProfileResponse]]:
    """List all users with optional role filter (admin only)."""
    try:
        users = await list_users(role=role, limit=limit, offset=offset)
        return APIResponse(success=True, data=users)
    except Exception as e:
        logger.error("admin.users.list_failed | error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.get("/users/{user_id}", response_model=APIResponse[UserProfileResponse])
async def get_user_by_id(
    user_id: str,
    current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[UserProfileResponse]:
    """Get user by ID (admin only)."""
    try:
        user = await get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return APIResponse(success=True, data=user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin.users.get_failed | user_id=%s error=%s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.post("/users", response_model=APIResponse[UserProfileResponse])
async def create_new_user(
    request: CreateUserRequest,
    current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[UserProfileResponse]:
    """Create a new user (admin only)."""
    try:
        user = await create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=request.role,
            department=request.department,
            created_by=current_user["id"]
        )
        return APIResponse(success=True, data=user)
    except Exception as e:
        logger.error("admin.users.create_failed | email=%s error=%s", request.email, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.put("/users/{user_id}", response_model=APIResponse[UserProfileResponse])
async def update_user_by_id(
    user_id: str,
    request: UpdateUserRequest,
    current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[UserProfileResponse]:
    """Update user (admin only)."""
    try:
        user = await update_user(
            user_id=user_id,
            full_name=request.full_name,
            role=request.role,
            department=request.department,
            updated_by=current_user["id"]
        )
        return APIResponse(success=True, data=user)
    except Exception as e:
        logger.error("admin.users.update_failed | user_id=%s error=%s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/users/{user_id}")
async def delete_user_by_id(
    user_id: str,
    current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[dict]:
    """Delete user (admin only)."""
    try:
        await delete_user(user_id=user_id, deleted_by=current_user["id"])
        return APIResponse(success=True, data={"message": "User deleted successfully"})
    except Exception as e:
        logger.error("admin.users.delete_failed | user_id=%s error=%s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.post("/users/invite", response_model=APIResponse[dict])
async def invite_new_user(
    request: InviteUserRequest,
    current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[dict]:
    """Invite a new user via email (admin only)."""
    try:
        result = await invite_user(
            email=request.email,
            full_name=request.full_name,
            role=request.role,
            department=request.department,
            invited_by=current_user["id"]
        )
        # Don't return temp_password in production
        return APIResponse(
            success=True,
            data={
                "user_id": result["id"],
                "email": result["email"],
                "message": "User invited successfully"
            }
        )
    except Exception as e:
        logger.error("admin.users.invite_failed | email=%s error=%s", request.email, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invite user"
        )

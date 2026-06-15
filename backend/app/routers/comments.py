"""
MedClaim — Comments Router

Handles comment CRUD operations for claims.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.middleware.auth import require_auth
from backend.app.models.responses import APIResponse
from backend.app.services.comment_service import (
    create_comment,
    delete_comment,
    get_claim_comments,
    update_comment,
)

logger = structlog.get_logger("medclaim.comments")

router = APIRouter(prefix="/comments", tags=["Comments"])


# Request/Response Models
class CreateCommentRequest(BaseModel):
    claim_id: str
    content: str
    parent_id: str | None = None


class UpdateCommentRequest(BaseModel):
    content: str


@router.post("", response_model=APIResponse[dict[str, Any]])
async def create_new_comment(
    request: CreateCommentRequest, current_user: dict[str, Any] = Depends(require_auth)
) -> APIResponse[dict[str, Any]]:
    """Create a new comment on a claim."""
    try:
        comment = await create_comment(
            claim_id=request.claim_id,
            user_id=current_user["id"],
            content=request.content,
            parent_id=request.parent_id,
        )
        return APIResponse(success=True, data=comment)
    except Exception as e:
        logger.error("comments.create_failed | claim_id=%s error=%s", request.claim_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create comment"
        )


@router.get("/claims/{claim_id}", response_model=APIResponse[list[dict[str, Any]]])
async def get_comments_for_claim(
    claim_id: str, current_user: dict[str, Any] = Depends(require_auth)
) -> APIResponse[list[dict[str, Any]]]:
    """Get all comments for a claim (threaded)."""
    try:
        comments = await get_claim_comments(claim_id=claim_id, include_deleted=False)
        return APIResponse(success=True, data=comments)
    except Exception as e:
        logger.error("comments.list_failed | claim_id=%s error=%s", claim_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get comments"
        )


@router.put("/{comment_id}", response_model=APIResponse[dict[str, Any]])
async def update_comment_by_id(
    comment_id: str,
    request: UpdateCommentRequest,
    current_user: dict[str, Any] = Depends(require_auth),
) -> APIResponse[dict[str, Any]]:
    """Update comment content."""
    try:
        comment = await update_comment(
            comment_id=comment_id, content=request.content, user_id=current_user["id"]
        )
        return APIResponse(success=True, data=comment)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this comment",
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    except Exception as e:
        logger.error("comments.update_failed | comment_id=%s error=%s", comment_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update comment"
        )


@router.delete("/{comment_id}")
async def delete_comment_by_id(
    comment_id: str, current_user: dict[str, Any] = Depends(require_auth)
) -> APIResponse[dict]:
    """Soft delete a comment."""
    try:
        await delete_comment(comment_id=comment_id, user_id=current_user["id"])
        return APIResponse(success=True, data={"message": "Comment deleted successfully"})
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this comment",
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    except Exception as e:
        logger.error("comments.delete_failed | comment_id=%s error=%s", comment_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete comment"
        )

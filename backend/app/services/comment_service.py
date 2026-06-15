"""
MedClaim — Comments Service

Handles threaded comments on claims with soft delete support.
"""

from __future__ import annotations

from typing import Any

import structlog

from backend.db.client import get_supabase_client

logger = structlog.get_logger("medclaim.comment_service")


async def create_comment(
    claim_id: str, user_id: str, content: str, parent_id: str | None = None
) -> dict[str, Any]:
    """Create a new comment on a claim."""
    client = get_supabase_client()

    try:
        comment_data = {
            "claim_id": claim_id,
            "user_id": user_id,
            "content": content,
            "parent_id": parent_id,
        }

        result = client.table("comments").insert(comment_data).execute()

        if not result.data:
            raise RuntimeError("Failed to create comment")

        logger.info(
            "comment.created | comment_id=%s claim_id=%s user_id=%s parent_id=%s",
            result.data[0]["id"],
            claim_id,
            user_id,
            parent_id,
        )

        return result.data[0]

    except Exception as e:
        logger.error(
            "comment.create_failed | claim_id=%s user_id=%s error=%s", claim_id, user_id, str(e)
        )
        raise


async def get_comment(comment_id: str) -> dict[str, Any] | None:
    """Get comment by ID."""
    client = get_supabase_client()

    try:
        result = client.table("comments").select("*").eq("id", comment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("comment.get_failed | comment_id=%s error=%s", comment_id, str(e))
        raise


async def get_claim_comments(claim_id: str, include_deleted: bool = False) -> list[dict[str, Any]]:
    """Get all comments for a claim, threaded."""
    client = get_supabase_client()

    try:
        query = client.table("comments").select("*").eq("claim_id", claim_id)

        if not include_deleted:
            query = query.eq("is_deleted", False)

        query = query.order("created_at", desc=True)
        result = query.execute()

        comments = result.data or []

        # Build threaded structure
        comment_map = {c["id"]: c for c in comments}
        threaded = []

        for comment in comments:
            comment["replies"] = []
            if comment["parent_id"] is None:
                threaded.append(comment)
            elif comment["parent_id"] in comment_map:
                comment_map[comment["parent_id"]]["replies"].append(comment)

        return threaded

    except Exception as e:
        logger.error("comment.list_failed | claim_id=%s error=%s", claim_id, str(e))
        raise


async def update_comment(comment_id: str, content: str, user_id: str) -> dict[str, Any]:
    """Update comment content."""
    client = get_supabase_client()

    try:
        # Verify ownership
        comment = await get_comment(comment_id)
        if not comment:
            raise ValueError("Comment not found")

        if comment["user_id"] != user_id:
            raise PermissionError("User does not own this comment")

        result = (
            client.table("comments").update({"content": content}).eq("id", comment_id).execute()
        )

        if not result.data:
            raise RuntimeError("Failed to update comment")

        logger.info("comment.updated | comment_id=%s user_id=%s", comment_id, user_id)

        return result.data[0]

    except Exception as e:
        logger.error("comment.update_failed | comment_id=%s error=%s", comment_id, str(e))
        raise


async def delete_comment(comment_id: str, user_id: str) -> None:
    """Soft delete a comment."""
    client = get_supabase_client()

    try:
        # Verify ownership
        comment = await get_comment(comment_id)
        if not comment:
            raise ValueError("Comment not found")

        if comment["user_id"] != user_id:
            raise PermissionError("User does not own this comment")

        client.table("comments").update({"is_deleted": True}).eq("id", comment_id).execute()

        logger.info("comment.deleted | comment_id=%s user_id=%s", comment_id, user_id)

    except Exception as e:
        logger.error("comment.delete_failed | comment_id=%s error=%s", comment_id, str(e))
        raise

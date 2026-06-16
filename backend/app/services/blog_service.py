"""
MedClaim — Blog Service

Handles blog post management for public website.
"""

from __future__ import annotations

from typing import Any

import structlog

from backend.db.client import get_supabase_client

logger = structlog.get_logger("medclaim.blog_service")


async def create_blog_post(
    title: str,
    slug: str,
    content: str,
    author_id: str,
    excerpt: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new blog post."""
    client = get_supabase_client()

    try:
        post_data = {
            "title": title,
            "slug": slug,
            "excerpt": excerpt,
            "content": content,
            "author_id": author_id,
            "category": category,
            "tags": tags or [],
            "published": False,
        }

        result = client.table("blog_posts").insert(post_data).execute()

        if not result.data:
            raise RuntimeError("Failed to create blog post")

        logger.info(
            "blog.post.created | post_id=%s slug=%s author_id=%s",
            result.data[0]["id"],
            slug,
            author_id,
        )

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("blog.post.create_failed | slug=%s error=%s", slug, str(e))
        raise


async def get_blog_post(slug: str, published_only: bool = False) -> dict[str, Any] | None:
    """Get blog post by slug."""
    client = get_supabase_client()

    try:
        query = client.table("blog_posts").select("*").eq("slug", slug)

        if published_only:
            query = query.eq("published", True)

        result = query.execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("blog.post.get_failed | slug=%s error=%s", slug, str(e))
        raise


async def get_blog_posts(
    published_only: bool = False, category: str | None = None, limit: int = 20, offset: int = 0
) -> list[dict[str, Any]]:
    """List blog posts with optional filters."""
    client = get_supabase_client()

    try:
        query = client.table("blog_posts").select("*")

        if published_only:
            query = query.eq("published", True)
        if category:
            query = query.eq("category", category)

        query = query.order("published_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        return result.data or []
    except Exception as e:
        logger.error("blog.post.list_failed | error=%s", str(e))
        raise


async def update_blog_post(
    post_id: str,
    title: str | None = None,
    slug: str | None = None,
    content: str | None = None,
    excerpt: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    published: bool | None = None,
) -> dict[str, Any]:
    """Update blog post."""
    client = get_supabase_client()

    try:
        update_data: dict[str, Any] = {}

        if title is not None:
            update_data["title"] = title
        if slug is not None:
            update_data["slug"] = slug
        if content is not None:
            update_data["content"] = content
        if excerpt is not None:
            update_data["excerpt"] = excerpt
        if category is not None:
            update_data["category"] = category
        if tags is not None:
            update_data["tags"] = tags
        if published is not None:
            update_data["published"] = published
            if published and update_data.get("published_at") is None:
                from datetime import datetime

                update_data["published_at"] = datetime.utcnow().isoformat()

        if not update_data:
            raise ValueError("No fields to update")

        result = client.table("blog_posts").update(update_data).eq("id", post_id).execute()

        if not result.data:
            raise RuntimeError("Failed to update blog post")

        logger.info("blog.post.updated | post_id=%s", post_id)

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("blog.post.update_failed | post_id=%s error=%s", post_id, str(e))
        raise


async def delete_blog_post(post_id: str) -> None:
    """Delete blog post."""
    client = get_supabase_client()

    try:
        client.table("blog_posts").delete().eq("id", post_id).execute()
        logger.info("blog.post.deleted | post_id=%s", post_id)
    except Exception as e:
        logger.error("blog.post.delete_failed | post_id=%s error=%s", post_id, str(e))
        raise

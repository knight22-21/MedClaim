"""
MedClaim — Public Website Router

Handles public-facing endpoints for blog, documentation, and lead capture.
No authentication required.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from backend.app.models.responses import APIResponse
from backend.app.services.blog_service import get_blog_post, get_blog_posts
from backend.app.services.lead_service import create_lead

logger = structlog.get_logger("medclaim.public")

router = APIRouter(prefix="/public", tags=["Public Website"])


# Request/Response Models
class DemoRequestRequest(BaseModel):
    name: str
    email: EmailStr
    company: str | None = None
    phone: str | None = None
    message: str | None = None


class ContactRequestRequest(BaseModel):
    name: str
    email: EmailStr
    company: str | None = None
    phone: str | None = None
    message: str


# Blog Endpoints
@router.get("/blog", response_model=APIResponse[list[dict[str, Any]]])
async def get_published_blog_posts(
    category: str | None = None,
    limit: int = 20,
    offset: int = 0
) -> APIResponse[list[dict[str, Any]]]:
    """Get all published blog posts (public)."""
    try:
        posts = await get_blog_posts(
            published_only=True,
            category=category,
            limit=limit,
            offset=offset
        )
        return APIResponse(success=True, data=posts)
    except Exception as e:
        logger.error("public.blog.list_failed | error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get blog posts"
        )


@router.get("/blog/{slug}", response_model=APIResponse[dict[str, Any]])
async def get_blog_post_by_slug(slug: str) -> APIResponse[dict[str, Any]]:
    """Get a published blog post by slug (public)."""
    try:
        post = await get_blog_post(slug=slug, published_only=True)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found"
            )
        return APIResponse(success=True, data=post)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("public.blog.get_failed | slug=%s error=%s", slug, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get blog post"
        )


# Lead Capture Endpoints
@router.post("/lead/demo", response_model=APIResponse[dict])
async def submit_demo_request(request: DemoRequestRequest) -> APIResponse[dict]:
    """Submit a demo request (public)."""
    try:
        lead_id = await create_lead(
            lead_type="demo_request",
            name=request.name,
            email=request.email,
            company=request.company,
            phone=request.phone,
            message=request.message
        )
        return APIResponse(
            success=True,
            data={"message": "Demo request submitted successfully", "lead_id": lead_id}
        )
    except Exception as e:
        logger.error("public.lead.demo_failed | email=%s error=%s", request.email, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit demo request"
        )


@router.post("/lead/contact", response_model=APIResponse[dict])
async def submit_contact_request(request: ContactRequestRequest) -> APIResponse[dict]:
    """Submit a contact form (public)."""
    try:
        lead_id = await create_lead(
            lead_type="contact",
            name=request.name,
            email=request.email,
            company=request.company,
            phone=request.phone,
            message=request.message
        )
        return APIResponse(
            success=True,
            data={"message": "Contact form submitted successfully", "lead_id": lead_id}
        )
    except Exception as e:
        logger.error("public.lead.contact_failed | email=%s error=%s", request.email, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit contact form"
        )

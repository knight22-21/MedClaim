"""
MedClaim — Lead Capture Service

Handles lead capture from public website (demo requests, contact forms).
"""

from __future__ import annotations

from typing import Any

import structlog

from backend.db.client import get_supabase_client

logger = structlog.get_logger("medclaim.lead_service")


async def create_lead(
    lead_type: str,
    name: str,
    email: str,
    company: str | None = None,
    phone: str | None = None,
    message: str | None = None,
) -> str:
    """Create a new lead from public website."""
    client = get_supabase_client()

    try:
        lead_data = {
            "type": lead_type,
            "name": name,
            "email": email,
            "company": company,
            "phone": phone,
            "message": message,
            "status": "new",
        }

        result = client.table("lead_captures").insert(lead_data).execute()

        if not result.data:
            raise RuntimeError("Failed to create lead")

        lead_id = result.data[0]["id"]

        logger.info("lead.created | lead_id=%s type=%s email=%s", lead_id, lead_type, email)

        return str(lead_id)

    except Exception as e:
        logger.error("lead.create_failed | email=%s error=%s", email, str(e))
        raise


async def get_lead(lead_id: str) -> dict[str, Any] | None:
    """Get lead by ID."""
    client = get_supabase_client()

    try:
        result = client.table("lead_captures").select("*").eq("id", lead_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("lead.get_failed | lead_id=%s error=%s", lead_id, str(e))
        raise


async def list_leads(
    lead_type: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    """List all leads with optional filters."""
    client = get_supabase_client()

    try:
        query = client.table("lead_captures").select("*")

        if lead_type:
            query = query.eq("type", lead_type)
        if status:
            query = query.eq("status", status)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        return result.data or []
    except Exception as e:
        logger.error("lead.list_failed | error=%s", str(e))
        raise


async def update_lead_status(lead_id: str, status: str) -> dict[str, Any]:
    """Update lead status."""
    client = get_supabase_client()

    try:
        result = (
            client.table("lead_captures").update({"status": status}).eq("id", lead_id).execute()
        )

        if not result.data:
            raise RuntimeError("Failed to update lead")

        logger.info("lead.status_updated | lead_id=%s new_status=%s", lead_id, status)

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("lead.update_failed | lead_id=%s error=%s", lead_id, str(e))
        raise

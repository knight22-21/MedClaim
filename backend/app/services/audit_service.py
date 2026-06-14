"""
MedClaim — Audit Logging Service

Comprehensive audit trail for all system actions.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from supabase import Client

from backend.db.client import get_supabase_client

logger = structlog.get_logger("medclaim.audit_service")


async def log_audit_event(
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None
) -> str:
    """Log an audit event."""
    client = get_supabase_client()
    
    try:
        audit_data = {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        
        result = client.table("audit_logs").insert(audit_data).execute()
        
        if not result.data:
            raise RuntimeError("Failed to log audit event")
        
        audit_id = result.data[0]["id"]
        
        logger.info("audit.logged | audit_id=%s action=%s resource_type=%s resource_id=%s user_id=%s",
                    audit_id, action, resource_type, resource_id, user_id)
        
        return str(audit_id)
        
    except Exception as e:
        logger.error("audit.log_failed | action=%s error=%s", action, str(e))
        raise


async def get_audit_logs(
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[dict[str, Any]]:
    """Get audit logs with optional filters."""
    client = get_supabase_client()
    
    try:
        query = client.table("audit_logs").select("*")
        
        if user_id:
            query = query.eq("user_id", user_id)
        if resource_type:
            query = query.eq("resource_type", resource_type)
        if resource_id:
            query = query.eq("resource_id", resource_id)
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        return result.data or []
    except Exception as e:
        logger.error("audit.logs.get_failed | error=%s", str(e))
        raise


async def get_audit_log(audit_id: str) -> dict[str, Any] | None:
    """Get audit log by ID."""
    client = get_supabase_client()
    
    try:
        result = client.table("audit_logs").select("*").eq("id", audit_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("audit.log.get_failed | audit_id=%s error=%s", audit_id, str(e))
        raise

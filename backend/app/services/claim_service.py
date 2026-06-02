"""
MedClaim — Claim Service

CRUD operations for claims via Supabase. Used by the claims router
and the agent pipeline to read/write claim state.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from backend.app.models.claim import ClaimCreate, ClaimResponse, ClaimStatus
from backend.db.client import get_supabase_client

logger = logging.getLogger("medclaim.services.claim")


def _row_to_response(row: dict[str, Any]) -> ClaimResponse:
    """Convert a Supabase row dict to a ClaimResponse model."""
    return ClaimResponse(
        id=row["id"],
        patient_name=row["patient_name"],
        patient_dob=row["patient_dob"],
        payer_name=row["payer_name"],
        payer_id=row["payer_id"],
        date_of_service=row["date_of_service"],
        facility_type=row["facility_type"],
        diagnosis_codes=row.get("diagnosis_codes", []),
        procedure_codes=row.get("procedure_codes", []),
        billed_amount=float(row["billed_amount"]),
        status=row["status"],
        market=row.get("market", "US"),
        assigned_user_id=row.get("assigned_user_id"),
        human_review_flag=row.get("human_review_flag", False),
        human_review_reason=row.get("human_review_reason"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


async def create_claim(claim: ClaimCreate) -> ClaimResponse:
    """Insert a new claim into Supabase and return the created record."""
    client = get_supabase_client()

    payload = {
        "patient_name": claim.patient_name,
        "patient_dob": claim.patient_dob.isoformat(),
        "payer_name": claim.payer_name,
        "payer_id": claim.payer_id,
        "date_of_service": claim.date_of_service.isoformat(),
        "facility_type": claim.facility_type.value,
        "diagnosis_codes": [dc.model_dump() for dc in claim.diagnosis_codes],
        "procedure_codes": [pc.model_dump() for pc in claim.procedure_codes],
        "billed_amount": claim.billed_amount,
        "status": ClaimStatus.RECEIVED.value,
        "market": claim.market.value,
        "assigned_user_id": claim.assigned_user_id,
    }

    result = client.table("claims").insert(payload).execute()

    if not result.data:
        raise RuntimeError("Failed to insert claim into database")

    row = result.data[0]
    logger.info("claim.created | claim_id=%s payer=%s", row["id"], claim.payer_name)
    return _row_to_response(row)


async def get_claim(claim_id: str) -> ClaimResponse | None:
    """Fetch a single claim by UUID."""
    client = get_supabase_client()
    result = client.table("claims").select("*").eq("id", claim_id).execute()

    if not result.data:
        return None
    return _row_to_response(result.data[0])


async def list_claims(
    status: str | None = None,
    payer: str | None = None,
    market: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ClaimResponse], int]:
    """
    List claims with optional filtering and pagination.

    Returns:
        Tuple of (claim list, total count).
    """
    client = get_supabase_client()
    query = client.table("claims").select("*", count="exact")

    if status:
        query = query.eq("status", status)
    if payer:
        query = query.eq("payer_name", payer)
    if market:
        query = query.eq("market", market)

    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

    result = query.execute()
    claims = [_row_to_response(row) for row in (result.data or [])]
    total = result.count or len(claims)

    return claims, total


async def update_claim_status(
    claim_id: str,
    new_status: ClaimStatus,
    human_review_flag: bool | None = None,
    human_review_reason: str | None = None,
) -> ClaimResponse | None:
    """Update a claim's status and optional review flags."""
    client = get_supabase_client()

    payload: dict[str, Any] = {"status": new_status.value}
    if human_review_flag is not None:
        payload["human_review_flag"] = human_review_flag
    if human_review_reason is not None:
        payload["human_review_reason"] = human_review_reason

    result = client.table("claims").update(payload).eq("id", claim_id).execute()

    if not result.data:
        return None

    logger.info("claim.status_updated | claim_id=%s new_status=%s", claim_id, new_status.value)
    return _row_to_response(result.data[0])


async def ingest_eob(claim_id: str, denial_reason_code: str, denial_reason_desc: str = "") -> ClaimResponse | None:
    """Mark a claim as DENIED after receiving an EOB."""
    client = get_supabase_client()

    result = (
        client.table("claims")
        .update({"status": ClaimStatus.DENIED.value})
        .eq("id", claim_id)
        .execute()
    )

    if not result.data:
        return None

    logger.info("claim.eob_ingested | claim_id=%s denial_code=%s", claim_id, denial_reason_code)
    return _row_to_response(result.data[0])


async def save_human_feedback(claim_id: str, specialist_id: str, action: str, notes: str) -> None:
    """Save HITL specialist feedback for few-shot learning."""
    client = get_supabase_client()
    payload = {
        "claim_id": claim_id,
        "specialist_id": specialist_id,
        "action": action,
        "notes": notes
    }
    result = client.table("human_feedback").insert(payload).execute()
    if not result.data:
        logger.error("claim.feedback.failed | claim_id=%s", claim_id)
    else:
        logger.info("claim.feedback.saved | claim_id=%s action=%s", claim_id, action)


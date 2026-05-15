"""
MedClaim — Claims Router

Endpoints for claim lifecycle management:
    POST   /claims              — Ingest a new claim (JSON or FHIR)
    GET    /claims              — List claims with filtering
    GET    /claims/{claim_id}   — Get single claim detail
    POST   /claims/{claim_id}/eob — Ingest denial EOB
    POST   /claims/{claim_id}/approve — Approve corrections/appeal
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.claim import (
    ClaimApproval,
    ClaimCreate,
    ClaimListResponse,
    ClaimResponse,
    ClaimStatus,
    EOBCreate,
    parse_fhir_claim,
)
from backend.app.models.responses import APIResponse
from backend.app.services.claim_service import (
    create_claim,
    get_claim,
    ingest_eob,
    list_claims,
    update_claim_status,
)

logger = logging.getLogger("medclaim.routers.claims")

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.post("", response_model=APIResponse[ClaimResponse])
async def ingest_claim(body: dict[str, Any]) -> APIResponse[ClaimResponse]:
    """
    Ingest a new claim. Accepts either:
    - Simplified JSON (ClaimCreate schema)
    - FHIR R4 Claim resource (detected by resourceType field)
    """
    try:
        # Detect FHIR resource
        if body.get("resourceType") == "Claim":
            logger.info("claim.ingest.fhir_format")
            claim_data = parse_fhir_claim(body)
        else:
            logger.info("claim.ingest.json_format")
            claim_data = ClaimCreate(**body)

        result = await create_claim(claim_data)
        return APIResponse(success=True, data=result, message="Claim ingested successfully")

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("claim.ingest.failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to ingest claim")


@router.get("", response_model=APIResponse[ClaimListResponse])
async def list_all_claims(
    status: str | None = Query(None, description="Filter by claim status"),
    payer: str | None = Query(None, description="Filter by payer name"),
    market: str | None = Query(None, description="Filter by market (US/INDIA)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
) -> APIResponse[ClaimListResponse]:
    """List claims with optional status/payer/market filters and pagination."""
    claims, total = await list_claims(
        status=status, payer=payer, market=market, page=page, page_size=page_size
    )
    return APIResponse(
        success=True,
        data=ClaimListResponse(claims=claims, total=total, page=page, page_size=page_size),
    )


@router.get("/{claim_id}", response_model=APIResponse[ClaimResponse])
async def get_claim_detail(claim_id: str) -> APIResponse[ClaimResponse]:
    """Get full detail for a single claim."""
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return APIResponse(success=True, data=claim)


@router.post("/{claim_id}/eob", response_model=APIResponse[ClaimResponse])
async def ingest_denial_eob(claim_id: str, eob: EOBCreate) -> APIResponse[ClaimResponse]:
    """Ingest an Explanation of Benefits for a denied claim."""
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    result = await ingest_eob(claim_id, eob.denial_reason_code, eob.denial_reason_description)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to process EOB")

    logger.info("claim.eob_ingested", claim_id=claim_id, denial_code=eob.denial_reason_code)
    return APIResponse(success=True, data=result, message="EOB ingested, claim marked as DENIED")


@router.post("/{claim_id}/approve", response_model=APIResponse[ClaimResponse])
async def approve_claim(claim_id: str, approval: ClaimApproval) -> APIResponse[ClaimResponse]:
    """
    Approve corrections or appeal letter for a claim.
    Requires human_approved=true (regulatory requirement).
    """
    if not approval.human_approved:
        raise HTTPException(
            status_code=400,
            detail="human_approved must be true. Autonomous submission is not permitted.",
        )

    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    # Determine next status based on current
    status_transitions = {
        ClaimStatus.CORRECTION_PENDING: ClaimStatus.READY_FOR_SUBMISSION,
        ClaimStatus.APPEAL_PENDING_APPROVAL: ClaimStatus.APPEAL_SUBMITTED,
        ClaimStatus.READY_FOR_SUBMISSION: ClaimStatus.SUBMITTED,
    }

    new_status = status_transitions.get(claim.status)
    if not new_status:
        raise HTTPException(
            status_code=400,
            detail=f"Claim in status {claim.status} cannot be approved",
        )

    result = await update_claim_status(claim_id, new_status)
    logger.info("claim.approved", claim_id=claim_id, by=approval.approved_by, new_status=new_status)
    return APIResponse(success=True, data=result, message=f"Claim approved → {new_status.value}")

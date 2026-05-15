"""
MedClaim — Agents Router

Manual trigger endpoints for individual agents.
Used by the dashboard for demonstration and debugging.

    POST /agents/audit/{claim_id}   — Trigger code audit
    POST /agents/predict/{claim_id} — Trigger denial prediction
    POST /agents/appeal/{claim_id}  — Trigger appeal drafting
    POST /agents/process/{claim_id} — Trigger full pipeline
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.app.models.responses import APIResponse
from backend.app.services.claim_service import get_claim

logger = logging.getLogger("medclaim.routers.agents")

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/audit/{claim_id}", response_model=APIResponse)
async def trigger_audit(claim_id: str) -> APIResponse:
    """Manually trigger the Code Audit Agent for a specific claim."""
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    # TODO: Phase 2 — invoke CodeAuditAgent via LangGraph
    logger.info("agent.audit.triggered", claim_id=claim_id)
    return APIResponse(
        success=True,
        message=f"Code audit triggered for claim {claim_id} (agent not yet implemented)",
    )


@router.post("/predict/{claim_id}", response_model=APIResponse)
async def trigger_prediction(claim_id: str) -> APIResponse:
    """Manually trigger the Denial Prediction Agent for a specific claim."""
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    # TODO: Phase 2 — invoke DenialPredictionAgent via LangGraph
    logger.info("agent.prediction.triggered", claim_id=claim_id)
    return APIResponse(
        success=True,
        message=f"Denial prediction triggered for claim {claim_id} (agent not yet implemented)",
    )


@router.post("/appeal/{claim_id}", response_model=APIResponse)
async def trigger_appeal(claim_id: str) -> APIResponse:
    """Manually trigger the Appeal Drafting Agent for a specific claim."""
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    # TODO: Phase 2 — invoke AppealDraftingAgent via LangGraph
    logger.info("agent.appeal.triggered", claim_id=claim_id)
    return APIResponse(
        success=True,
        message=f"Appeal drafting triggered for claim {claim_id} (agent not yet implemented)",
    )


@router.post("/process/{claim_id}", response_model=APIResponse)
async def trigger_full_pipeline(claim_id: str) -> APIResponse:
    """Trigger the full LangGraph processing pipeline for a claim."""
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    # TODO: Phase 2 — invoke full LangGraph StateGraph
    logger.info("agent.pipeline.triggered", claim_id=claim_id)
    return APIResponse(
        success=True,
        message=f"Full pipeline triggered for claim {claim_id} (agents not yet implemented)",
    )

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
    logger.info("agent.audit.triggered | claim_id=%s", claim_id)
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
    logger.info("agent.prediction.triggered | claim_id=%s", claim_id)
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
    logger.info("agent.appeal.triggered | claim_id=%s", claim_id)
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

    logger.info("agent.pipeline.triggered | claim_id=%s", claim_id)

    try:
        from backend.agents.graph import process_claim
        final_state = await process_claim(claim_id)

        return APIResponse(
            success=True,
            data={
                "claim_id": claim_id,
                "final_status": final_state.get("status"),
                "human_review_flag": final_state.get("human_review_flag", False),
                "human_review_reason": final_state.get("human_review_reason", ""),
                "audit_confidence": final_state.get("audit_confidence"),
                "denial_risk_score": final_state.get("denial_risk_score"),
                "current_agent": final_state.get("current_agent"),
            },
            message=f"Pipeline complete → {final_state.get('status')}",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("agent.pipeline.failed | claim_id=%s error=%s", claim_id, str(e))
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


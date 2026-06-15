"""
MedClaim — Outcome Feedback Loop Router

Handles the continuous learning loop. When a claim reaches a terminal
resolution (e.g., APPROVED_ON_APPEAL, FINAL_DENIED), this endpoint
receives the outcome, embeds it, and upserts it into the Qdrant
`denial_patterns` collection for future agents to use as few-shot RAG examples.

Implementation: Missed Subphase 4.1
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from langchain_community.embeddings import OllamaEmbeddings
from pydantic import BaseModel
from qdrant_client.models import PointStruct

from backend.app.services.claim_service import get_claim
from backend.rag.setup import get_qdrant_client

logger = logging.getLogger("medclaim.routers.feedback")
router = APIRouter(prefix="/feedback", tags=["Feedback Loop"])


class OutcomePayload(BaseModel):
    claim_id: str
    outcome: str
    denial_reason_code: str | None = None
    notes: str | None = None


@router.post("/claim-outcome")
async def process_claim_outcome(payload: OutcomePayload) -> dict[str, Any]:
    """
    Process a claim outcome and embed it into the denial_patterns collection.
    Called via Supabase Edge Function (Webhook) or directly by the frontend/API.
    """
    claim_id = payload.claim_id
    logger.info("feedback.received | claim_id=%s outcome=%s", claim_id, payload.outcome)

    # 1. Fetch full claim context
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # 2. Format as a pattern document
    dx_str = ", ".join(
        [f"{d.get('code')} ({d.get('description', '')})" for d in claim.diagnosis_codes]
    )
    px_str = ", ".join(
        [f"{p.get('code')} ({p.get('description', '')})" for p in claim.procedure_codes]
    )

    content = (
        f"Payer: {claim.payer_name} | Facility: {claim.facility_type} | "
        f"Diagnoses: {dx_str} | Procedures: {px_str} | "
        f"Outcome: {payload.outcome} | Denial Reason: {payload.denial_reason_code or 'N/A'}"
    )

    # 3. Generate embedding
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vector = embeddings.embed_query(content)
    except Exception as e:
        logger.warning("feedback.embed.failed | claim_id=%s error=%s", claim_id, str(e))
        vector = [0.0] * 768  # Fallback zero vector if Ollama is unavailable

    # 4. Upsert into Qdrant using the claim UUID as the point ID to prevent duplicates
    try:
        qdrant = get_qdrant_client()
        qdrant.upsert(
            collection_name="denial_patterns",
            points=[
                PointStruct(
                    id=str(claim.id),  # Use claim UUID to overwrite if status updates
                    vector=vector,
                    payload={
                        "page_content": content,
                        "metadata": {
                            "claim_id": str(claim.id),
                            "payer_name": claim.payer_name,
                            "facility_type": claim.facility_type,
                            "outcome": payload.outcome,
                            "denial_reason_code": payload.denial_reason_code,
                            "notes": payload.notes,
                        },
                    },
                )
            ],
        )
        logger.info("feedback.upserted | claim_id=%s", claim_id)
        return {"success": True, "message": "Outcome embedded and upserted to Qdrant"}
    except Exception as e:
        logger.error("feedback.upsert.failed | claim_id=%s error=%s", claim_id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upsert feedback: {str(e)}")

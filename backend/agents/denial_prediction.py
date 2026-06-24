"""
MedClaim — Denial Prediction Agent

Predicts claim denial risk by analyzing the claim against historical
denial patterns (from Qdrant) and the current audit results.

Pipeline:
    1. Retrieve similar historical denials from the denial_patterns collection
    2. Render the denial_prediction.j2 prompt with claim + audit context
    3. Query Groq LLM (with Gemini fallback) for structured risk assessment
    4. Parse risk_score (0–100), risk_factors, and recommended_action
    5. Record metrics to Prometheus (DENIALS_PREDICTED counter)

The denial_patterns collection may be empty during early development.
The agent handles this gracefully by relying on the LLM's general
knowledge combined with the audit findings already in state.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from backend.agents.llm import query_llm
from backend.agents.state import ClaimState
from backend.llmops.metrics import DENIALS_PREDICTED
from backend.prompts.loader import render_prompt
from backend.rag.retrievers import retrieve_with_scores

logger = structlog.get_logger("medclaim.agents.denial_prediction")


def _format_denial_patterns(results: list[tuple[Any, float]]) -> str:
    """Format historical denial pattern documents for prompt injection."""
    if not results:
        return (
            "No historical denial patterns found in the knowledge base. "
            "Assess risk based on general coding and payer policy knowledge."
        )

    formatted = []
    for idx, (doc, score) in enumerate(results, 1):
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        meta = doc.metadata if hasattr(doc, "metadata") else {}

        payer = meta.get("payer_name", "Unknown")
        denial_code = meta.get("denial_code", "N/A")
        outcome = meta.get("outcome", "N/A")

        formatted.append(
            f"[{idx}] Payer: {payer} | Denial Code: {denial_code} | "
            f"Outcome: {outcome} (Similarity: {score:.4f})\n"
            f"Details: {content}"
        )
    return "\n\n".join(formatted)


async def run_denial_prediction(state: ClaimState) -> dict[str, Any]:
    """
    Execute the Denial Prediction Agent.

    Args:
        state: Current pipeline state (must include audit results).

    Returns:
        Partial state update with denial_risk_score, risk_factors,
        recommended_action, and LLMOps telemetry.
    """
    claim_id = state.get("claim_id", "unknown")
    market = state.get("market", "US")
    payer_name = state.get("payer_name", "")
    payer_id = state.get("payer_id", "")
    diagnosis_codes = state.get("diagnosis_codes", [])
    procedure_codes = state.get("procedure_codes", [])

    start_time = time.time()
    logger.info("agent.denial_prediction.start", claim_id=claim_id)

    # ── Step 1: RAG retrieval from denial_patterns ───────────
    dx_terms = " ".join([dx.get("code", "") for dx in diagnosis_codes])
    px_terms = " ".join([px.get("code", "") for px in procedure_codes])
    rag_query = f"{payer_name} {dx_terms} {px_terms} denial".strip()

    try:
        denial_docs = retrieve_with_scores(
            collection_name="denial_patterns",
            query=rag_query,
            top_k=5,
            filter_kwargs={"market": market},
        )
    except Exception as e:
        # denial_patterns may be empty — this is expected in early dev
        logger.warning(
            "agent.denial_prediction.rag_failed",
            claim_id=claim_id,
            error=str(e),
        )
        denial_docs = []

    rag_context = _format_denial_patterns(denial_docs)

    # ── Step 2: Render prompt ────────────────────────────────
    prompt_context = {
        "market": market,
        "payer_name": payer_name,
        "payer_id": payer_id,
        "patient_name": state.get("patient_name", "Unknown"),
        "date_of_service": state.get("date_of_service", "Unknown"),
        "facility_type": state.get("facility_type", "physician_office"),
        "billed_amount": state.get("billed_amount", 0.0),
        "diagnosis_codes": diagnosis_codes,
        "procedure_codes": procedure_codes,
        "audit_confidence": state.get("audit_confidence", 0.0),
        "audit_findings": state.get("audit_findings", []),
        "audit_summary": state.get("audit_summary", ""),
        "rag_context": rag_context,
    }

    try:
        user_prompt = render_prompt("denial_prediction", prompt_context)
        system_prompt = (
            "You are an insurance claims risk analyst. "
            "Analyze the claim data and predict the likelihood of denial. "
            "Return strict structured JSON."
        )

        # ── Step 3: Query LLM ────────────────────────────────
        llm_response = await query_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            preferred_provider="groq",
            temperature=0.1,
            json_mode=True,
        )

        # ── Step 4: Parse response ───────────────────────────
        prediction_json = llm_response.get("json") or {}

        risk_score = int(prediction_json.get("risk_score", 50))
        risk_score = max(0, min(100, risk_score))  # Clamp to 0-100

        risk_factors = prediction_json.get("risk_factors", [])
        # Normalize risk factors to our expected schema
        normalized_factors = []
        for rf in risk_factors[:5]:  # Cap at top 5
            normalized_factors.append(
                {
                    "factor": rf.get("factor", "Unknown factor"),
                    "weight": float(rf.get("weight", 0.5)),
                    "description": rf.get("description", ""),
                }
            )

        recommended_action = prediction_json.get("recommended_action", "SUBMIT_AS_IS")
        valid_actions = {"SUBMIT_AS_IS", "CORRECT_AND_RESUBMIT", "ESCALATE_TO_HUMAN"}
        if recommended_action not in valid_actions:
            recommended_action = "SUBMIT_AS_IS"

        latency = int((time.time() - start_time) * 1000)

        # ── Step 5: Prometheus metrics ───────────────────────
        risk_level = "low" if risk_score <= 30 else ("medium" if risk_score <= 70 else "high")
        DENIALS_PREDICTED.labels(risk_level=risk_level, market=market).inc()

        logger.info(
            "agent.denial_prediction.complete",
            claim_id=claim_id,
            risk_score=risk_score,
            risk_level=risk_level,
            action=recommended_action,
            factors_count=len(normalized_factors),
            latency_ms=latency,
        )

        # Track LLMOps
        prompt_tokens = llm_response.get("prompt_tokens", 0)
        completion_tokens = llm_response.get("completion_tokens", 0)

        retry_count = state.get("retry_count", 0)

        if risk_score > 70:
            retry_count += 1

        return {
            "denial_risk_score": risk_score,
            "retry_count": retry_count,
            "risk_factors": normalized_factors,
            "recommended_action": recommended_action,
            "status": "PREDICTION_COMPLETE",
            "current_agent": "denial_prediction",
            "total_prompt_tokens": state.get("total_prompt_tokens", 0) + prompt_tokens,
            "total_completion_tokens": state.get("total_completion_tokens", 0) + completion_tokens,
            "total_latency_ms": state.get("total_latency_ms", 0) + latency,
            "llm_calls": state.get("llm_calls", [])
            + [
                {
                    "agent": "denial_prediction",
                    "provider": llm_response.get("provider"),
                    "model": llm_response.get("model"),
                    "latency_ms": latency,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
            ],
        }

    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        logger.error(
            "agent.denial_prediction.failed",
            claim_id=claim_id,
            error=str(e),
            latency_ms=latency,
        )

        # Fallback: moderate risk to trigger human review rather than auto-submit
        return {
            "denial_risk_score": 55,
            "risk_factors": [
                {
                    "factor": "Prediction agent error",
                    "weight": 1.0,
                    "description": f"Agent failed: {str(e)}. Defaulting to moderate risk.",
                }
            ],
            "recommended_action": "ESCALATE_TO_HUMAN",
            "status": "PREDICTION_COMPLETE",
            "current_agent": "denial_prediction",
            "processing_errors": state.get("processing_errors", [])
            + [f"Denial prediction error: {str(e)}"],
            "total_latency_ms": state.get("total_latency_ms", 0) + latency,
        }

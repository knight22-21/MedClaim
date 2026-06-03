"""
MedClaim — LangGraph State Machine

Constructs and compiles the claim processing pipeline as a LangGraph
StateGraph with deterministic conditional edges routed by the Supervisor.

Graph Topology:
    ┌─────────┐
    │  START   │
    └────┬─────┘
         │
    ┌────▼──────────┐
    │ eligibility    │
    │   _check       │
    └────┬──────────┘
         │ (supervisor decides)
    ┌────▼──────────┐     ┌──────────────┐
    │  code_audit   │◄────│  correction  │
    └────┬──────────┘     │    loop      │
         │                └──────┬───────┘
    ┌────▼──────────┐            │
    │   denial      │────────────┘
    │  _prediction  │
    └────┬──────────┘
         │ (risk ≤ 70)
    ┌────▼──────────┐
    │ ready_for     │
    │ _submission   │──────► END
    └───────────────┘

    ┌───────────────┐
    │ appeal        │──────► END (await approval)
    │ _drafting     │
    └───────────────┘

    ┌───────────────┐
    │ human_review  │──────► END (await specialist)
    └───────────────┘

Usage:
    from backend.agents.graph import process_claim

    result = await process_claim("claim-uuid-here")
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from backend.agents.nodes import (
    appeal_drafting,
    code_audit,
    denial_prediction,
    eligibility_check,
    human_review,
    ready_for_submission,
)
from backend.agents.state import ClaimState
from backend.agents.supervisor import route_claim
from backend.app.services.claim_service import get_claim, update_claim_status
from backend.app.models.claim import ClaimStatus

logger = logging.getLogger("medclaim.agents.graph")


def build_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph for claim processing.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = StateGraph(ClaimState)

    # ── Add Nodes ────────────────────────────────────────────
    graph.add_node("eligibility_check", eligibility_check)
    graph.add_node("code_audit", code_audit)
    graph.add_node("denial_prediction", denial_prediction)
    graph.add_node("ready_for_submission", ready_for_submission)
    graph.add_node("appeal_drafting", appeal_drafting)
    graph.add_node("human_review", human_review)

    # ── Entry Point ──────────────────────────────────────────
    # All claims start at eligibility check
    graph.set_entry_point("eligibility_check")

    # ── Conditional Edges (Supervisor Router) ────────────────
    # After eligibility check → supervisor decides
    graph.add_conditional_edges(
        "eligibility_check",
        route_claim,
        {
            "code_audit": "code_audit",
            "human_review": "human_review",
            "__end__": END,
        },
    )

    # After code audit → supervisor decides
    graph.add_conditional_edges(
        "code_audit",
        route_claim,
        {
            "denial_prediction": "denial_prediction",
            "human_review": "human_review",
            "__end__": END,
        },
    )

    # After denial prediction → supervisor decides
    graph.add_conditional_edges(
        "denial_prediction",
        route_claim,
        {
            "ready_for_submission": "ready_for_submission",
            "code_audit": "code_audit",      # correction loop
            "human_review": "human_review",
            "__end__": END,
        },
    )

    # After appeal drafting → end (await human approval)
    graph.add_edge("appeal_drafting", END)

    # Terminal nodes → end
    graph.add_edge("ready_for_submission", END)
    graph.add_edge("human_review", END)

    return graph


# ── Compiled Graph (singleton) ───────────────────────────────
_compiled_graph = None


def get_compiled_graph():
    """Get or create the compiled graph (cached singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_graph()
        _compiled_graph = graph.compile()
        logger.info("graph.compiled | nodes=6 edges=conditional")
    return _compiled_graph


# ── Public API ───────────────────────────────────────────────

async def process_claim(claim_id: str) -> dict[str, Any]:
    """
    Run the full agentic pipeline for a claim.

    Fetches the claim from Supabase, builds initial ClaimState,
    invokes the LangGraph, and persists the final status.

    Args:
        claim_id: UUID of the claim to process.

    Returns:
        Final ClaimState after pipeline execution.

    Raises:
        ValueError: If claim_id not found in database.
    """
    logger.info("pipeline.start | claim_id=%s", claim_id)

    # 1. Fetch claim from DB
    claim = await get_claim(claim_id)
    if not claim:
        raise ValueError(f"Claim {claim_id} not found")

    # 2. Build initial state from claim data
    initial_state: ClaimState = {
        "claim_id": str(claim.id),
        "patient_name": claim.patient_name,
        "patient_dob": str(claim.patient_dob),
        "payer_name": claim.payer_name,
        "payer_id": claim.payer_id,
        "date_of_service": str(claim.date_of_service),
        "facility_type": claim.facility_type,
        "diagnosis_codes": claim.diagnosis_codes,
        "procedure_codes": claim.procedure_codes,
        "billed_amount": claim.billed_amount,
        "market": claim.market,
        "status": "RECEIVED",
        "current_agent": "supervisor",
        "previous_agent": "",
        "retry_count": 0,
        "human_review_flag": False,
        "human_review_reason": "",
        "processing_errors": [],
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_latency_ms": 0,
        "llm_calls": [],
    }

    # 3. Run the graph
    compiled = get_compiled_graph()
    try:
        run_config = {
            "tags": [initial_state.get("market", "US"), "pipeline_run"],
            "metadata": {
                "claim_id": claim_id,
                "payer_name": initial_state.get("payer_name", ""),
            },
            "callbacks": [] # Can attach specific callbacks here if needed
        }
        final_state = await compiled.ainvoke(initial_state, config=run_config)
    except Exception as e:
        logger.error("pipeline.failed | claim_id=%s error=%s", claim_id, str(e))
        await update_claim_status(
            claim_id,
            ClaimStatus.HUMAN_REVIEW_REQUIRED,
            human_review_flag=True,
            human_review_reason=f"Pipeline error: {str(e)}",
        )
        raise

    # 4. Persist final status to DB
    final_status_str = final_state.get("status", "HUMAN_REVIEW_REQUIRED")
    try:
        final_status = ClaimStatus(final_status_str)
    except ValueError:
        final_status = ClaimStatus.HUMAN_REVIEW_REQUIRED

    await update_claim_status(
        claim_id,
        final_status,
        human_review_flag=final_state.get("human_review_flag", False),
        human_review_reason=final_state.get("human_review_reason"),
    )

    logger.info(
        "pipeline.complete | claim_id=%s final_status=%s total_tokens=%d",
        claim_id,
        final_status_str,
        final_state.get("total_prompt_tokens", 0)
        + final_state.get("total_completion_tokens", 0),
    )

    return final_state

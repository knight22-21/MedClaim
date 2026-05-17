"""
MedClaim — Supervisor Agent (Deterministic Router)

The Supervisor is NOT an LLM — it is pure Python conditional logic
that examines ClaimState values and returns the name of the next
node in the LangGraph pipeline. This eliminates LLM latency and
non-determinism from routing decisions.

Routing Table:
    ┌──────────────────────────────┬─────────────────────────────────┐
    │ Condition                    │ Next Node                       │
    ├──────────────────────────────┼─────────────────────────────────┤
    │ status == RECEIVED           │ eligibility_check               │
    │ status == ELIGIBILITY_VERIFIED│ code_audit                     │
    │ status == ELIGIBILITY_FAILED │ __end__ (human review flagged)  │
    │ status == AUDIT_COMPLETE     │                                 │
    │   confidence >= 0.80         │ denial_prediction               │
    │   confidence <  0.80         │ human_review                    │
    │ status == READY_FOR_SUBMISSION│ __end__                        │
    │ status == HUMAN_REVIEW_REQUIRED│ __end__                       │
    │ denial_risk <= 70            │ ready_for_submission            │
    │ denial_risk > 70, retry < 2  │ code_audit (correction loop)   │
    │ denial_risk > 70, retry >= 2 │ human_review                   │
    │ status == DENIED             │ appeal_drafting                 │
    │ status == APPEAL_DRAFT_READY │ __end__ (await approval)        │
    │ fallback                     │ __end__                         │
    └──────────────────────────────┴─────────────────────────────────┘
"""

from __future__ import annotations

import logging

from backend.agents.state import ClaimState

logger = logging.getLogger("medclaim.agents.supervisor")

# Node name constants — must match the names used in graph.py
NODE_ELIGIBILITY = "eligibility_check"
NODE_CODE_AUDIT = "code_audit"
NODE_DENIAL_PREDICTION = "denial_prediction"
NODE_APPEAL_DRAFTING = "appeal_drafting"
NODE_HUMAN_REVIEW = "human_review"
NODE_READY = "ready_for_submission"
NODE_END = "__end__"

# Thresholds
AUDIT_CONFIDENCE_THRESHOLD = 0.80
DENIAL_RISK_THRESHOLD = 70
MAX_CORRECTION_RETRIES = 2


def route_claim(state: ClaimState) -> str:
    """
    Deterministic routing function for the Supervisor node.

    Examines the current ClaimState and returns the name of the
    next LangGraph node to execute.

    Args:
        state: Current pipeline state.

    Returns:
        Name of the next node (str). "__end__" terminates the graph.
    """
    status = state.get("status", "RECEIVED")
    claim_id = state.get("claim_id", "unknown")

    logger.info(
        "supervisor.routing | claim_id=%s current_status=%s current_agent=%s",
        claim_id,
        status,
        state.get("current_agent", "none"),
    )

    # ── RECEIVED: Start pipeline ─────────────────────────────
    if status == "RECEIVED":
        logger.info(
            "supervisor.route | claim_id=%s next_node=%s",
            claim_id,
            NODE_ELIGIBILITY,
        )
        return NODE_ELIGIBILITY

    # ── ELIGIBILITY_FAILED: Cannot proceed ───────────────────
    if status == "ELIGIBILITY_FAILED":
        logger.info(
            "supervisor.route | claim_id=%s next_node=%s reason=%s",
            claim_id,
            NODE_END,
            "eligibility_failed",
        )
        return NODE_END

    # ── ELIGIBILITY_VERIFIED: Proceed to audit ───────────────
    if status == "ELIGIBILITY_VERIFIED":
        logger.info(
            "supervisor.route | claim_id=%s next_node=%s",
            claim_id,
            NODE_CODE_AUDIT,
        )
        return NODE_CODE_AUDIT

    # ── AUDIT_COMPLETE: Check confidence ─────────────────────
    if status == "AUDIT_COMPLETE":
        confidence = state.get("audit_confidence", 0.0)

        if confidence >= AUDIT_CONFIDENCE_THRESHOLD:
            logger.info(
                "supervisor.route | claim_id=%s next_node=%s confidence=%.2f",
                claim_id,
                NODE_DENIAL_PREDICTION,
                confidence,
            )
            return NODE_DENIAL_PREDICTION
        else:
            logger.warning(
                "supervisor.route.low_confidence | "
                "claim_id=%s next_node=%s confidence=%.2f threshold=%.2f",
                claim_id,
                NODE_HUMAN_REVIEW,
                confidence,
                AUDIT_CONFIDENCE_THRESHOLD,
            )
            return NODE_HUMAN_REVIEW

    # ── Post Denial Prediction: Evaluate risk ────────────────
    if status == "PREDICTION_COMPLETE":
        risk_score = state.get("denial_risk_score", 0)
        retry_count = state.get("retry_count", 0)

        if risk_score <= DENIAL_RISK_THRESHOLD:
            logger.info(
                "supervisor.route | claim_id=%s next_node=%s risk_score=%s",
                claim_id,
                NODE_READY,
                risk_score,
            )
            return NODE_READY

        elif retry_count < MAX_CORRECTION_RETRIES:
            logger.warning(
                "supervisor.route.correction_loop | "
                "claim_id=%s next_node=%s risk_score=%s retry=%s",
                claim_id,
                NODE_CODE_AUDIT,
                risk_score,
                retry_count,
            )
            return NODE_CODE_AUDIT

        else:
            logger.warning(
                "supervisor.route.max_retries | "
                "claim_id=%s next_node=%s risk_score=%s retry=%s",
                claim_id,
                NODE_HUMAN_REVIEW,
                risk_score,
                retry_count,
            )
            return NODE_HUMAN_REVIEW

    # ── DENIED: Generate appeal ──────────────────────────────
    if status == "DENIED":
        logger.info(
            "supervisor.route | claim_id=%s next_node=%s",
            claim_id,
            NODE_APPEAL_DRAFTING,
        )
        return NODE_APPEAL_DRAFTING

    # ── Terminal states: Stop the graph ──────────────────────
    terminal_statuses = {
        "READY_FOR_SUBMISSION",
        "SUBMITTED",
        "HUMAN_REVIEW_REQUIRED",
        "CORRECTION_PENDING",
        "APPEAL_DRAFT_READY",
        "APPEAL_PENDING_APPROVAL",
        "APPEAL_SUBMITTED",
        "APPROVED",
        "APPROVED_ON_APPEAL",
        "FINAL_DENIED",
    }

    if status in terminal_statuses:
        logger.info(
            "supervisor.route.terminal | claim_id=%s status=%s",
            claim_id,
            status,
        )
        return NODE_END

    # ── Fallback ─────────────────────────────────────────────
    logger.error(
        "supervisor.route.unknown_status | claim_id=%s status=%s",
        claim_id,
        status,
    )

    return NODE_END
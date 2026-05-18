"""
MedClaim — Eligibility Verification Agent

Verifies patient insurance coverage before coding work begins.
This is the first agent in the LangGraph pipeline — it gates all
downstream processing.

Checks performed:
    1. Coverage active on date of service
    2. Procedure covered under plan
    3. Provider in-network

Uses fixture-based mock for development. In production, this would
integrate with real payer eligibility APIs (X12 270/271 transactions).

Market-specific behavior:
    US:    Checks against Medicare/Medicaid/commercial payer rules
    INDIA: Checks against IRDAI/PM-JAY HBP coverage lists
"""

from __future__ import annotations

import logging
import time
from typing import Any

from backend.agents.state import ClaimState
from backend.app.services.eligibility_service import (
    get_payer_info,
    verify_eligibility,
)

logger = logging.getLogger("medclaim.agents.eligibility")


def run_eligibility_check(state: ClaimState) -> dict[str, Any]:
    """
    Execute the eligibility verification agent.

    Reads claim data from state, calls the eligibility service,
    and returns a partial state update with the result.

    Args:
        state: Current ClaimState from the LangGraph pipeline.

    Returns:
        Partial state dict with eligibility_result, eligibility_status,
        status, and current_agent fields.
    """
    claim_id = state.get("claim_id", "unknown")
    payer_id = state.get("payer_id", "")
    payer_name = state.get("payer_name", "")
    patient_dob = state.get("patient_dob", "")
    procedure_codes = state.get("procedure_codes", [])
    market = state.get("market", "US")

    start = time.time()
    logger.info(
        "agent.eligibility.start | claim_id=%s payer=%s market=%s",
        claim_id, payer_name, market,
    )

    try:
        # Run verification
        result = verify_eligibility(
            payer_id=payer_id,
            payer_name=payer_name,
            patient_dob=patient_dob,
            procedure_codes=procedure_codes,
            market=market,
        )

        is_eligible = result.get("is_eligible", False)
        failure_reason = result.get("failure_reason", "")

        latency = int((time.time() - start) * 1000)

        if is_eligible:
            logger.info(
                "agent.eligibility.verified | claim_id=%s payer=%s latency_ms=%d",
                claim_id, payer_name, latency,
            )

            # Look up payer info for enrichment
            payer_info = get_payer_info(payer_id, market)

            return {
                "eligibility_result": result,
                "eligibility_status": "VERIFIED",
                "status": "ELIGIBILITY_VERIFIED",
                "current_agent": "eligibility_check",
            }
        else:
            logger.warning(
                "agent.eligibility.failed | claim_id=%s payer=%s reason=%s latency_ms=%d",
                claim_id, payer_name, failure_reason, latency,
            )
            return {
                "eligibility_result": result,
                "eligibility_status": "FAILED",
                "status": "ELIGIBILITY_FAILED",
                "current_agent": "eligibility_check",
                "human_review_flag": True,
                "human_review_reason": f"Eligibility failed: {failure_reason}",
            }

    except Exception as e:
        latency = int((time.time() - start) * 1000)
        logger.error(
            "agent.eligibility.error | claim_id=%s error=%s latency_ms=%d",
            claim_id, str(e), latency,
        )

        return {
            "eligibility_result": {
                "is_eligible": False,
                "coverage_active": False,
                "procedure_covered": False,
                "provider_in_network": False,
                "failure_reason": f"Eligibility check error: {str(e)}",
            },
            "eligibility_status": "FAILED",
            "status": "ELIGIBILITY_FAILED",
            "current_agent": "eligibility_check",
            "human_review_flag": True,
            "human_review_reason": f"Eligibility check error: {str(e)}",
            "processing_errors": state.get("processing_errors", []) + [str(e)],
        }

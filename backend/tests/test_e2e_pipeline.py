"""
MedClaim — End-to-End Pipeline Integration Tests

Tests the full LangGraph pipeline from RECEIVED to terminal states,
with all external calls (LLM, RAG) mocked. Validates:
    - Happy path traversal
    - Ineligible claim halts at ELIGIBILITY_FAILED
    - High risk + retry exhaustion escalates to HUMAN_REVIEW
    - LLMOps telemetry accumulates across agents
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from backend.agents.state import ClaimState


def _base_state(**overrides) -> ClaimState:
    """Create a fully populated initial ClaimState."""
    state: ClaimState = {
        "claim_id": "e2e-test-001",
        "patient_name": "E2E Patient",
        "patient_dob": "1985-03-15",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": "2024-06-01",
        "facility_type": "physician_office",
        "diagnosis_codes": [{"code": "J18.9", "description": "Pneumonia"}],
        "procedure_codes": [{"code": "99213", "description": "Office visit"}],
        "billed_amount": 250.00,
        "market": "US",
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
    state.update(overrides)
    return state


def _mock_llm_audit_clean():
    """LLM response for a clean code audit."""
    return {
        "content": "ok",
        "json": {
            "findings": [],
            "overall_confidence": 0.95,
            "summary": "All codes correctly assigned.",
        },
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "latency_ms": 350,
        "prompt_tokens": 1200,
        "completion_tokens": 150,
    }


def _mock_llm_prediction_low_risk():
    """LLM response for a low-risk denial prediction."""
    return {
        "content": "ok",
        "json": {
            "risk_score": 20,
            "risk_factors": [],
            "recommended_action": "SUBMIT_AS_IS",
        },
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "latency_ms": 200,
        "prompt_tokens": 1000,
        "completion_tokens": 80,
    }


def _mock_llm_prediction_high_risk():
    """LLM response for a high-risk denial prediction."""
    return {
        "content": "ok",
        "json": {
            "risk_score": 85,
            "risk_factors": [
                {"factor": "Missing prior auth", "weight": 0.9, "description": "PA required"}
            ],
            "recommended_action": "CORRECT_AND_RESUBMIT",
        },
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "latency_ms": 250,
        "prompt_tokens": 1100,
        "completion_tokens": 120,
    }


# ═══════════════════════════════════════════════════════════════
# Happy Path: RECEIVED → READY_FOR_SUBMISSION
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@patch("backend.agents.denial_prediction.retrieve_with_scores")
@patch("backend.agents.denial_prediction.query_llm")
@patch("backend.agents.code_audit.retrieve_with_scores")
@patch("backend.agents.code_audit.query_llm")
async def test_e2e_happy_path(
    mock_audit_llm,
    mock_audit_rag,
    mock_pred_llm,
    mock_pred_rag,
):
    """
    Full happy path: eligible → clean audit → low risk → READY_FOR_SUBMISSION.
    Traverses 4 nodes: eligibility → code_audit → denial_prediction → ready.
    """
    from backend.agents.graph import build_graph

    mock_audit_rag.return_value = []
    mock_audit_llm.return_value = _mock_llm_audit_clean()
    mock_pred_rag.return_value = []
    mock_pred_llm.return_value = _mock_llm_prediction_low_risk()

    compiled = build_graph().compile()
    result = await compiled.ainvoke(_base_state())

    # Final status
    assert result["status"] == "READY_FOR_SUBMISSION"
    assert result["human_review_flag"] is False

    # Eligibility passed
    assert result["eligibility_status"] == "VERIFIED"

    # Audit passed
    assert result["audit_confidence"] == 0.95
    assert len(result["audit_findings"]) == 0

    # Prediction passed
    assert result["denial_risk_score"] == 20
    assert result["recommended_action"] == "SUBMIT_AS_IS"

    # LLMOps telemetry accumulated from 2 LLM calls (audit + prediction)
    assert result["total_prompt_tokens"] == 1200 + 1000
    assert result["total_completion_tokens"] == 150 + 80
    assert len(result["llm_calls"]) == 2
    assert result["llm_calls"][0]["agent"] == "code_audit"
    assert result["llm_calls"][1]["agent"] == "denial_prediction"


# ═══════════════════════════════════════════════════════════════
# Ineligible Claim: RECEIVED → ELIGIBILITY_FAILED
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_e2e_ineligible_claim():
    """
    Ineligible claim stops immediately at ELIGIBILITY_FAILED.
    The MCR-001 / DOB 1978-12-01 fixture has coverage_active=false.
    """
    from backend.agents.graph import build_graph

    compiled = build_graph().compile()
    state = _base_state(patient_dob="1978-12-01")

    result = await compiled.ainvoke(state)

    assert result["status"] == "ELIGIBILITY_FAILED"
    assert result["human_review_flag"] is True
    assert "inactive" in result["human_review_reason"].lower()
    # No LLM calls should have been made
    assert len(result.get("llm_calls", [])) == 0


# ═══════════════════════════════════════════════════════════════
# High Risk + Retry Exhaustion: → HUMAN_REVIEW_REQUIRED
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@patch("backend.agents.denial_prediction.retrieve_with_scores")
@patch("backend.agents.denial_prediction.query_llm")
@patch("backend.agents.code_audit.retrieve_with_scores")
@patch("backend.agents.code_audit.query_llm")
async def test_e2e_high_risk_retry_exhaustion(
    mock_audit_llm,
    mock_audit_rag,
    mock_pred_llm,
    mock_pred_rag,
):
    """
    High risk claim exhausts correction retries → HUMAN_REVIEW_REQUIRED.

    Flow: eligibility → audit → prediction (high risk, retry 0)
          → audit (retry 1) → prediction (still high risk)
          → audit (retry 2) → prediction (still high risk, retry >= 2)
          → HUMAN_REVIEW_REQUIRED
    """
    from backend.agents.graph import build_graph

    mock_audit_rag.return_value = []
    mock_audit_llm.return_value = _mock_llm_audit_clean()
    mock_pred_rag.return_value = []
    # Always return high risk
    mock_pred_llm.return_value = _mock_llm_prediction_high_risk()

    compiled = build_graph().compile()
    result = await compiled.ainvoke(_base_state())

    assert result["status"] == "HUMAN_REVIEW_REQUIRED"
    assert result["human_review_flag"] is True
    assert "85%" in result["human_review_reason"]


# ═══════════════════════════════════════════════════════════════
# Audit Low Confidence: → HUMAN_REVIEW_REQUIRED
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@patch("backend.agents.code_audit.retrieve_with_scores")
@patch("backend.agents.code_audit.query_llm")
async def test_e2e_low_audit_confidence(mock_audit_llm, mock_audit_rag):
    """
    Audit returns low confidence (<0.80) → escalated to HUMAN_REVIEW.
    """
    from backend.agents.graph import build_graph

    mock_audit_rag.return_value = []
    mock_audit_llm.return_value = {
        "content": "ok",
        "json": {
            "findings": [
                {
                    "code": "99215",
                    "issue_type": "UPCODING",
                    "severity": "HIGH",
                    "description": "Possible upcoding",
                    "suggested_correction": "99213",
                    "confidence": 0.6,
                }
            ],
            "overall_confidence": 0.55,
            "summary": "Significant coding concerns.",
        },
        "provider": "mock",
        "model": "mock",
        "latency_ms": 1,
        "prompt_tokens": 1,
        "completion_tokens": 1,
    }

    compiled = build_graph().compile()
    result = await compiled.ainvoke(_base_state())

    assert result["status"] == "HUMAN_REVIEW_REQUIRED"
    assert result["human_review_flag"] is True
    assert "0.55" in result["human_review_reason"]

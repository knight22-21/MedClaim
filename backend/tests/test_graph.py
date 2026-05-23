"""
MedClaim — LangGraph Pipeline Tests

Tests the supervisor routing logic and graph traversal
using mock ClaimState objects.

Node functions that call LLM/RAG are mocked so these tests
run without external services.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.agents.supervisor import (
    route_claim,
    NODE_ELIGIBILITY,
    NODE_CODE_AUDIT,
    NODE_DENIAL_PREDICTION,
    NODE_APPEAL_DRAFTING,
    NODE_HUMAN_REVIEW,
    NODE_READY,
    NODE_END,
)
from backend.agents.state import ClaimState
from backend.agents.nodes import (
    eligibility_check,
    code_audit,
    denial_prediction,
    ready_for_submission,
    appeal_drafting,
    human_review,
)


def _base_state(**overrides) -> ClaimState:
    """Create a minimal ClaimState with sensible defaults."""
    state: ClaimState = {
        "claim_id": "test-claim-001",
        "patient_name": "Test Patient",
        "patient_dob": "1990-01-01",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": "2024-01-01",
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


# ═══════════════════════════════════════════════════════════════
# Supervisor Routing Tests
# ═══════════════════════════════════════════════════════════════

class TestSupervisorRouting:
    """Test each branch of the deterministic routing table."""

    def test_received_routes_to_eligibility(self):
        state = _base_state(status="RECEIVED")
        assert route_claim(state) == NODE_ELIGIBILITY

    def test_eligibility_verified_routes_to_audit(self):
        state = _base_state(status="ELIGIBILITY_VERIFIED")
        assert route_claim(state) == NODE_CODE_AUDIT

    def test_eligibility_failed_routes_to_end(self):
        state = _base_state(status="ELIGIBILITY_FAILED")
        assert route_claim(state) == NODE_END

    def test_audit_high_confidence_routes_to_prediction(self):
        state = _base_state(status="AUDIT_COMPLETE", audit_confidence=0.92)
        assert route_claim(state) == NODE_DENIAL_PREDICTION

    def test_audit_low_confidence_routes_to_human_review(self):
        state = _base_state(status="AUDIT_COMPLETE", audit_confidence=0.62)
        assert route_claim(state) == NODE_HUMAN_REVIEW

    def test_audit_boundary_confidence_routes_to_prediction(self):
        """Exactly 0.80 should pass (>= threshold)."""
        state = _base_state(status="AUDIT_COMPLETE", audit_confidence=0.80)
        assert route_claim(state) == NODE_DENIAL_PREDICTION

    def test_low_risk_routes_to_ready(self):
        state = _base_state(status="PREDICTION_COMPLETE", denial_risk_score=25)
        assert route_claim(state) == NODE_READY

    def test_high_risk_first_retry_routes_to_audit(self):
        state = _base_state(status="PREDICTION_COMPLETE", denial_risk_score=85, retry_count=0)
        assert route_claim(state) == NODE_CODE_AUDIT

    def test_high_risk_second_retry_routes_to_audit(self):
        state = _base_state(status="PREDICTION_COMPLETE", denial_risk_score=85, retry_count=1)
        assert route_claim(state) == NODE_CODE_AUDIT

    def test_high_risk_max_retries_routes_to_human_review(self):
        state = _base_state(status="PREDICTION_COMPLETE", denial_risk_score=85, retry_count=2)
        assert route_claim(state) == NODE_HUMAN_REVIEW

    def test_boundary_risk_routes_to_ready(self):
        """Exactly 70 should pass (<= threshold)."""
        state = _base_state(status="PREDICTION_COMPLETE", denial_risk_score=70)
        assert route_claim(state) == NODE_READY

    def test_denied_routes_to_appeal(self):
        state = _base_state(status="DENIED")
        assert route_claim(state) == NODE_APPEAL_DRAFTING

    def test_appeal_draft_ready_routes_to_end(self):
        state = _base_state(status="APPEAL_DRAFT_READY")
        assert route_claim(state) == NODE_END

    def test_ready_for_submission_routes_to_end(self):
        state = _base_state(status="READY_FOR_SUBMISSION")
        assert route_claim(state) == NODE_END

    def test_approved_routes_to_end(self):
        state = _base_state(status="APPROVED")
        assert route_claim(state) == NODE_END

    def test_unknown_status_routes_to_end(self):
        state = _base_state(status="TOTALLY_UNKNOWN")
        assert route_claim(state) == NODE_END


# ═══════════════════════════════════════════════════════════════
# Node Function Tests
# ═══════════════════════════════════════════════════════════════

class TestNodeFunctions:
    """Test that node functions return correct state updates."""

    def test_eligibility_check_returns_verified(self):
        state = _base_state()
        result = eligibility_check(state)
        assert result["status"] == "ELIGIBILITY_VERIFIED"
        assert result["eligibility_result"]["is_eligible"] is True
        assert result["current_agent"] == "eligibility_check"

    @pytest.mark.asyncio
    @patch("backend.agents.code_audit.retrieve_with_scores")
    @patch("backend.agents.code_audit.query_llm")
    async def test_code_audit_returns_complete(self, mock_query_llm, mock_retrieve):
        mock_retrieve.return_value = []
        mock_query_llm.return_value = {
            "content": "ok",
            "json": {
                "findings": [],
                "overall_confidence": 0.92,
                "summary": "No audit issues found",
            },
            "provider": "mock",
            "model": "mock",
            "latency_ms": 1,
            "prompt_tokens": 1,
            "completion_tokens": 1,
        }

        state = _base_state(status="ELIGIBILITY_VERIFIED")
        result = await code_audit(state)

        assert result["status"] == "AUDIT_COMPLETE"
        assert 0 <= result["audit_confidence"] <= 1
        assert result["current_agent"] == "code_audit"

    @pytest.mark.asyncio
    @patch("backend.agents.denial_prediction.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.query_llm")
    async def test_denial_prediction_returns_score(self, mock_query_llm, mock_retrieve):
        mock_retrieve.return_value = []
        mock_query_llm.return_value = {
            "content": "ok",
            "json": {
                "risk_score": 25,
                "risk_factors": [],
                "recommended_action": "SUBMIT_AS_IS",
            },
            "provider": "mock",
            "model": "mock",
            "latency_ms": 1,
            "prompt_tokens": 1,
            "completion_tokens": 1,
        }

        state = _base_state(status="AUDIT_COMPLETE", audit_confidence=0.92)
        result = await denial_prediction(state)

        assert result["status"] == "PREDICTION_COMPLETE"
        assert 0 <= result["denial_risk_score"] <= 100
        assert result["recommended_action"] in (
            "SUBMIT_AS_IS", "CORRECT_AND_RESUBMIT", "ESCALATE_TO_HUMAN"
        )

    def test_ready_for_submission_sets_status(self):
        state = _base_state()
        result = ready_for_submission(state)
        assert result["status"] == "READY_FOR_SUBMISSION"

    @pytest.mark.asyncio
    @patch("backend.agents.appeal_drafting.retrieve_with_scores")
    @patch("backend.agents.appeal_drafting.query_llm")
    async def test_appeal_drafting_returns_letter(self, mock_query_llm, mock_retrieve):
        mock_retrieve.return_value = []
        mock_query_llm.side_effect = RuntimeError("Not configured")  # trigger fallback

        state = _base_state(status="DENIED", denial_reason_code="CO-4")
        result = await appeal_drafting(state)

        assert result["status"] == "APPEAL_DRAFT_READY"
        assert "APPEAL LETTER" in result["appeal_letter_content"]
        assert result["appeal_status"] == "DRAFT"

    def test_human_review_flags_claim(self):
        state = _base_state(status="AUDIT_COMPLETE", audit_confidence=0.55)
        result = human_review(state)
        assert result["status"] == "HUMAN_REVIEW_REQUIRED"
        assert result["human_review_flag"] is True
        assert "0.55" in result["human_review_reason"]


# ═══════════════════════════════════════════════════════════════
# Graph Compilation Test
# ═══════════════════════════════════════════════════════════════

class TestGraphCompilation:
    """Test that the graph compiles and can be invoked."""

    def test_graph_compiles(self):
        from backend.agents.graph import build_graph
        graph = build_graph()
        compiled = graph.compile()
        assert compiled is not None

    @pytest.mark.asyncio
    @patch("backend.agents.denial_prediction.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.query_llm")
    @patch("backend.agents.code_audit.retrieve_with_scores")
    @patch("backend.agents.code_audit.query_llm")
    async def test_happy_path_traversal(
        self,
        mock_audit_llm,
        mock_audit_retrieve,
        mock_pred_llm,
        mock_pred_retrieve,
    ):
        """Test the full happy path: RECEIVED → READY_FOR_SUBMISSION."""
        from backend.agents.graph import build_graph

        # Mock code audit
        mock_audit_retrieve.return_value = []
        mock_audit_llm.return_value = {
            "content": "ok",
            "json": {
                "findings": [],
                "overall_confidence": 0.92,
                "summary": "Clean audit",
            },
            "provider": "mock", "model": "mock",
            "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1,
        }

        # Mock denial prediction
        mock_pred_retrieve.return_value = []
        mock_pred_llm.return_value = {
            "content": "ok",
            "json": {
                "risk_score": 25,
                "risk_factors": [],
                "recommended_action": "SUBMIT_AS_IS",
            },
            "provider": "mock", "model": "mock",
            "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1,
        }

        compiled = build_graph().compile()
        initial_state = _base_state(status="RECEIVED")

        result = await compiled.ainvoke(initial_state)

        assert result["status"] == "READY_FOR_SUBMISSION"

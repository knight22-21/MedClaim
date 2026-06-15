"""
MedClaim — Denial Prediction Agent Tests

Tests the prediction agent including RAG formatting,
LLM JSON parsing, risk score clamping, and metric emissions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from backend.agents.denial_prediction import _format_denial_patterns, run_denial_prediction

if TYPE_CHECKING:
    from backend.agents.state import ClaimState


def _make_state(**overrides) -> ClaimState:
    """Create a minimal ClaimState for prediction testing."""
    state: ClaimState = {
        "claim_id": "predict-test-001",
        "patient_name": "John Doe",
        "patient_dob": "1980-01-01",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": "2024-01-15",
        "facility_type": "physician_office",
        "diagnosis_codes": [{"code": "J18.9"}],
        "procedure_codes": [{"code": "99214"}],
        "billed_amount": 150.00,
        "market": "US",
        "status": "AUDIT_COMPLETE",
        "audit_confidence": 0.95,
        "audit_findings": [],
        "audit_summary": "Clean audit",
        "current_agent": "code_audit",
        "retry_count": 0,
        "total_prompt_tokens": 500,
        "total_completion_tokens": 100,
        "total_latency_ms": 1000,
        "llm_calls": [],
        "processing_errors": [],
    }
    state.update(overrides)
    return state


# ═══════════════════════════════════════════════════════════════
# RAG Formatting Tests
# ═══════════════════════════════════════════════════════════════


class TestRAGFormatting:
    def test_empty_results_returns_default(self):
        result = _format_denial_patterns([])
        assert "No historical denial patterns found" in result

    def test_formatting_with_metadata(self):
        class MockDoc:
            def __init__(self, content, metadata):
                self.page_content = content
                self.metadata = metadata

        docs = [
            (
                MockDoc(
                    "Procedure lacks prior authorization.",
                    {"payer_name": "Medicare", "denial_code": "CO-16", "outcome": "DENIED"},
                ),
                0.85,
            )
        ]

        formatted = _format_denial_patterns(docs)
        assert "[1] Payer: Medicare" in formatted
        assert "Denial Code: CO-16" in formatted
        assert "Outcome: DENIED" in formatted
        assert "Similarity: 0.8500" in formatted
        assert "Procedure lacks prior authorization" in formatted


# ═══════════════════════════════════════════════════════════════
# Agent Logic Tests (Mocked)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDenialPredictionAgent:
    @patch("backend.agents.denial_prediction.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.query_llm")
    @patch("backend.agents.denial_prediction.DENIALS_PREDICTED")
    async def test_low_risk_prediction(self, mock_metric, mock_query_llm, mock_retrieve):
        """Test a successful low-risk prediction."""
        mock_retrieve.return_value = []
        mock_query_llm.return_value = {
            "content": "raw",
            "json": {"risk_score": 15, "risk_factors": [], "recommended_action": "SUBMIT_AS_IS"},
            "provider": "groq",
            "model": "llama-3",
            "latency_ms": 200,
            "prompt_tokens": 1000,
            "completion_tokens": 50,
        }

        state = _make_state()
        result = await run_denial_prediction(state)

        assert result["status"] == "PREDICTION_COMPLETE"
        assert result["denial_risk_score"] == 15
        assert result["recommended_action"] == "SUBMIT_AS_IS"
        assert len(result["risk_factors"]) == 0

        # LLMOps
        assert result["total_prompt_tokens"] == state["total_prompt_tokens"] + 1000
        assert len(result["llm_calls"]) == 1

        # Metric
        mock_metric.labels.assert_called_with(risk_level="low", market="US")
        mock_metric.labels().inc.assert_called_once()

    @patch("backend.agents.denial_prediction.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.query_llm")
    async def test_high_risk_prediction_and_clamping(self, mock_query_llm, mock_retrieve):
        """Test a high-risk prediction where the score is out of bounds (>100)."""
        mock_retrieve.return_value = []
        mock_query_llm.return_value = {
            "content": "raw",
            "json": {
                "risk_score": 150,  # Should be clamped to 100
                "risk_factors": [
                    {"factor": "Missing Modifier", "weight": 0.8, "description": "Need mod 25"}
                ],
                "recommended_action": "CORRECT_AND_RESUBMIT",
            },
            "latency_ms": 200,
        }

        state = _make_state()
        result = await run_denial_prediction(state)

        assert result["denial_risk_score"] == 100  # Clamped
        assert result["recommended_action"] == "CORRECT_AND_RESUBMIT"
        assert len(result["risk_factors"]) == 1
        assert result["risk_factors"][0]["factor"] == "Missing Modifier"

    @patch("backend.agents.denial_prediction.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.query_llm")
    async def test_invalid_action_fallback(self, mock_query_llm, mock_retrieve):
        """Test that an invalid recommended_action falls back to SUBMIT_AS_IS."""
        mock_retrieve.return_value = []
        mock_query_llm.return_value = {
            "content": "raw",
            "json": {"risk_score": 40, "recommended_action": "DO_SOMETHING_WEIRD"},
            "latency_ms": 200,
        }

        state = _make_state()
        result = await run_denial_prediction(state)

        assert result["recommended_action"] == "SUBMIT_AS_IS"

    @patch("backend.agents.denial_prediction.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.query_llm")
    async def test_agent_failure_fallback(self, mock_query_llm, mock_retrieve):
        """Test that if the LLM query fails, the agent falls back to moderate risk/human review."""
        mock_retrieve.return_value = []
        mock_query_llm.side_effect = RuntimeError("LLM is down")

        state = _make_state()
        result = await run_denial_prediction(state)

        assert result["status"] == "PREDICTION_COMPLETE"
        assert result["denial_risk_score"] == 55
        assert result["recommended_action"] == "ESCALATE_TO_HUMAN"
        assert len(result["processing_errors"]) == 1
        assert "LLM is down" in result["processing_errors"][0]


# ═══════════════════════════════════════════════════════════════
# Graph Integration Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDenialPredictionGraphIntegration:
    """Test how prediction outputs affect graph routing."""

    @patch("backend.agents.code_audit.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.retrieve_with_scores")
    @patch("backend.agents.denial_prediction.query_llm")
    async def test_low_risk_routes_to_ready(
        self,
        mock_query_llm,
        mock_prediction_retrieve,
        mock_code_audit_retrieve,
    ):
        from backend.agents.graph import build_graph

        compiled = build_graph().compile()

        # Mock ALL vector retrievals
        mock_prediction_retrieve.return_value = []
        mock_code_audit_retrieve.return_value = []

        # Mock prediction LLM
        mock_query_llm.return_value = {
            "json": {"risk_score": 25, "recommended_action": "SUBMIT_AS_IS"},
            "latency_ms": 100,
        }

        state = _make_state(status="AUDIT_COMPLETE", audit_confidence=0.95)

        result = await compiled.ainvoke(state)

        assert result["status"] == "READY_FOR_SUBMISSION"

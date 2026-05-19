"""
MedClaim — Code Audit Agent Tests

Tests the code audit agent, including RAG retrieval formatting,
LLM query parameters, response parsing, and state updates.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.code_audit import run_code_audit, _format_rag_docs
from backend.agents.state import ClaimState


def _make_state(**overrides) -> ClaimState:
    """Create a minimal ClaimState for code audit testing."""
    state: ClaimState = {
        "claim_id": "audit-test-001",
        "patient_name": "Jane Doe",
        "patient_dob": "1990-05-15",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": "2024-01-10",
        "facility_type": "physician_office",
        "diagnosis_codes": [{"code": "J18.9", "description": "Pneumonia, unspecified organism"}],
        "procedure_codes": [{"code": "99215", "description": "Office visit, high complexity"}],
        "billed_amount": 350.00,
        "market": "US",
        "status": "ELIGIBILITY_VERIFIED",
        "current_agent": "eligibility_check",
        "retry_count": 0,
        "human_review_flag": False,
        "total_prompt_tokens": 100,
        "total_completion_tokens": 50,
        "total_latency_ms": 200,
        "llm_calls": [],
    }
    state.update(overrides)
    return state


# ═══════════════════════════════════════════════════════════════
# RAG Formatting Tests
# ═══════════════════════════════════════════════════════════════

class TestRAGFormatting:
    """Test that Qdrant RAG docs are formatted cleanly for LLM consumption."""

    def test_empty_results_returns_default(self):
        assert "No matching guidelines" in _format_rag_docs([])

    def test_formatting_with_metadata(self):
        class MockDoc:
            def __init__(self, content, metadata):
                self.page_content = content
                self.metadata = metadata

        docs = [
            (MockDoc("Verify high-level E/M matches documentation.", {
                "guideline_source": "CMS",
                "clinical_topic": "E/M Coding Guidelines"
            }), 0.88),
            (MockDoc("Unbundling code 99215 and 93000 is prohibited.", {
                "payer_name": "Medicare",
                "policy_type": "LCD"
            }), 0.76)
        ]

        formatted = _format_rag_docs(docs)
        assert "[1] Source: CMS" in formatted
        assert "E/M Coding Guidelines" in formatted
        assert "Similarity Score: 0.8800" in formatted
        assert "Verify high-level" in formatted
        assert "[2] Source: Medicare" in formatted
        assert "prohibited" in formatted.lower()


# ═══════════════════════════════════════════════════════════════
# Agent Logic Tests (Mocked LLM & RAG)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestCodeAuditAgent:
    """Test code audit logic with mocked LLM queries and RAG retrieval."""

    @patch("backend.agents.code_audit.retrieve_with_scores")
    @patch("backend.agents.code_audit.query_llm")
    async def test_audit_successful_findings(self, mock_query_llm, mock_retrieve):
        """Test a successful audit where LLM identifies upcoding."""
        # 1. Mock RAG retrievals to return empty
        mock_retrieve.return_value = []

        # 2. Mock LLM query response
        mock_query_llm.return_value = {
            "content": "raw content",
            "json": {
                "findings": [
                    {
                        "code": "99215",
                        "issue_type": "UPCODING",
                        "severity": "HIGH",
                        "description": "Level 5 E/M billed but documentation only supports Level 3.",
                        "suggested_correction": "Downcode to 99213",
                        "confidence": 0.95
                    }
                ],
                "overall_confidence": 0.92,
                "summary": "Upcoding detected on primary procedure."
            },
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "latency_ms": 350,
            "prompt_tokens": 1200,
            "completion_tokens": 150,
        }

        state = _make_state()
        result = await run_code_audit(state)

        # Verify state updates
        assert result["status"] == "AUDIT_COMPLETE"
        assert result["current_agent"] == "code_audit"
        assert len(result["audit_findings"]) == 1
        assert result["audit_findings"][0]["issue_type"] == "UPCODING"
        assert result["audit_confidence"] == 0.92
        assert "Upcoding detected" in result["audit_summary"]

        # Verify LLMOps telemetry accumulated
        assert result["total_prompt_tokens"] == state["total_prompt_tokens"] + 1200
        assert result["total_completion_tokens"] == state["total_completion_tokens"] + 150
        assert len(result["llm_calls"]) == 1
        assert result["llm_calls"][0]["agent"] == "code_audit"
        assert result["llm_calls"][0]["latency_ms"] > 0

    @patch("backend.agents.code_audit.retrieve_with_scores")
    @patch("backend.agents.code_audit.query_llm")
    async def test_audit_failure_fallback(self, mock_query_llm, mock_retrieve):
        """Test that if the LLM query fails, the agent falls back cleanly."""
        mock_retrieve.return_value = []
        mock_query_llm.side_effect = RuntimeError("API key invalid")

        state = _make_state()
        result = await run_code_audit(state)

        # Verify clean audit fallback
        assert result["status"] == "AUDIT_COMPLETE"
        assert len(result["audit_findings"]) == 0
        assert result["audit_confidence"] == 0.85
        assert "fallback" in result["audit_summary"].lower()
        assert len(result["processing_errors"]) == 1

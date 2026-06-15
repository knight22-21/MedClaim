"""
MedClaim — Eligibility Agent Tests

Tests the eligibility verification service and agent against
the fixture scenarios in data/eligibility_fixtures.yaml.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.agents.eligibility import run_eligibility_check
from backend.app.services.eligibility_service import (
    get_payer_info,
    verify_eligibility,
)

if TYPE_CHECKING:
    from backend.agents.state import ClaimState


def _make_state(**overrides) -> ClaimState:
    """Create a minimal ClaimState for eligibility testing."""
    state: ClaimState = {
        "claim_id": "elig-test-001",
        "patient_name": "Test Patient",
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
        "retry_count": 0,
        "human_review_flag": False,
        "processing_errors": [],
    }
    state.update(overrides)
    return state


# ═══════════════════════════════════════════════════════════════
# Payer Directory Tests
# ═══════════════════════════════════════════════════════════════


class TestPayerDirectory:
    """Test payer directory loading and lookup."""

    def test_us_medicare_found(self):
        payer = get_payer_info("MCR-001", "US")
        assert payer is not None
        assert "Medicare" in payer["name"]

    def test_us_bcbs_found(self):
        payer = get_payer_info("BCBS-100", "US")
        assert payer is not None
        assert "Blue Cross" in payer["name"]

    def test_india_star_health_found(self):
        payer = get_payer_info("STAR-IN-001", "INDIA")
        assert payer is not None
        assert "Star Health" in payer["name"]

    def test_india_pmjay_found(self):
        payer = get_payer_info("PMJAY-001", "INDIA")
        assert payer is not None
        assert "PM-JAY" in payer["name"] or "Ayushman" in payer["name"]

    def test_unknown_payer_returns_none(self):
        payer = get_payer_info("FAKE-999", "US")
        assert payer is None


# ═══════════════════════════════════════════════════════════════
# Eligibility Service Tests
# ═══════════════════════════════════════════════════════════════


class TestEligibilityService:
    """Test the verify_eligibility function against fixture scenarios."""

    def test_us_medicare_active_coverage(self):
        """Fixture: MCR-001, DOB 1985-03-15, procedure 99213 → all pass."""
        result = verify_eligibility(
            payer_id="MCR-001",
            payer_name="Medicare",
            patient_dob="1985-03-15",
            procedure_codes=[{"code": "99213"}],
            market="US",
        )
        assert result["is_eligible"] is True
        assert result["coverage_active"] is True
        assert result["procedure_covered"] is True
        assert result["provider_in_network"] is True

    def test_us_medicare_inactive_coverage(self):
        """Fixture: MCR-001, DOB 1978-12-01, procedure 99213 → coverage inactive."""
        result = verify_eligibility(
            payer_id="MCR-001",
            payer_name="Medicare",
            patient_dob="1978-12-01",
            procedure_codes=[{"code": "99213"}],
            market="US",
        )
        assert result["is_eligible"] is False
        assert result["coverage_active"] is False
        assert "inactive" in result["failure_reason"].lower()

    def test_us_bcbs_out_of_network(self):
        """Fixture: BCBS-100, DOB 1985-03-15, procedure 99213 → out of network."""
        result = verify_eligibility(
            payer_id="BCBS-100",
            payer_name="Blue Cross Blue Shield",
            patient_dob="1985-03-15",
            procedure_codes=[{"code": "99213"}],
            market="US",
        )
        assert result["is_eligible"] is False
        assert result["provider_in_network"] is False
        assert "network" in result["failure_reason"].lower()

    def test_us_bcbs_uncovered_procedure(self):
        """Fixture: BCBS-100, DOB 1992-05-10, procedure 69990 → not covered."""
        result = verify_eligibility(
            payer_id="BCBS-100",
            payer_name="Blue Cross Blue Shield",
            patient_dob="1992-05-10",
            procedure_codes=[{"code": "69990"}],
            market="US",
        )
        assert result["is_eligible"] is False
        assert result["procedure_covered"] is False
        assert "not covered" in result["failure_reason"].lower()

    def test_india_pmjay_covered_hbp(self):
        """Fixture: PMJAY-001, DOB 1995-02-28, HBP-1201 → all pass."""
        result = verify_eligibility(
            payer_id="PMJAY-001",
            payer_name="Ayushman Bharat PM-JAY",
            patient_dob="1995-02-28",
            procedure_codes=[{"code": "HBP-1201"}],
            market="INDIA",
        )
        assert result["is_eligible"] is True
        assert result["procedure_covered"] is True

    def test_india_pmjay_non_hbp_procedure(self):
        """Fixture: PMJAY-001, DOB 2000-09-05, HBP-9999 → not in HBP list."""
        result = verify_eligibility(
            payer_id="PMJAY-001",
            payer_name="Ayushman Bharat PM-JAY",
            patient_dob="2000-09-05",
            procedure_codes=[{"code": "HBP-9999"}],
            market="INDIA",
        )
        assert result["is_eligible"] is False
        assert result["procedure_covered"] is False

    def test_unknown_payer_uses_defaults(self):
        """Unknown payer falls back to defaults → eligible."""
        result = verify_eligibility(
            payer_id="FAKE-999",
            payer_name="Unknown Payer",
            patient_dob="1990-01-01",
            procedure_codes=[{"code": "99213"}],
            market="US",
        )
        assert result["is_eligible"] is True
        assert result["raw_response"]["fixture_matched"] is False


# ═══════════════════════════════════════════════════════════════
# Eligibility Agent Tests
# ═══════════════════════════════════════════════════════════════


class TestEligibilityAgent:
    """Test the full agent function that integrates into the LangGraph."""

    def test_eligible_claim_returns_verified(self):
        state = _make_state(
            payer_id="MCR-001",
            patient_dob="1985-03-15",
            procedure_codes=[{"code": "99213"}],
        )
        result = run_eligibility_check(state)
        assert result["status"] == "ELIGIBILITY_VERIFIED"
        assert result["eligibility_status"] == "VERIFIED"
        assert result["current_agent"] == "eligibility_check"

    def test_ineligible_claim_returns_failed(self):
        state = _make_state(
            payer_id="MCR-001",
            patient_dob="1978-12-01",
            procedure_codes=[{"code": "99213"}],
        )
        result = run_eligibility_check(state)
        assert result["status"] == "ELIGIBILITY_FAILED"
        assert result["eligibility_status"] == "FAILED"
        assert result["human_review_flag"] is True
        assert "Eligibility failed" in result["human_review_reason"]

    def test_india_eligible_claim(self):
        state = _make_state(
            payer_id="PMJAY-001",
            payer_name="Ayushman Bharat PM-JAY",
            patient_dob="1995-02-28",
            procedure_codes=[{"code": "HBP-1201"}],
            market="INDIA",
        )
        result = run_eligibility_check(state)
        assert result["status"] == "ELIGIBILITY_VERIFIED"


# ═══════════════════════════════════════════════════════════════
# Graph Integration Tests
# ═══════════════════════════════════════════════════════════════


class TestEligibilityGraphIntegration:
    """Test that eligibility results flow correctly through the graph."""

    async def test_eligible_claim_reaches_code_audit(self):
        """An eligible claim should flow: eligibility → code_audit → ... → ready."""
        from backend.agents.graph import build_graph

        compiled = build_graph().compile()
        state = _make_state(
            payer_id="MCR-001",
            patient_dob="1985-03-15",
            procedure_codes=[{"code": "99213"}],
        )

        result = await compiled.ainvoke(state)
        # With placeholders for audit (0.92 confidence) and prediction (risk=25),
        # an eligible claim should reach READY_FOR_SUBMISSION
        assert result["status"] == "READY_FOR_SUBMISSION"

    def test_ineligible_claim_stops_at_failed(self):
        """An ineligible claim should stop at ELIGIBILITY_FAILED."""
        from backend.agents.graph import build_graph

        compiled = build_graph().compile()
        state = _make_state(
            payer_id="MCR-001",
            patient_dob="1978-12-01",
            procedure_codes=[{"code": "99213"}],
        )

        result = compiled.invoke(state)
        assert result["status"] == "ELIGIBILITY_FAILED"
        assert result["human_review_flag"] is True

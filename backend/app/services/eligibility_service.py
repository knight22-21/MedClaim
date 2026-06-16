"""
MedClaim — Eligibility Verification Service

Loads payer directory and eligibility fixtures from YAML, then
verifies patient insurance coverage by matching (payer_id, patient_dob,
procedure_code) against known fixture scenarios.

In production, this would call the real payer eligibility API (X12 270/271).
For development/demo, we use the fixture-based mock.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from datetime import date

    from backend.agents.state import EligibilityResult

logger = logging.getLogger("medclaim.services.eligibility")

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


@lru_cache(maxsize=1)
def _load_payer_directory() -> dict[str, list[dict[str, Any]]]:
    """Load and cache payer_directory.yaml."""
    path = DATA_DIR / "payer_directory.yaml"
    if not path.exists():
        logger.warning("payer_directory.yaml not found at %s", path)
        return {"us_payers": [], "india_payers": []}

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info(
        "payer_directory loaded: %d US, %d India",
        len(data.get("us_payers", [])),
        len(data.get("india_payers", [])),
    )
    return data  # type: ignore[no-any-return]


@lru_cache(maxsize=1)
def _load_eligibility_fixtures() -> dict[str, Any]:
    """Load and cache eligibility_fixtures.yaml."""
    path = DATA_DIR / "eligibility_fixtures.yaml"
    if not path.exists():
        logger.warning("eligibility_fixtures.yaml not found at %s", path)
        return {"defaults": {}, "fixtures": []}

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info("eligibility_fixtures loaded: %d scenarios", len(data.get("fixtures", [])))
    return data  # type: ignore[no-any-return]


def get_payer_info(payer_id: str, market: str = "US") -> dict[str, Any] | None:
    """
    Look up a payer by ID from the payer directory.

    Args:
        payer_id: Payer identifier (e.g., "MCR-001").
        market: "US" or "INDIA".

    Returns:
        Payer dict or None if not found.
    """
    directory = _load_payer_directory()
    payer_list_key = "india_payers" if market.upper() == "INDIA" else "us_payers"
    payers = directory.get(payer_list_key, [])

    for payer in payers:
        if payer.get("id") == payer_id:
            return payer

    # Try the other market as fallback
    fallback_key = "us_payers" if payer_list_key == "india_payers" else "india_payers"
    for payer in directory.get(fallback_key, []):
        if payer.get("id") == payer_id:
            return payer

    return None


def _find_fixture_match(
    payer_id: str,
    patient_dob: str,
    procedure_code: str,
) -> dict[str, Any] | None:
    """
    Find an exact fixture match for the given parameters.

    Matching priority:
        1. Exact match on (payer_id, patient_dob, procedure_code)
        2. Partial match on (payer_id, procedure_code) — any DOB
        3. Partial match on (payer_id) — any DOB/procedure
        4. None — use defaults
    """
    data = _load_eligibility_fixtures()
    fixtures = data.get("fixtures", [])

    # Priority 1: Exact match
    for fix in fixtures:
        if (
            fix.get("payer_id") == payer_id
            and fix.get("patient_dob") == patient_dob
            and fix.get("procedure_code") == procedure_code
        ):
            return fix  # type: ignore[no-any-return]

    # Priority 2: Match payer + procedure (ignore DOB)
    for fix in fixtures:
        if fix.get("payer_id") == payer_id and fix.get("procedure_code") == procedure_code:
            return fix  # type: ignore[no-any-return]

    # Priority 3: Match payer only
    for fix in fixtures:
        if fix.get("payer_id") == payer_id:
            return fix  # type: ignore[no-any-return]

    return None


def verify_eligibility(
    payer_id: str,
    payer_name: str,
    patient_dob: str | date,
    procedure_codes: list[dict[str, Any]],
    market: str = "US",
) -> EligibilityResult:
    """
    Verify patient insurance eligibility.

    Checks:
        1. Payer exists in payer directory
        2. Coverage is active on date of service
        3. Primary procedure is covered under the plan
        4. Provider is in-network

    Args:
        payer_id: Payer identifier.
        payer_name: Payer display name (for logging).
        patient_dob: Patient date of birth (ISO format string or date).
        procedure_codes: List of procedure code dicts with 'code' key.
        market: "US" or "INDIA".

    Returns:
        EligibilityResult with verification details.
    """
    dob_str = str(patient_dob)
    primary_procedure = procedure_codes[0]["code"] if procedure_codes else ""

    logger.info(
        "eligibility.verify_start | payer=%s dob=%s procedure=%s market=%s",
        payer_id,
        dob_str,
        primary_procedure,
        market,
    )

    # Step 1: Validate payer exists
    payer_info = get_payer_info(payer_id, market)
    if not payer_info:
        logger.warning("eligibility.payer_not_found | payer_id=%s", payer_id)
        # Unknown payer — fall through to defaults (don't fail)

    # Step 2: Look up fixture match
    fixture = _find_fixture_match(payer_id, dob_str, primary_procedure)

    if fixture:
        # Use fixture response
        coverage_active = fixture.get("coverage_active", True)
        procedure_covered = fixture.get("procedure_covered", True)
        provider_in_network = fixture.get("provider_in_network", True)
        response_msg = fixture.get("response_message", "")

        logger.info(
            "eligibility.fixture_matched | payer=%s active=%s covered=%s in_network=%s",
            payer_id,
            coverage_active,
            procedure_covered,
            provider_in_network,
        )
    else:
        # Use defaults — assume eligible
        defaults = _load_eligibility_fixtures().get("defaults", {})
        coverage_active = defaults.get("coverage_active", True)
        procedure_covered = defaults.get("procedure_covered", True)
        provider_in_network = defaults.get("provider_in_network", True)
        response_msg = "No specific fixture found; using defaults."

        logger.info("eligibility.using_defaults | payer=%s", payer_id)

    # Step 3: Determine overall eligibility
    is_eligible = coverage_active and procedure_covered and provider_in_network

    # Build failure reason
    failure_reasons = []
    if not coverage_active:
        failure_reasons.append("Coverage inactive on date of service")
    if not procedure_covered:
        failure_reasons.append(f"Procedure {primary_procedure} not covered under plan")
    if not provider_in_network:
        failure_reasons.append("Provider is out of network for this plan")

    failure_reason = "; ".join(failure_reasons) if failure_reasons else ""

    result: EligibilityResult = {
        "is_eligible": is_eligible,
        "coverage_active": coverage_active,
        "procedure_covered": procedure_covered,
        "provider_in_network": provider_in_network,
        "failure_reason": failure_reason,
        "raw_response": {
            "payer_id": payer_id,
            "payer_name": payer_name,
            "fixture_matched": fixture is not None,
            "response_message": response_msg,
            "market": market,
        },
    }

    logger.info(
        "eligibility.verify_complete | payer=%s eligible=%s reason=%s",
        payer_id,
        is_eligible,
        failure_reason or "none",
    )

    return result

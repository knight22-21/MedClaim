"""
MedClaim — Claim Pipeline State

Defines the ClaimState TypedDict that flows through the entire
LangGraph processing pipeline. Every node reads from and writes
to this shared state object.

Architecture Note:
    LangGraph merges partial state updates from each node via
    reducer functions. Each node returns only the keys it modifies.
"""

from __future__ import annotations

from typing import Any, TypedDict


class EligibilityResult(TypedDict, total=False):
    """Result from the Eligibility Verification Agent."""
    is_eligible: bool
    coverage_active: bool
    procedure_covered: bool
    provider_in_network: bool
    failure_reason: str
    raw_response: dict[str, Any]


class AuditFinding(TypedDict, total=False):
    """A single finding from the Code Audit Agent."""
    code: str
    issue_type: str          # UPCODING, UNBUNDLING, MISSING_MODIFIER, INCORRECT_DX
    severity: str            # HIGH, MEDIUM, LOW
    description: str
    suggested_correction: str
    confidence: float


class RiskFactor(TypedDict, total=False):
    """A single risk factor from Denial Prediction."""
    factor: str
    weight: float
    description: str


class ClaimState(TypedDict, total=False):
    """
    Shared state flowing through the LangGraph claim processing pipeline.

    Every agent node reads relevant fields and returns a partial dict
    updating only the fields it is responsible for. LangGraph merges
    these updates automatically.

    Field Groups:
        1. Claim Identity — from the ingested claim
        2. Eligibility — set by EligibilityAgent
        3. Code Audit — set by CodeAuditAgent
        4. Denial Prediction — set by DenialPredictionAgent
        5. Appeal — set by AppealDraftingAgent
        6. Pipeline Control — used by the Supervisor for routing
        7. LLMOps — metrics collected per-node for observability
    """

    # ── 1. Claim Identity ────────────────────────────────────
    claim_id: str
    patient_name: str
    patient_dob: str
    payer_name: str
    payer_id: str
    date_of_service: str
    facility_type: str
    diagnosis_codes: list[dict[str, Any]]
    procedure_codes: list[dict[str, Any]]
    billed_amount: float
    market: str                         # "US" or "INDIA"

    # ── 2. Eligibility ───────────────────────────────────────
    eligibility_result: EligibilityResult
    eligibility_status: str             # VERIFIED, FAILED

    # ── 3. Code Audit ────────────────────────────────────────
    audit_findings: list[AuditFinding]
    audit_confidence: float             # 0.0 – 1.0
    audit_summary: str
    codes_corrected: bool               # True if corrections were applied

    # ── 4. Denial Prediction ─────────────────────────────────
    denial_risk_score: int              # 0 – 100
    risk_factors: list[RiskFactor]
    recommended_action: str             # SUBMIT_AS_IS, CORRECT_AND_RESUBMIT, ESCALATE_TO_HUMAN

    # ── 5. Appeal ────────────────────────────────────────────
    denial_reason_code: str
    denial_reason_desc: str
    appeal_letter_content: str
    appeal_supporting_docs: list[str]
    appeal_status: str                  # DRAFT, APPROVED, SUBMITTED

    # ── 6. Pipeline Control ──────────────────────────────────
    status: str                         # Current ClaimStatus value
    current_agent: str                  # Name of the active node
    previous_agent: str                 # Name of the previous node
    retry_count: int                    # Correction loop counter (max 2)
    human_review_flag: bool
    human_review_reason: str
    processing_errors: list[str]        # Accumulated error messages

    # ── 7. LLMOps Telemetry ──────────────────────────────────
    total_prompt_tokens: int
    total_completion_tokens: int
    total_latency_ms: int
    llm_calls: list[dict[str, Any]]     # Per-call metadata for LangSmith

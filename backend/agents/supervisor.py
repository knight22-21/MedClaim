"""
MedClaim — Supervisor Agent (LangGraph Orchestrator)

The Supervisor is the root node of the LangGraph StateGraph.
It uses deterministic conditional edges (no LLM calls) to route
claims through the processing pipeline based on ClaimState values.

Routing Logic:
    RECEIVED            → EligibilityAgent
    ELIGIBILITY_VERIFIED → CodeAuditAgent
    AUDIT_COMPLETE (confidence >= 0.80) → DenialPredictionAgent
    AUDIT_COMPLETE (confidence <  0.80) → HumanReviewQueue
    denial_risk_score > 70  → CodeAuditAgent (correction loop)
    denial_risk_score <= 70 → READY_FOR_SUBMISSION
    DENIED              → AppealDraftingAgent

Implementation: Subphase 2.1
"""

"""
MedClaim — Appeal Drafting Agent

Drafts a formal appeal letter for a denied claim.
Retrieves payer policies and clinical guidelines via RAG,
then generates a highly structured and cited appeal letter using Gemini
(preferred for long-context generation).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog

from backend.agents.llm import query_llm
from backend.prompts.loader import render_prompt
from backend.rag.retrievers import retrieve_with_scores

if TYPE_CHECKING:
    from backend.agents.state import ClaimState

logger = structlog.get_logger("medclaim.agents.appeal_drafting")


def _format_docs_for_appeal(results: list[tuple[Any, float]], doc_type: str) -> str:
    """Format RAG search results specifically for appeal citations."""
    if not results:
        return f"No relevant {doc_type} found in knowledge base."

    formatted = []
    for idx, (doc, score) in enumerate(results, 1):
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        meta = doc.metadata if hasattr(doc, "metadata") else {}

        source = meta.get("source", meta.get("payer_name", "Unknown Source"))
        title = meta.get("title", meta.get("policy_type", "Document"))

        formatted.append(
            f"[{idx}] Source: {source} | Title: {title} (Sim: {score:.4f})\nText: {content}\n---"
        )
    return "\n".join(formatted)


async def run_appeal_drafting(state: ClaimState) -> dict[str, Any]:
    """
    Execute the Appeal Drafting Agent.

    Args:
        state: Current pipeline state (must include denial details).

    Returns:
        Partial state update containing the drafted letter and citations.
    """
    claim_id = state.get("claim_id", "unknown")
    market = state.get("market", "US")
    payer_name = state.get("payer_name", "Unknown Payer")
    diagnosis_codes = state.get("diagnosis_codes", [])
    procedure_codes = state.get("procedure_codes", [])
    denial_reason_code = state.get("denial_reason_code", "UNKNOWN")
    denial_reason_desc = state.get("denial_reason_desc", "No description provided")

    start_time = time.time()
    logger.info("agent.appeal_drafting.start", claim_id=claim_id, denial_code=denial_reason_code)

    # ── Step 1: RAG retrieval for policies and guidelines ────
    dx_terms = " ".join([dx.get("code", "") for dx in diagnosis_codes])
    px_terms = " ".join([px.get("code", "") for px in procedure_codes])

    # Query for payer policies
    policy_query = f"{payer_name} {dx_terms} {px_terms} {denial_reason_code}".strip()
    try:
        policy_docs = retrieve_with_scores(
            collection_name="payer_policies",
            query=policy_query,
            top_k=4,
            filter_kwargs={"market": market, "payer_name": payer_name},
        )
    except Exception as e:
        logger.warning(
            "agent.appeal_drafting.rag_failed", collection="payer_policies", error=str(e)
        )
        policy_docs = []

    # Query for clinical guidelines
    guideline_query = f"{dx_terms} {px_terms} medical necessity standard of care".strip()
    try:
        guideline_docs = retrieve_with_scores(
            collection_name="clinical_guidelines",
            query=guideline_query,
            top_k=4,
            filter_kwargs={"market": market},
        )
    except Exception as e:
        logger.warning(
            "agent.appeal_drafting.rag_failed", collection="clinical_guidelines", error=str(e)
        )
        guideline_docs = []

    policy_context = _format_docs_for_appeal(policy_docs, "payer policies")
    guideline_context = _format_docs_for_appeal(guideline_docs, "clinical guidelines")

    # ── Step 2: Render prompt ────────────────────────────────
    prompt_context = {
        "market": market,
        "payer_name": payer_name,
        "patient_name": state.get("patient_name", "Unknown"),
        "date_of_service": state.get("date_of_service", "Unknown"),
        "facility_type": state.get("facility_type", "physician_office"),
        "billed_amount": state.get("billed_amount", 0.0),
        "claim_id": claim_id,
        "denial_reason_code": denial_reason_code,
        "denial_reason_desc": denial_reason_desc,
        "diagnosis_codes": diagnosis_codes,
        "procedure_codes": procedure_codes,
        "payer_policy_context": policy_context,
        "clinical_guideline_context": guideline_context,
    }

    try:
        user_prompt = render_prompt("appeal_letter", prompt_context)
        system_prompt = (
            "You are an expert medical billing appeals specialist. "
            "Write a formal appeal letter that cites specific clinical evidence, "
            "payer policy language, and regulatory guidelines to overturn the denial. "
            "Return strict structured JSON."
        )

        # ── Step 3: Query LLM ────────────────────────────────
        # Prefer Gemini (google) for drafting appeals due to long context and narrative quality
        llm_response = await query_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            preferred_provider="google",
            temperature=0.3,  # Slightly higher temperature for better narrative flow
            json_mode=True,
        )

        # ── Step 4: Parse response ───────────────────────────
        appeal_json = llm_response.get("json") or {}

        letter_content = appeal_json.get(
            "letter_content", "Error: Failed to generate letter content."
        )
        supporting_docs = appeal_json.get("supporting_documents", [])
        cited_policies = appeal_json.get("cited_policies", [])
        appeal_json.get("cited_guidelines", [])

        latency = int((time.time() - start_time) * 1000)

        logger.info(
            "agent.appeal_drafting.complete",
            claim_id=claim_id,
            letter_length=len(letter_content),
            policies_cited=len(cited_policies),
            latency_ms=latency,
        )

        # Track LLMOps
        prompt_tokens = llm_response.get("prompt_tokens", 0)
        completion_tokens = llm_response.get("completion_tokens", 0)

        return {
            "appeal_letter_content": letter_content,
            "appeal_supporting_docs": supporting_docs,
            "appeal_status": "DRAFT",
            "status": "APPEAL_DRAFT_READY",
            "current_agent": "appeal_drafting",
            "total_prompt_tokens": state.get("total_prompt_tokens", 0) + prompt_tokens,
            "total_completion_tokens": state.get("total_completion_tokens", 0) + completion_tokens,
            "total_latency_ms": state.get("total_latency_ms", 0) + latency,
            "llm_calls": state.get("llm_calls", [])
            + [
                {
                    "agent": "appeal_drafting",
                    "provider": llm_response.get("provider"),
                    "model": llm_response.get("model"),
                    "latency_ms": latency,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
            ],
        }

    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        logger.error(
            "agent.appeal_drafting.failed",
            claim_id=claim_id,
            error=str(e),
            latency_ms=latency,
        )

        fallback_letter = (
            f"APPEAL LETTER — Claim {claim_id}\n\n"
            f"Dear Claims Review Department,\n\n"
            f"We are writing to appeal the denial of claim {claim_id} "
            f"under denial reason code {denial_reason_code}.\n\n"
            f"[Agent failed to generate full appeal context: {str(e)}]\n\n"
            f"Respectfully submitted."
        )

        return {
            "appeal_letter_content": fallback_letter,
            "appeal_supporting_docs": [],
            "appeal_status": "DRAFT",
            "status": "APPEAL_DRAFT_READY",
            "current_agent": "appeal_drafting",
            "processing_errors": state.get("processing_errors", [])
            + [f"Appeal drafting error: {str(e)}"],
            "total_latency_ms": state.get("total_latency_ms", 0) + latency,
        }

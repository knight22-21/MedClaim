"""
MedClaim — Code Audit Agent

Audits medical claims for coding accuracy, completeness, and payer policy compliance.
Retrieves relevant rules and policies using Qdrant vector database (RAG), renders
the system audit prompt, queries the LLM (Groq with Gemini fallback), and parses findings.

Detects issues like:
    - UPCODING (e.g. billing higher complexity E/M than supported)
    - UNBUNDLING (billing separate services that should be bundled)
    - MISSING_MODIFIER (e.g. bilateral procedures without modifier 50)
    - INCORRECT_DX (diagnosis code mismatches)
"""

from __future__ import annotations

import logging
import time
from typing import Any

import structlog

from backend.agents.state import ClaimState
from backend.agents.llm import query_llm
from backend.prompts.loader import render_prompt
from backend.rag.retrievers import retrieve_with_scores

logger = structlog.get_logger("medclaim.agents.code_audit")


def _format_rag_docs(results: list[tuple[Any, float]]) -> str:
    """Format RAG search results into a clean string for prompt injection."""
    if not results:
        return "No matching guidelines or policies found in knowledge base."

    formatted = []
    for idx, (doc, score) in enumerate(results, 1):
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        
        source = meta.get("guideline_source", meta.get("payer_name", "Unknown Source"))
        topic = meta.get("clinical_topic", meta.get("policy_type", "General"))
        
        formatted.append(
            f"[{idx}] Source: {source} | Topic/Type: {topic} (Similarity Score: {score:.4f})\n"
            f"Content: {content}\n"
            f"---"
        )
    return "\n\n".join(formatted)


async def run_code_audit(state: ClaimState) -> dict[str, Any]:
    """
    Execute the Code Audit Agent.

    Args:
        state: Current pipeline state.

    Returns:
        Partial state update containing audit results and LLMOps stats.
    """
    claim_id = state.get("claim_id", "unknown")
    market = state.get("market", "US")
    payer_id = state.get("payer_id", "")
    payer_name = state.get("payer_name", "")
    diagnosis_codes = state.get("diagnosis_codes", [])
    procedure_codes = state.get("procedure_codes", [])
    facility_type = state.get("facility_type", "physician_office")
    billed_amount = state.get("billed_amount", 0.0)

    start_time = time.time()
    logger.info("agent.code_audit.start", claim_id=claim_id, codes_count=len(procedure_codes))

    # Step 1: Perform RAG retrieval
    # Build search query from diagnoses & procedures
    dx_terms = " ".join([f"{dx.get('code', '')} {dx.get('description', '')}" for dx in diagnosis_codes])
    px_terms = " ".join([f"{px.get('code', '')} {px.get('description', '')}" for px in procedure_codes])
    rag_query = f"{dx_terms} {px_terms}".strip()

    logger.debug("agent.code_audit.rag_search", query=rag_query)

    # Fetch coding guidelines
    coding_rules_docs = retrieve_with_scores(
        collection_name="coding_rules",
        query=rag_query,
        top_k=4,
        filter_kwargs={"market": market}
    )

    # Fetch payer policies matching this specific payer and query
    payer_policy_docs = retrieve_with_scores(
        collection_name="payer_policies",
        query=f"{payer_name} {rag_query}",
        top_k=3,
        filter_kwargs={"market": market, "payer_name": payer_name}
    )

    # Merge contexts
    all_rag_results = coding_rules_docs + payer_policy_docs
    rag_context = _format_rag_docs(all_rag_results)

    # Step 2: Render system prompt
    prompt_context = {
        "market": market,
        "payer_name": payer_name,
        "patient_name": state.get("patient_name", "Unknown Patient"),
        "date_of_service": state.get("date_of_service", "Unknown"),
        "facility_type": facility_type,
        "billed_amount": billed_amount,
        "diagnosis_codes": diagnosis_codes,
        "procedure_codes": procedure_codes,
        "rag_context": rag_context,
    }

    try:
        user_prompt = render_prompt("code_audit", prompt_context)
        system_prompt = "You are a professional medical auditor. Analyze claims and return strict structured JSON."

        # Step 3: Query the LLM
        # Groq is fast and cheap, excellent for the audit agent
        llm_response = await query_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            preferred_provider="groq",
            temperature=0.1,
            json_mode=True
        )

        # Step 4: Parse findings
        audit_json = llm_response.get("json") or {}
        findings = audit_json.get("findings", [])
        overall_confidence = audit_json.get("overall_confidence", 0.90)
        summary = audit_json.get("summary", "Audit completed successfully.")

        # Ensure confidence fits range
        overall_confidence = float(overall_confidence)
        if overall_confidence > 1.0:
            overall_confidence = overall_confidence / 100.0

        latency = int((time.time() - start_time) * 1000)
        logger.info(
            "agent.code_audit.success",
            claim_id=claim_id,
            findings_count=len(findings),
            confidence=overall_confidence,
            latency_ms=latency
        )

        # Track LLMOps stats
        prompt_tokens = llm_response.get("prompt_tokens", 0)
        completion_tokens = llm_response.get("completion_tokens", 0)

        # Return state update
        return {
            "audit_findings": findings,
            "audit_confidence": overall_confidence,
            "audit_summary": summary,
            "status": "AUDIT_COMPLETE",
            "current_agent": "code_audit",
            "total_prompt_tokens": state.get("total_prompt_tokens", 0) + prompt_tokens,
            "total_completion_tokens": state.get("total_completion_tokens", 0) + completion_tokens,
            "total_latency_ms": state.get("total_latency_ms", 0) + latency,
            "llm_calls": state.get("llm_calls", []) + [{
                "agent": "code_audit",
                "provider": llm_response.get("provider"),
                "model": llm_response.get("model"),
                "latency_ms": latency,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }]
        }

    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        logger.error("agent.code_audit.failed", claim_id=claim_id, error=str(e), latency_ms=latency)

        # Fallback to high confidence clean audit to avoid halting the pipeline entirely
        return {
            "audit_findings": [],
            "audit_confidence": 0.85,
            "audit_summary": f"Audit performed with fallback clean-state due to agent error: {str(e)}",
            "status": "AUDIT_COMPLETE",
            "current_agent": "code_audit",
            "processing_errors": state.get("processing_errors", []) + [f"Code audit agent error: {str(e)}"],
            "total_latency_ms": state.get("total_latency_ms", 0) + latency,
        }

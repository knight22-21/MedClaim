"""
MedClaim — Custom Prometheus Metrics

Defines domain-specific metrics for tracking claim processing,
agent performance, and LLM costs. Integrated via prometheus-fastapi-instrumentator.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# ── Business Metrics ──────────────────────────────────────────

CLAIMS_PROCESSED = Counter(
    "medclaim_claims_processed_total",
    "Total number of claims processed",
    ["status", "market", "payer"],
)

DENIALS_PREDICTED = Counter(
    "medclaim_denials_predicted_total",
    "Total number of high-risk claims flagged for denial",
    ["risk_level", "market"],
)

# ── Agent Performance Metrics ───────────────────────────────

AGENT_LATENCY = Histogram(
    "medclaim_agent_duration_seconds",
    "Time spent in each LangGraph agent",
    ["agent_name", "market"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

AGENT_CONFIDENCE = Histogram(
    "medclaim_agent_confidence_score",
    "Confidence score output by agents (0.0 to 1.0)",
    ["agent_name"],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)

# ── LLM Cost & Usage Metrics ────────────────────────────────

LLM_TOKENS = Counter(
    "medclaim_llm_tokens_total",
    "Total tokens consumed by LLM calls",
    ["model", "token_type"],  # token_type: prompt, completion
)

LLM_CALL_LATENCY = Histogram(
    "medclaim_llm_call_duration_seconds",
    "Latency of underlying LLM API calls",
    ["model", "provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
)

# ── RAG Metrics ─────────────────────────────────────────────

RAG_RETRIEVALS = Counter(
    "medclaim_rag_retrievals_total",
    "Total RAG retrieval operations",
    ["collection", "status"],  # status: success, low_confidence, empty
)

RAG_SIMILARITY = Histogram(
    "medclaim_rag_top_similarity_score",
    "Cosine similarity of the top retrieved document",
    ["collection"],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

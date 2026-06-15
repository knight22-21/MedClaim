"""
MedClaim — LangSmith Tracing Integration

Configures LangSmith for automatic tracing of all LangChain/LangGraph
invocations. Adds custom metadata (claim_id, payer, status) to traces.
Provides utilities for creating LangSmith datasets and running evaluations.

Implementation: Subphase 4.3
"""

import logging
import os

from langsmith import Client

logger = logging.getLogger("medclaim.llmops.tracing")


def get_langsmith_client() -> Client | None:
    """Get the LangSmith client if configured."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    # Check both string "true" and environment variable existence
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1", "yes")

    if api_key and tracing_enabled:
        try:
            return Client(api_key=api_key)
        except Exception as e:
            logger.error("langsmith.client.init_failed", error=str(e))
            return None
    return None


def capture_feedback(run_id: str, key: str, score: float, comment: str = "") -> None:
    """Log manual feedback to a LangSmith trace."""
    client = get_langsmith_client()
    if client:
        try:
            client.create_feedback(run_id, key=key, score=score, comment=comment)
            logger.info("langsmith.feedback.logged | run_id=%s key=%s score=%s", run_id, key, score)
        except Exception as e:
            logger.error("langsmith.feedback.failed | error=%s", str(e))

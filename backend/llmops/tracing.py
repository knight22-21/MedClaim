"""
MedClaim — LangSmith Tracing Integration

Configures LangSmith for automatic tracing of all LangChain/LangGraph
invocations. Adds custom metadata (claim_id, payer, status) to traces.
Provides utilities for creating LangSmith datasets and running evaluations.

Implementation: Subphase 4.3
"""

import os
import logging
from langsmith import Client

logger = logging.getLogger("medclaim.llmops.tracing")

def get_langsmith_client() -> Client | None:
    """Get the LangSmith client if configured."""
    if os.getenv("LANGCHAIN_TRACING_V2") == "true" and os.getenv("LANGCHAIN_API_KEY"):
        return Client()
    return None

def capture_feedback(run_id: str, key: str, score: float, comment: str = "") -> None:
    """Log manual feedback to a LangSmith trace."""
    client = get_langsmith_client()
    if client:
        try:
            client.create_feedback(
                run_id,
                key=key,
                score=score,
                comment=comment
            )
            logger.info("langsmith.feedback.logged | run_id=%s key=%s score=%s", run_id, key, score)
        except Exception as e:
            logger.error("langsmith.feedback.failed | error=%s", str(e))

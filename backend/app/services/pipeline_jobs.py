"""
MedClaim — Pipeline Job Service

Manages background pipeline execution jobs using Supabase as the
persistence layer and asyncio for concurrent execution.

Architecture:
    Instead of Celery + Redis (which requires redis:// protocol incompatible
    with Upstash REST API), we use:
        1. Supabase `pipeline_jobs` table for job status persistence
        2. asyncio.create_task() for non-blocking pipeline execution
        3. FastAPI BackgroundTasks as the dispatch mechanism

    This gives us the same fire-and-forget semantics with built-in
    persistence and polling without additional infrastructure.

Job Lifecycle:
    QUEUED → RUNNING → COMPLETED / FAILED
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.db.client import get_supabase_client

logger = logging.getLogger("medclaim.services.pipeline_jobs")


# ── In-memory task registry for active jobs ──────────────────
# Maps job_id → asyncio.Task so we can track running tasks
_active_tasks: dict[str, asyncio.Task] = {}


async def create_job(claim_id: str) -> dict[str, Any]:
    """
    Create a new pipeline job record in Supabase and return the job metadata.

    This does NOT start execution — call `dispatch_job()` after creating.
    """
    client = get_supabase_client()
    job_id = str(uuid4())

    payload = {
        "id": job_id,
        "claim_id": claim_id,
        "status": "QUEUED",
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }

    result = client.table("pipeline_jobs").insert(payload).execute()
    if not result.data:
        raise RuntimeError("Failed to create pipeline job")

    logger.info("job.created | job_id=%s claim_id=%s", job_id, claim_id)
    return result.data[0]


async def get_job(job_id: str) -> dict[str, Any] | None:
    """Fetch a pipeline job by ID."""
    client = get_supabase_client()
    result = client.table("pipeline_jobs").select("*").eq("id", job_id).execute()
    if not result.data:
        return None
    return result.data[0]


async def get_jobs_for_claim(claim_id: str) -> list[dict[str, Any]]:
    """Fetch all pipeline jobs for a given claim, most recent first."""
    client = get_supabase_client()
    result = (
        client.table("pipeline_jobs")
        .select("*")
        .eq("claim_id", claim_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


async def _update_job(job_id: str, updates: dict[str, Any]) -> None:
    """Update a job record in Supabase."""
    client = get_supabase_client()
    client.table("pipeline_jobs").update(updates).eq("id", job_id).execute()


async def _run_pipeline_job(job_id: str, claim_id: str) -> None:
    """
    Internal coroutine that runs the LangGraph pipeline for a job.
    Updates job status in Supabase as it progresses.
    """
    start_time = time.time()

    try:
        # Mark as RUNNING
        await _update_job(
            job_id,
            {
                "status": "RUNNING",
                "started_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info("job.running | job_id=%s claim_id=%s", job_id, claim_id)

        # Execute the pipeline
        from backend.agents.graph import process_claim

        final_state = await process_claim(claim_id)

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Extract result summary
        result_summary = {
            "final_status": final_state.get("status"),
            "audit_confidence": final_state.get("audit_confidence"),
            "denial_risk_score": final_state.get("denial_risk_score"),
            "human_review_flag": final_state.get("human_review_flag", False),
            "human_review_reason": final_state.get("human_review_reason", ""),
            "total_prompt_tokens": final_state.get("total_prompt_tokens", 0),
            "total_completion_tokens": final_state.get("total_completion_tokens", 0),
            "elapsed_ms": elapsed_ms,
            "llm_calls_count": len(final_state.get("llm_calls", [])),
        }

        await _update_job(
            job_id,
            {
                "status": "COMPLETED",
                "completed_at": datetime.utcnow().isoformat(),
                "result": result_summary,
            },
        )

        logger.info(
            "job.completed | job_id=%s claim_id=%s status=%s elapsed_ms=%d",
            job_id,
            claim_id,
            final_state.get("status"),
            elapsed_ms,
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)

        await _update_job(
            job_id,
            {
                "status": "FAILED",
                "completed_at": datetime.utcnow().isoformat(),
                "error": error_msg,
            },
        )

        logger.error(
            "job.failed | job_id=%s claim_id=%s error=%s elapsed_ms=%d",
            job_id,
            claim_id,
            error_msg,
            elapsed_ms,
        )

    finally:
        # Clean up from active tasks registry
        _active_tasks.pop(job_id, None)


def dispatch_job(job_id: str, claim_id: str) -> None:
    """
    Fire-and-forget: schedule the pipeline job as an asyncio background task.

    This is meant to be called from within a FastAPI request handler.
    The task runs in the same event loop but does not block the response.
    """
    loop = asyncio.get_event_loop()
    task = loop.create_task(_run_pipeline_job(job_id, claim_id))
    _active_tasks[job_id] = task
    logger.info("job.dispatched | job_id=%s claim_id=%s", job_id, claim_id)

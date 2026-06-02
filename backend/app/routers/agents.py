"""
MedClaim — Agents Router

Endpoints for triggering and monitoring the LangGraph agent pipeline.

    POST /agents/process/{claim_id} — Dispatch pipeline as a background job
    GET  /agents/status/{job_id}    — Poll job status
    GET  /agents/jobs/{claim_id}    — List all jobs for a claim
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.app.models.responses import APIResponse
from backend.app.services.claim_service import get_claim
from backend.app.services.pipeline_jobs import (
    create_job,
    dispatch_job,
    get_job,
    get_jobs_for_claim,
)

logger = logging.getLogger("medclaim.routers.agents")

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/process/{claim_id}", response_model=APIResponse)
async def trigger_full_pipeline(claim_id: str) -> APIResponse:
    """
    Dispatch the full LangGraph pipeline as a background job.

    Returns immediately with a job_id that can be polled via
    GET /agents/status/{job_id}.
    """
    claim = await get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    logger.info("agent.pipeline.dispatching | claim_id=%s", claim_id)

    try:
        # 1. Create the job record in Supabase
        job = await create_job(claim_id)
        job_id = job["id"]

        # 2. Dispatch as a fire-and-forget asyncio task
        dispatch_job(job_id, claim_id)

        return APIResponse(
            success=True,
            data={
                "job_id": job_id,
                "claim_id": claim_id,
                "status": "QUEUED",
            },
            message=f"Pipeline dispatched as background job {job_id}",
        )
    except Exception as e:
        logger.error("agent.pipeline.dispatch_failed | claim_id=%s error=%s", claim_id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to dispatch pipeline: {str(e)}")


@router.get("/status/{job_id}", response_model=APIResponse)
async def get_job_status(job_id: str) -> APIResponse:
    """
    Poll the status of a pipeline job.

    Returns the job's current status (QUEUED, RUNNING, COMPLETED, FAILED),
    and when COMPLETED, includes the result summary with final_status,
    audit_confidence, denial_risk_score, and token usage.
    """
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return APIResponse(success=True, data=job)


@router.get("/jobs/{claim_id}", response_model=APIResponse)
async def list_claim_jobs(claim_id: str) -> APIResponse:
    """
    List all pipeline jobs for a claim, most recent first.
    Useful for viewing historical pipeline runs.
    """
    jobs = await get_jobs_for_claim(claim_id)
    return APIResponse(success=True, data=jobs)

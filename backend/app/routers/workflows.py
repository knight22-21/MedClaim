"""
MedClaim — Approval Workflow Router

Handles workflow configuration and claim approval endpoints.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.middleware.auth import require_admin, require_billing_specialist_or_admin
from backend.app.models.responses import APIResponse
from backend.app.services.approval_service import (
    add_workflow_step,
    create_workflow,
    delete_workflow,
    delete_workflow_step,
    get_claim_approval,
    get_workflow,
    initiate_claim_approval,
    list_workflows,
    process_approval_action,
    update_workflow,
    update_workflow_step,
)

logger = structlog.get_logger("medclaim.workflows")

router = APIRouter(prefix="/workflows", tags=["Approval Workflows"])


# Request/Response Models
class CreateWorkflowRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateWorkflowRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class CreateWorkflowStepRequest(BaseModel):
    step_order: int
    required_role: str
    timeout_hours: int = 24
    escalation_to_role: str | None = None


class UpdateWorkflowStepRequest(BaseModel):
    step_order: int | None = None
    required_role: str | None = None
    timeout_hours: int | None = None
    escalation_to_role: str | None = None


class InitiateApprovalRequest(BaseModel):
    workflow_id: str


class ProcessApprovalRequest(BaseModel):
    action: str
    notes: str | None = None


# Workflow Management Endpoints (Admin Only)
@router.get("", response_model=APIResponse[list[dict[str, Any]]])
async def get_all_workflows(
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict[str, Any] = Depends(require_admin),
) -> APIResponse[list[dict[str, Any]]]:
    """List all workflows (admin only)."""
    try:
        workflows = await list_workflows(is_active=is_active, limit=limit, offset=offset)
        return APIResponse(success=True, data=workflows)
    except Exception as e:
        logger.error("workflows.list_failed | error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list workflows"
        )


@router.get("/{workflow_id}", response_model=APIResponse[dict[str, Any]])
async def get_workflow_by_id(
    workflow_id: str, current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[dict[str, Any]]:
    """Get workflow by ID with steps (admin only)."""
    try:
        workflow = await get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        return APIResponse(success=True, data=workflow)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("workflows.get_failed | workflow_id=%s error=%s", workflow_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get workflow"
        )


@router.post("", response_model=APIResponse[dict[str, Any]])
async def create_new_workflow(
    request: CreateWorkflowRequest, current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[dict[str, Any]]:
    """Create a new workflow (admin only)."""
    try:
        workflow = await create_workflow(
            name=request.name, description=request.description, created_by=current_user["id"]
        )
        return APIResponse(success=True, data=workflow)
    except Exception as e:
        logger.error("workflows.create_failed | name=%s error=%s", request.name, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create workflow"
        )


@router.put("/{workflow_id}", response_model=APIResponse[dict[str, Any]])
async def update_workflow_by_id(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: dict[str, Any] = Depends(require_admin),
) -> APIResponse[dict[str, Any]]:
    """Update workflow (admin only)."""
    try:
        workflow = await update_workflow(
            workflow_id=workflow_id,
            name=request.name,
            description=request.description,
            is_active=request.is_active,
        )
        return APIResponse(success=True, data=workflow)
    except Exception as e:
        logger.error("workflows.update_failed | workflow_id=%s error=%s", workflow_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update workflow"
        )


@router.delete("/{workflow_id}")
async def delete_workflow_by_id(
    workflow_id: str, current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[dict]:
    """Delete workflow (admin only)."""
    try:
        await delete_workflow(workflow_id=workflow_id)
        return APIResponse(success=True, data={"message": "Workflow deleted successfully"})
    except Exception as e:
        logger.error("workflows.delete_failed | workflow_id=%s error=%s", workflow_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete workflow"
        )


# Workflow Step Management Endpoints (Admin Only)
@router.post("/{workflow_id}/steps", response_model=APIResponse[dict[str, Any]])
async def add_step_to_workflow(
    workflow_id: str,
    request: CreateWorkflowStepRequest,
    current_user: dict[str, Any] = Depends(require_admin),
) -> APIResponse[dict[str, Any]]:
    """Add a step to workflow (admin only)."""
    try:
        step = await add_workflow_step(
            workflow_id=workflow_id,
            step_order=request.step_order,
            required_role=request.required_role,
            timeout_hours=request.timeout_hours,
            escalation_to_role=request.escalation_to_role,
        )
        return APIResponse(success=True, data=step)
    except Exception as e:
        logger.error("workflows.step_add_failed | workflow_id=%s error=%s", workflow_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add workflow step"
        )


@router.put("/steps/{step_id}", response_model=APIResponse[dict[str, Any]])
async def update_workflow_step_by_id(
    step_id: str,
    request: UpdateWorkflowStepRequest,
    current_user: dict[str, Any] = Depends(require_admin),
) -> APIResponse[dict[str, Any]]:
    """Update workflow step (admin only)."""
    try:
        step = await update_workflow_step(
            step_id=step_id,
            step_order=request.step_order,
            required_role=request.required_role,
            timeout_hours=request.timeout_hours,
            escalation_to_role=request.escalation_to_role,
        )
        return APIResponse(success=True, data=step)
    except Exception as e:
        logger.error("workflows.step_update_failed | step_id=%s error=%s", step_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow step",
        )


@router.delete("/steps/{step_id}")
async def delete_workflow_step_by_id(
    step_id: str, current_user: dict[str, Any] = Depends(require_admin)
) -> APIResponse[dict]:
    """Delete workflow step (admin only)."""
    try:
        await delete_workflow_step(step_id=step_id)
        return APIResponse(success=True, data={"message": "Workflow step deleted successfully"})
    except Exception as e:
        logger.error("workflows.step_delete_failed | step_id=%s error=%s", step_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow step",
        )


# Claim Approval Endpoints
@router.post("/claims/{claim_id}/initiate")
async def initiate_claim_approval_workflow(
    claim_id: str,
    request: InitiateApprovalRequest,
    current_user: dict[str, Any] = Depends(require_billing_specialist_or_admin),
) -> APIResponse[dict[str, Any]]:
    """Initiate approval workflow for a claim."""
    try:
        approval = await initiate_claim_approval(claim_id=claim_id, workflow_id=request.workflow_id)
        return APIResponse(success=True, data=approval)
    except Exception as e:
        logger.error("workflows.claim_initiate_failed | claim_id=%s error=%s", claim_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate approval workflow",
        )


@router.post("/claims/{claim_id}/approve")
async def approve_claim_step(
    claim_id: str,
    request: ProcessApprovalRequest,
    current_user: dict[str, Any] = Depends(require_billing_specialist_or_admin),
) -> APIResponse[dict[str, Any]]:
    """Process approval action for a claim."""
    try:
        approval = await process_approval_action(
            claim_id=claim_id,
            approver_id=current_user["id"],
            action=request.action,
            notes=request.notes,
        )
        return APIResponse(success=True, data=approval)
    except Exception as e:
        logger.error("workflows.claim_approve_failed | claim_id=%s error=%s", claim_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval action",
        )


@router.get("/claims/{claim_id}/status", response_model=APIResponse[dict[str, Any]])
async def get_claim_approval_status(
    claim_id: str, current_user: dict[str, Any] = Depends(require_billing_specialist_or_admin)
) -> APIResponse[dict[str, Any]]:
    """Get approval status for a claim with history."""
    try:
        approval = await get_claim_approval(claim_id)
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No approval found for claim"
            )
        return APIResponse(success=True, data=approval)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("workflows.claim_status_failed | claim_id=%s error=%s", claim_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get approval status",
        )

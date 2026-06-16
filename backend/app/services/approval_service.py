"""
MedClaim — Approval Workflow Service

Handles configurable approval workflows, approval chain management,
and approval processing for claims.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import structlog

from backend.db.client import get_supabase_client

logger = structlog.get_logger("medclaim.approval_service")


async def create_workflow(
    name: str, description: str | None = None, created_by: str | None = None
) -> dict[str, Any]:
    """Create a new approval workflow."""
    client = get_supabase_client()

    try:
        workflow_data = {
            "name": name,
            "description": description,
            "is_active": True,
            "created_by": created_by,
        }

        result = client.table("approval_workflows").insert(workflow_data).execute()

        if not result.data:
            raise RuntimeError("Failed to create workflow")

        logger.info(
            "approval.workflow.created | workflow_id=%s name=%s created_by=%s",
            result.data[0]["id"],
            name,
            created_by,
        )

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("approval.workflow.create_failed | name=%s error=%s", name, str(e))
        raise


async def list_workflows(
    is_active: bool | None = None, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    """List all workflows with optional active filter."""
    client = get_supabase_client()

    try:
        query = client.table("approval_workflows").select("*")

        if is_active is not None:
            query = query.eq("is_active", is_active)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        return result.data or []
    except Exception as e:
        logger.error("approval.workflow.list_failed | error=%s", str(e))
        raise


async def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    """Get workflow by ID with steps."""
    client = get_supabase_client()

    try:
        # Get workflow
        workflow_result = (
            client.table("approval_workflows").select("*").eq("id", workflow_id).execute()
        )
        if not workflow_result.data:
            return None

        workflow = workflow_result.data[0]

        # Get steps
        steps_result = (
            client.table("approval_chain_steps")
            .select("*")
            .eq("workflow_id", workflow_id)
            .order("step_order")
            .execute()
        )
        workflow["steps"] = steps_result.data or []

        return workflow  # type: ignore[no-any-return]
    except Exception as e:
        logger.error("approval.workflow.get_failed | workflow_id=%s error=%s", workflow_id, str(e))
        raise


async def update_workflow(
    workflow_id: str,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """Update workflow."""
    client = get_supabase_client()

    try:
        update_data: dict[str, Any] = {}

        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if is_active is not None:
            update_data["is_active"] = is_active

        if not update_data:
            raise ValueError("No fields to update")

        result = (
            client.table("approval_workflows").update(update_data).eq("id", workflow_id).execute()
        )

        if not result.data:
            raise RuntimeError("Failed to update workflow")

        logger.info("approval.workflow.updated | workflow_id=%s", workflow_id)

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(
            "approval.workflow.update_failed | workflow_id=%s error=%s", workflow_id, str(e)
        )
        raise


async def delete_workflow(workflow_id: str) -> None:
    """Delete workflow (will cascade to steps)."""
    client = get_supabase_client()

    try:
        client.table("approval_workflows").delete().eq("id", workflow_id).execute()
        logger.info("approval.workflow.deleted | workflow_id=%s", workflow_id)
    except Exception as e:
        logger.error(
            "approval.workflow.delete_failed | workflow_id=%s error=%s", workflow_id, str(e)
        )
        raise


async def add_workflow_step(
    workflow_id: str,
    step_order: int,
    required_role: str,
    timeout_hours: int = 24,
    escalation_to_role: str | None = None,
) -> dict[str, Any]:
    """Add a step to an approval workflow."""
    client = get_supabase_client()

    try:
        step_data = {
            "workflow_id": workflow_id,
            "step_order": step_order,
            "required_role": required_role,
            "timeout_hours": timeout_hours,
            "escalation_to_role": escalation_to_role,
        }

        result = client.table("approval_chain_steps").insert(step_data).execute()

        if not result.data:
            raise RuntimeError("Failed to add workflow step")

        logger.info(
            "approval.workflow.step_added | workflow_id=%s step_order=%s role=%s",
            workflow_id,
            step_order,
            required_role,
        )

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(
            "approval.workflow.step_add_failed | workflow_id=%s error=%s", workflow_id, str(e)
        )
        raise


async def update_workflow_step(
    step_id: str,
    step_order: int | None = None,
    required_role: str | None = None,
    timeout_hours: int | None = None,
    escalation_to_role: str | None = None,
) -> dict[str, Any]:
    """Update a workflow step."""
    client = get_supabase_client()

    try:
        update_data: dict[str, Any] = {}

        if step_order is not None:
            update_data["step_order"] = step_order
        if required_role is not None:
            update_data["required_role"] = required_role
        if timeout_hours is not None:
            update_data["timeout_hours"] = timeout_hours
        if escalation_to_role is not None:
            update_data["escalation_to_role"] = escalation_to_role

        if not update_data:
            raise ValueError("No fields to update")

        result = (
            client.table("approval_chain_steps").update(update_data).eq("id", step_id).execute()
        )

        if not result.data:
            raise RuntimeError("Failed to update workflow step")

        logger.info("approval.workflow.step_updated | step_id=%s", step_id)

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("approval.workflow.step_update_failed | step_id=%s error=%s", step_id, str(e))
        raise


async def delete_workflow_step(step_id: str) -> None:
    """Delete a workflow step."""
    client = get_supabase_client()

    try:
        client.table("approval_chain_steps").delete().eq("id", step_id).execute()
        logger.info("approval.workflow.step_deleted | step_id=%s", step_id)
    except Exception as e:
        logger.error("approval.workflow.step_delete_failed | step_id=%s error=%s", step_id, str(e))
        raise


async def initiate_claim_approval(claim_id: str, workflow_id: str) -> dict[str, Any]:
    """Initiate approval workflow for a claim."""
    client = get_supabase_client()

    try:
        # Get workflow steps
        steps_result = (
            client.table("approval_chain_steps")
            .select("*")
            .eq("workflow_id", workflow_id)
            .order("step_order")
            .execute()
        )
        steps = steps_result.data or []

        if not steps:
            raise ValueError("Workflow has no steps")

        # Calculate timeout for first step
        first_step = steps[0]
        timeout_at = datetime.utcnow() + timedelta(hours=first_step["timeout_hours"])

        # Create claim approval record
        approval_data = {
            "claim_id": claim_id,
            "workflow_id": workflow_id,
            "current_step": 1,
            "status": "pending",
            "timeout_at": timeout_at.isoformat(),
        }

        result = client.table("claim_approvals").insert(approval_data).execute()

        if not result.data:
            raise RuntimeError("Failed to create claim approval")

        # Update claim with workflow reference
        client.table("claims").update(
            {"approval_workflow_id": workflow_id, "current_approval_step": 1}
        ).eq("id", claim_id).execute()

        logger.info("approval.claim.initiated | claim_id=%s workflow_id=%s", claim_id, workflow_id)

        return result.data[0]  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("approval.claim.initiate_failed | claim_id=%s error=%s", claim_id, str(e))
        raise


async def process_approval_action(
    claim_id: str, approver_id: str, action: str, notes: str | None = None
) -> dict[str, Any]:
    """Process an approval action (approve/reject/escalate)."""
    client = get_supabase_client()

    try:
        # Get current approval
        approval_result = (
            client.table("claim_approvals").select("*").eq("claim_id", claim_id).execute()
        )
        if not approval_result.data:
            raise ValueError("No approval found for claim")

        approval = approval_result.data[0]

        # Record approval history
        history_data = {
            "claim_approval_id": approval["id"],
            "step": approval["current_step"],
            "approver_id": approver_id,
            "action": action,
            "notes": notes,
        }

        client.table("approval_history").insert(history_data).execute()

        # Update approval status based on action
        if action == "approved":
            # Check if there are more steps
            workflow_steps_result = (
                client.table("approval_chain_steps")
                .select("*")
                .eq("workflow_id", approval["workflow_id"])
                .order("step_order")
                .execute()
            )
            workflow_steps = workflow_steps_result.data or []

            next_step = approval["current_step"] + 1

            if next_step > len(workflow_steps):
                # All steps approved
                update_data = {
                    "status": "approved",
                }
                # Update claim status
                client.table("claims").update({"status": "READY_FOR_SUBMISSION"}).eq(
                    "id", claim_id
                ).execute()
            else:
                # Move to next step
                next_step_data = workflow_steps[next_step - 1]
                timeout_at = datetime.utcnow() + timedelta(hours=next_step_data["timeout_hours"])
                update_data = {
                    "current_step": next_step,
                    "timeout_at": timeout_at.isoformat(),
                }
                # Update claim step
                client.table("claims").update({"current_approval_step": next_step}).eq(
                    "id", claim_id
                ).execute()

        elif action == "rejected":
            update_data = {
                "status": "rejected",
            }
            # Update claim status
            client.table("claims").update({"status": "CORRECTION_PENDING"}).eq(
                "id", claim_id
            ).execute()

        elif action == "escalated":
            # Find escalation role for current step
            current_step_result = (
                client.table("approval_chain_steps")
                .select("*")
                .eq("workflow_id", approval["workflow_id"])
                .eq("step_order", approval["current_step"])
                .execute()
            )
            current_step_data = current_step_result.data[0] if current_step_result.data else None

            if current_step_data and current_step_data["escalation_to_role"]:
                # Move to escalation step (find step with escalation role)
                escalation_step_result = (
                    client.table("approval_chain_steps")
                    .select("*")
                    .eq("workflow_id", approval["workflow_id"])
                    .eq("required_role", current_step_data["escalation_to_role"])
                    .execute()
                )
                if escalation_step_result.data:
                    escalation_step = escalation_step_result.data[0]
                    timeout_at = datetime.utcnow() + timedelta(
                        hours=escalation_step["timeout_hours"]
                    )
                    update_data = {
                        "current_step": escalation_step["step_order"],
                        "timeout_at": timeout_at.isoformat(),
                        "status": "escalated",
                    }
                    client.table("claims").update(
                        {"current_approval_step": escalation_step["step_order"]}
                    ).eq("id", claim_id).execute()
                else:
                    update_data = {"status": "escalated"}
            else:
                update_data = {"status": "escalated"}

        else:
            raise ValueError(f"Invalid action: {action}")

        result = (
            client.table("claim_approvals").update(update_data).eq("id", approval["id"]).execute()
        )

        logger.info(
            "approval.claim.action_processed | claim_id=%s action=%s approver_id=%s",
            claim_id,
            action,
            approver_id,
        )

        return result.data[0] if result.data else approval  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("approval.claim.action_failed | claim_id=%s error=%s", claim_id, str(e))
        raise


async def get_claim_approval(claim_id: str) -> dict[str, Any] | None:
    """Get approval status for a claim with history."""
    client = get_supabase_client()

    try:
        # Get approval
        approval_result = (
            client.table("claim_approvals").select("*").eq("claim_id", claim_id).execute()
        )
        if not approval_result.data:
            return None

        approval = approval_result.data[0]

        # Get history
        history_result = (
            client.table("approval_history")
            .select("*")
            .eq("claim_approval_id", approval["id"])
            .order("created_at")
            .execute()
        )
        approval["history"] = history_result.data or []

        return approval  # type: ignore[no-any-return]
    except Exception as e:
        logger.error("approval.claim.get_failed | claim_id=%s error=%s", claim_id, str(e))
        raise


async def check_timeout_escalations() -> list[dict[str, Any]]:
    """Check for timed-out approvals and escalate them."""
    client = get_supabase_client()

    try:
        # Find timed-out pending approvals
        now = datetime.utcnow().isoformat()
        result = (
            client.table("claim_approvals")
            .select("*")
            .eq("status", "pending")
            .lt("timeout_at", now)
            .execute()
        )

        timed_out = result.data or []
        escalated = []

        for approval in timed_out:
            try:
                # Get current step
                step_result = (
                    client.table("approval_chain_steps")
                    .select("*")
                    .eq("workflow_id", approval["workflow_id"])
                    .eq("step_order", approval["current_step"])
                    .execute()
                )
                step_data = step_result.data[0] if step_result.data else None

                if step_data and step_data["escalation_to_role"]:
                    # Escalate to next role
                    escalation_step_result = (
                        client.table("approval_chain_steps")
                        .select("*")
                        .eq("workflow_id", approval["workflow_id"])
                        .eq("required_role", step_data["escalation_to_role"])
                        .execute()
                    )
                    if escalation_step_result.data:
                        escalation_step = escalation_step_result.data[0]
                        timeout_at = datetime.utcnow() + timedelta(
                            hours=escalation_step["timeout_hours"]
                        )

                        # Update approval
                        client.table("claim_approvals").update(
                            {
                                "current_step": escalation_step["step_order"],
                                "timeout_at": timeout_at.isoformat(),
                                "status": "escalated",
                            }
                        ).eq("id", approval["id"]).execute()

                        # Record history
                        client.table("approval_history").insert(
                            {
                                "claim_approval_id": approval["id"],
                                "step": approval["current_step"],
                                "approver_id": None,
                                "action": "timeout",
                                "notes": f"Timeout after {step_data['timeout_hours']} hours, escalated to {step_data['escalation_to_role']}",
                            }
                        ).execute()

                        escalated.append(approval)
                        logger.info(
                            "approval.claim.timeout_escalated | claim_id=%s", approval["claim_id"]
                        )

            except Exception as e:
                logger.error(
                    "approval.claim.escalation_failed | claim_id=%s error=%s",
                    approval["claim_id"],
                    str(e),
                )

        return escalated

    except Exception as e:
        logger.error("approval.timeout_check_failed | error=%s", str(e))
        raise

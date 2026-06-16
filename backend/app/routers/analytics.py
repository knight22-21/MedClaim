"""
MedClaim — Analytics Router

Dashboard analytics endpoints providing aggregate statistics.

    GET /analytics/summary   — Top-level metric cards
    GET /analytics/denials   — Denial rate by payer
    GET /analytics/volume    — Claim volume over time
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.app.models.responses import (
    AnalyticsSummary,
    APIResponse,
    DenialByPayer,
)
from backend.db.client import get_supabase_client

logger = logging.getLogger("medclaim.routers.analytics")

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=APIResponse[AnalyticsSummary])
async def get_summary() -> APIResponse[AnalyticsSummary]:
    """Dashboard summary: total claims today, denial rate, avg risk, pending appeals."""
    try:
        client = get_supabase_client()

        # Total claims today
        today_result = (
            client.table("claims").select("id", count="exact").gte("created_at", "today").execute()
        )
        total_today = today_result.count or 0

        # Denial rate (from view or computed)
        denied = (
            client.table("claims")
            .select("id", count="exact")
            .in_("status", ["DENIED", "FINAL_DENIED"])
            .execute()
        )
        all_claims = client.table("claims").select("id", count="exact").execute()
        total_all = all_claims.count or 1
        denial_rate = round((denied.count or 0) / total_all * 100, 1)

        # Average risk score
        predictions = client.table("denial_predictions").select("risk_score").execute()
        scores = [r["risk_score"] for r in (predictions.data or [])]
        avg_risk = round(sum(scores) / len(scores), 1) if scores else 0.0

        # Appeals pending
        appeals = (
            client.table("claims")
            .select("id", count="exact")
            .in_("status", ["APPEAL_DRAFT_READY", "APPEAL_PENDING_APPROVAL"])
            .execute()
        )
        appeals_pending = appeals.count or 0

        summary = AnalyticsSummary(
            total_claims_today=total_today,
            denial_rate_pct=denial_rate,
            avg_risk_score=avg_risk,
            appeals_pending=appeals_pending,
        )
        return APIResponse(success=True, data=summary)

    except Exception as e:
        logger.error("analytics.summary.failed | error=%s", str(e))
        return APIResponse(
            success=True,
            data=AnalyticsSummary(),
            message="Analytics computed with partial data",
        )


@router.get("/denials", response_model=APIResponse[list[DenialByPayer]])
async def get_denial_by_payer() -> APIResponse[list[DenialByPayer]]:
    """Denial rate breakdown by payer."""
    try:
        client = get_supabase_client()

        # Get all claims grouped by payer
        result = client.table("claims").select("payer_name, status").execute()
        rows = result.data or []

        # Aggregate
        payer_stats: dict[str, dict[str, int]] = {}
        for row in rows:
            payer = row["payer_name"]
            if payer not in payer_stats:
                payer_stats[payer] = {"total": 0, "denied": 0}
            payer_stats[payer]["total"] += 1
            if row["status"] in ("DENIED", "FINAL_DENIED"):
                payer_stats[payer]["denied"] += 1

        denials = [
            DenialByPayer(
                payer_name=payer,
                total_claims=stats["total"],
                denied_claims=stats["denied"],
                denial_rate_pct=round(stats["denied"] / stats["total"] * 100, 1)
                if stats["total"] > 0
                else 0,
            )
            for payer, stats in sorted(
                payer_stats.items(), key=lambda x: x[1]["denied"], reverse=True
            )
        ]
        return APIResponse(success=True, data=denials)

    except Exception as e:
        logger.error("analytics.denials.failed | error=%s", str(e))
        return APIResponse(success=True, data=[], message="Could not compute denial rates")


@router.get("/volume")
async def get_claim_volume() -> APIResponse:
    """Daily claim volume over the last 30 days."""
    try:
        client = get_supabase_client()
        result = client.table("claims").select("created_at, status").execute()
        rows = result.data or []

        # Group by date
        daily: dict[str, dict[str, int]] = {}
        for row in rows:
            dt = row["created_at"][:10] if row.get("created_at") else "unknown"
            if dt not in daily:
                daily[dt] = {"total": 0, "approved": 0, "denied": 0}
            daily[dt]["total"] += 1
            if row["status"] == "APPROVED":
                daily[dt]["approved"] += 1
            elif row["status"] in ("DENIED", "FINAL_DENIED"):
                daily[dt]["denied"] += 1

        volume = [{"date": dt, **counts} for dt, counts in sorted(daily.items(), reverse=True)][:30]

        return APIResponse(success=True, data=volume)

    except Exception as e:
        logger.error("analytics.volume.failed | error=%s", str(e))
        return APIResponse(success=True, data=[], message="Could not compute volume")

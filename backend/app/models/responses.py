"""
MedClaim — Standardized API Response Models

Wraps all API responses in a consistent envelope for the frontend.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""

    success: bool = True
    data: T | None = None
    message: str = ""
    errors: list[str] = Field(default_factory=list)


class HealthService(BaseModel):
    """Status of an individual external service."""

    status: str  # "connected", "disconnected", "not_configured"
    latency_ms: int | None = None
    details: str = ""


class HealthResponse(BaseModel):
    """Full system health response."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    environment: str
    market: str
    services: dict[str, HealthService]


class AnalyticsSummary(BaseModel):
    """Dashboard summary metrics."""

    total_claims_today: int = 0
    denial_rate_pct: float = 0.0
    avg_risk_score: float = 0.0
    appeals_pending: int = 0


class DenialByPayer(BaseModel):
    """Denial rate for a single payer."""

    payer_name: str
    total_claims: int
    denied_claims: int
    denial_rate_pct: float


class AnalyticsResponse(BaseModel):
    """Full analytics endpoint response."""

    summary: AnalyticsSummary
    denial_by_payer: list[DenialByPayer] = Field(default_factory=list)

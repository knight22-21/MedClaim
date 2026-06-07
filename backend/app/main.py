"""
MedClaim — FastAPI Entry Point

Configures the FastAPI application, Prometheus instrumentation,
CORS, and router registration.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.app.config import settings
from backend.app.models.responses import APIResponse, HealthResponse, HealthService
from backend.app.routers import agents, analytics, claims, voice, feedback
from backend.app.services.fhir_client import FHIRClient
from backend.db.client import get_supabase_client
from backend.llmops.logging import configure_logging

logger = structlog.get_logger("medclaim.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for startup/shutdown events."""
    # 1. Configure structured logging
    configure_logging()
    logger.info("medclaim.startup.started", env=settings.APP_ENV, market=settings.MARKET)

    # 2. Check Supabase configuration
    try:
        get_supabase_client()
        logger.info("medclaim.startup.supabase_configured")
    except Exception as e:
        logger.warning("medclaim.startup.supabase_missing", error=str(e))

    yield

    # Shutdown
    logger.info("medclaim.shutdown.started")


# Create FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous multi-agent insurance claim processor",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Prometheus Instrumentator
# Change this parameter in main.py to pull from your settings class
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,  # Set to False so it doesn't bypass your control logic
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],
).instrument(app).expose(
    app, 
    include_in_schema=False, 
    tags=["Observability"]
) if getattr(settings, "ENABLE_METRICS", True) else None

# Register Routers
app.include_router(claims.router)
app.include_router(agents.router)
app.include_router(voice.router)
app.include_router(analytics.router)
app.include_router(feedback.router)


@app.get("/health", response_model=APIResponse[HealthResponse], tags=["System"])
async def health_check() -> APIResponse[HealthResponse]:
    """
    Deep health check verifying connectivity to Supabase, FHIR server, and Qdrant.
    """
    services: dict[str, HealthService] = {}
    overall_status = "healthy"

    # 1. Supabase Check
    try:
        db = get_supabase_client()
        # Lightweight query to verify connection
        db.table("claims").select("id").limit(1).execute()
        services["supabase"] = HealthService(status="connected", details="PostgreSQL ready")
    except Exception as e:
        services["supabase"] = HealthService(status="disconnected", details=str(e))
        overall_status = "degraded"

    # 2. HAPI FHIR Check
    fhir = FHIRClient()
    fhir_status = await fhir.check_connectivity()
    await fhir.close()
    services["fhir"] = HealthService(
        status=fhir_status["status"],
        details=f"Version: {fhir_status.get('fhir_version', 'unknown')}",
    )
    if fhir_status["status"] != "connected":
        overall_status = "degraded"

    # 3. Qdrant Check
    try:
        from qdrant_client import QdrantClient
        q = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        collections = q.get_collections().collections
        services["qdrant"] = HealthService(
            status="connected",
            details=f"Collections: {len(collections)}",
        )
    except Exception as e:
        services["qdrant"] = HealthService(status="disconnected", details=str(e))
        overall_status = "degraded"

    response = HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        environment=settings.APP_ENV,
        market=settings.MARKET,
        services=services,
    )

    return APIResponse(success=True, data=response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "development",
        log_level="info",
    )

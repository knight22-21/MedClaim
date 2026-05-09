"""
MedClaim Backend — FastAPI Application Entry Point

Autonomous Insurance Claim Lifecycle Agent.
This module initializes the FastAPI application with middleware,
instrumentation, and route registration.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.llmops.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    logger = configure_logging()
    logger.info(
        "medclaim.startup",
        environment=settings.APP_ENV,
        market=settings.MARKET,
    )
    yield
    logger.info("medclaim.shutdown")


app = FastAPI(
    title="MedClaim API",
    description="Autonomous Insurance Claim Lifecycle Agent — REST API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tightened in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health Check ---
@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """
    System health endpoint.
    Returns connectivity status for all external dependencies.
    Expanded in Subphase 1.4 with real connectivity checks.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
        "market": settings.MARKET,
        "services": {
            "groq": "not_configured",
            "qdrant": "not_configured",
            "supabase": "not_configured",
            "hapi_fhir": "not_configured",
        },
    }

"""
MedClaim — Structured Logging Configuration

Uses structlog to produce machine-readable JSON logs in production
and human-readable colored output in development.

Every agent, service, and API endpoint uses this logger for consistent
structured event logging with fields like claim_id, agent_name, latency_ms, etc.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "DEBUG", environment: str = "development") -> structlog.BoundLogger:
    """
    Configure structlog for the application.

    Args:
        log_level: Python log level string (DEBUG, INFO, WARNING, ERROR).
        environment: 'development' for pretty console output,
                     'production' for JSON-serialized output.

    Returns:
        A configured structlog BoundLogger instance.
    """
    # Shared processors for both dev and prod
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "production":
        # JSON output for machine parsing (Render, log aggregators)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Pretty colored output for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))

    # Quiet noisy third-party loggers
    for noisy_logger in ["httpx", "httpcore", "urllib3", "hpack"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    return structlog.get_logger("medclaim")

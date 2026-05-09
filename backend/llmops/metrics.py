"""
MedClaim — Prometheus Custom Metrics

Defines custom Prometheus metrics beyond the auto-instrumented HTTP metrics:
- Groq token usage per hour (counter)
- Qdrant query latency (histogram)
- Agent processing duration (histogram, per agent)
- Circuit breaker state (gauge)
- Claims processed (counter, by status)

Implementation: Subphase 1.4 (base) / Phase 4 (custom metrics)
"""

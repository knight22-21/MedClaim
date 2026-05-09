"""
MedClaim — Embedding Generation

Wraps Ollama (local, nomic-embed-text) for development and batch ingestion.
Falls back to HuggingFace Inference API (free tier) when Ollama is unavailable
(e.g., production on Render).

Both backends produce 768-dimensional vectors compatible with Qdrant collections.

Implementation: Subphase 1.3
"""

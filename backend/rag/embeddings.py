"""
MedClaim — Embedding Generation

Provides a unified interface for generating embeddings using:
  1. Ollama (primary) — local, free, nomic-embed-text (768-dim)
  2. HuggingFace Inference API (fallback) — free tier, for production on Render

Both backends produce 768-dimensional vectors compatible with all Qdrant collections.

Usage:
    from backend.rag.embeddings import get_embedding_function

    embed_fn = get_embedding_function()
    vectors = embed_fn.embed_documents(["medical text here"])
    query_vec = embed_fn.embed_query("ICD-10 code for pneumonia")
"""

from __future__ import annotations

import logging
from typing import Protocol

from langchain_community.embeddings import OllamaEmbeddings

logger = logging.getLogger("medclaim.rag.embeddings")

# Model configuration
OLLAMA_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = "http://localhost:11434"
HF_MODEL = "nomic-ai/nomic-embed-text-v1.5"
VECTOR_DIMENSION = 768


class EmbeddingFunction(Protocol):
    """Protocol for embedding functions used throughout MedClaim."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


def get_ollama_embeddings() -> OllamaEmbeddings:
    """
    Create Ollama embedding function using nomic-embed-text.

    Requires Ollama running locally with the model pulled:
        ollama pull nomic-embed-text

    Returns:
        OllamaEmbeddings instance.
    """
    return OllamaEmbeddings(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
    )


def get_hf_embeddings():
    """
    Create HuggingFace Inference API embedding function (fallback).

    Used when Ollama is unavailable (e.g., production on Render).
    Requires HUGGINGFACE_API_KEY environment variable.

    Returns:
        HuggingFaceInferenceAPIEmbeddings instance.
    """
    try:
        from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
    except ImportError:
        raise ImportError(
            "langchain-community with HuggingFace support is required. "
            "Install with: pip install langchain-community"
        )

    import os

    api_key = os.environ.get("HUGGINGFACE_API_KEY", "")
    if not api_key:
        raise ValueError(
            "HUGGINGFACE_API_KEY environment variable is not set. "
            "Required for HuggingFace fallback embeddings."
        )

    return HuggingFaceInferenceAPIEmbeddings(
        api_key=api_key,
        model_name=HF_MODEL,
    )


def get_embedding_function(prefer_ollama: bool = True) -> EmbeddingFunction:
    """
    Get the best available embedding function.

    Tries Ollama first (local, fast, free). Falls back to HuggingFace
    Inference API if Ollama is unavailable.

    Args:
        prefer_ollama: If True, try Ollama before HuggingFace.

    Returns:
        An embedding function implementing embed_documents() and embed_query().

    Raises:
        RuntimeError: If no embedding backend is available.
    """
    if prefer_ollama:
        try:
            embeddings = get_ollama_embeddings()
            # Test connectivity with a small embedding
            test_result = embeddings.embed_query("test")
            if len(test_result) == VECTOR_DIMENSION:
                logger.info(
                    f"Using Ollama embeddings (model={OLLAMA_MODEL}, dimension={VECTOR_DIMENSION})"
                )
                return embeddings
            else:
                logger.warning(
                    f"Ollama returned unexpected dimension (expected={VECTOR_DIMENSION}, actual={len(test_result)})"
                )
        except Exception as e:
            logger.warning(f"Ollama unavailable, trying HuggingFace fallback: {e}")

    # Fallback to HuggingFace
    try:
        embeddings = get_hf_embeddings()
        logger.info(
            f"Using HuggingFace Inference API embeddings (model={HF_MODEL}, dimension={VECTOR_DIMENSION})"
        )
        return embeddings
    except Exception as e:
        logger.error(f"HuggingFace fallback also failed: {e}")

    raise RuntimeError(
        "No embedding backend available. Either:\n"
        "  1. Start Ollama locally: ollama serve && ollama pull nomic-embed-text\n"
        "  2. Set HUGGINGFACE_API_KEY for the HuggingFace fallback"
    )


def embed_batch(
    texts: list[str],
    embed_fn: EmbeddingFunction | None = None,
    batch_size: int = 100,
    show_progress: bool = True,
) -> list[list[float]]:
    """
    Embed a list of texts in batches with progress reporting.

    Args:
        texts: List of text strings to embed.
        embed_fn: Embedding function to use. If None, auto-detects.
        batch_size: Number of texts per batch.
        show_progress: If True, print progress to stdout.

    Returns:
        List of embedding vectors (each 768-dimensional).
    """
    if embed_fn is None:
        embed_fn = get_embedding_function()

    all_embeddings: list[list[float]] = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_num = i // batch_size + 1

        if show_progress:
            print(f"  Embedding batch {batch_num}/{total_batches} ({len(batch)} texts)...", end=" ")

        embeddings = embed_fn.embed_documents(batch)
        all_embeddings.extend(embeddings)

        if show_progress:
            print("✓")

    return all_embeddings

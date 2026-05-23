"""
MedClaim — RAG Retrievers

Configures LangChain Qdrant retrievers for each collection with
search parameters, metadata filters, and minimum similarity thresholds.

The 0.70 cosine similarity threshold flags LOW_CONFIDENCE retrievals
to prevent hallucination from irrelevant documents.

Usage:
    from backend.rag.retrievers import get_retriever

    retriever = get_retriever("coding_rules", filter_kwargs={"code_type": "ICD10"})
    docs = retriever.invoke("pneumonia coding guidelines")
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from backend.app.config import settings
from backend.rag.embeddings import get_embedding_function
from backend.rag.setup import VECTOR_SIZE

logger = logging.getLogger("medclaim.rag.retrievers")

# Minimum cosine similarity threshold per collection
# Retrievals below this are flagged as LOW_CONFIDENCE
SIMILARITY_THRESHOLDS = {
    "coding_rules": 0.70,
    "payer_policies": 0.70,
    "denial_patterns": 0.65,      # Lower threshold — synthetic data is noisier
    "clinical_guidelines": 0.70,
}

# Default number of documents to retrieve per query
DEFAULT_TOP_K = {
    "coding_rules": 5,
    "payer_policies": 3,
    "denial_patterns": 10,        # More examples for few-shot denial prediction
    "clinical_guidelines": 3,
}


def _get_qdrant_client() -> QdrantClient:
    """Get a Qdrant client from settings."""
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )


def get_vector_store(collection_name: str) -> QdrantVectorStore:
    """
    Get a LangChain QdrantVectorStore for the specified collection.

    Args:
        collection_name: Name of the Qdrant collection.

    Returns:
        QdrantVectorStore instance connected to the collection.
    """
    embed_fn = get_embedding_function()
    client = _get_qdrant_client()

    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embed_fn,
    )


def build_qdrant_filter(filter_kwargs: dict[str, Any] | None = None) -> Filter | None:
    """
    Build a Qdrant Filter from simple key-value pairs.

    Args:
        filter_kwargs: Dict of field_name → value to match.
                       e.g., {"payer_name": "Medicare", "policy_type": "LCD"}

    Returns:
        Qdrant Filter object, or None if no filters.
    """
    if not filter_kwargs:
        return None

    conditions = [
        FieldCondition(key=key, match=MatchValue(value=value))
        for key, value in filter_kwargs.items()
        if value is not None
    ]

    if not conditions:
        return None

    return Filter(must=conditions)


def get_retriever(
    collection_name: str,
    top_k: int | None = None,
    filter_kwargs: dict[str, Any] | None = None,
    score_threshold: float | None = None,
):
    """
    Get a configured LangChain retriever for the specified collection.

    Args:
        collection_name: One of 'coding_rules', 'payer_policies',
                         'denial_patterns', 'clinical_guidelines'.
        top_k: Number of documents to retrieve. Defaults to collection-specific value.
        filter_kwargs: Metadata filters as key-value pairs.
        score_threshold: Minimum similarity score. Defaults to collection threshold.

    Returns:
        LangChain retriever with search kwargs configured.
    """
    if collection_name not in SIMILARITY_THRESHOLDS:
        raise ValueError(
            f"Unknown collection: {collection_name}. "
            f"Valid: {list(SIMILARITY_THRESHOLDS.keys())}"
        )

    vector_store = get_vector_store(collection_name)

    k = top_k or DEFAULT_TOP_K.get(collection_name, 5)
    threshold = score_threshold or SIMILARITY_THRESHOLDS[collection_name]

    search_kwargs: dict[str, Any] = {"k": k}

    # Add filter if provided
    qdrant_filter = build_qdrant_filter(filter_kwargs)
    if qdrant_filter:
        search_kwargs["filter"] = qdrant_filter

    # Add score threshold
    search_kwargs["score_threshold"] = threshold

    logger.info(
        "retriever.configured"
        f" (collection={collection_name}, "
        f"top_k={k}, "
        f"threshold={threshold}, "
        f"filters={list(filter_kwargs.keys()) if filter_kwargs else []})"
    )

    return vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs=search_kwargs,
    )


def retrieve_with_scores(
    collection_name: str,
    query: str,
    top_k: int | None = None,
    filter_kwargs: dict[str, Any] | None = None,
) -> list[tuple[Any, float]]:
    """
    Retrieve documents with similarity scores for quality monitoring.

    Returns (document, score) tuples sorted by descending score.
    Logs a LOW_CONFIDENCE warning if the top score is below threshold.

    Args:
        collection_name: Qdrant collection name.
        query: Query text.
        top_k: Number of results.
        filter_kwargs: Metadata filters.

    Returns:
        List of (Document, score) tuples.
    """
    vector_store = get_vector_store(collection_name)
    k = top_k or DEFAULT_TOP_K.get(collection_name, 5)

    search_kwargs = {"k": k}
    qdrant_filter = build_qdrant_filter(filter_kwargs)
    if qdrant_filter:
        search_kwargs["filter"] = qdrant_filter

    results = vector_store.similarity_search_with_score(query, **search_kwargs)

    # Quality monitoring: check top similarity score
    threshold = SIMILARITY_THRESHOLDS.get(collection_name, 0.70)
    if results:
        top_score = results[0][1]
        if top_score < threshold:
            logger.warning(
                "retrieval.low_confidence "
                f"(collection={collection_name}, "
                f"query_preview={query[:100]}, "
                f"top_score={round(top_score, 4)}, "
                f"threshold={threshold}, "
                f"num_results={len(results)}",
            )
        else:
            logger.info(
                "retrieval.success"
                f" (collection={collection_name}, "
                f"top_score={round(top_score, 4)}, "
                f"num_results={len(results)}")
    else:
        logger.warning(
            "retrieval.no_results"
            f" (collection={collection_name}, "
            f"query_preview={query[:100]}",
        )

    return results

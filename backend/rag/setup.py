"""
MedClaim — Qdrant Collection Setup

Creates and configures the four Qdrant vector collections with appropriate
vector size, distance metric, and payload indexes for filtered retrieval.

Collections:
    1. coding_rules      — ICD-10-CM/CPT codes + AHA coding guidelines
    2. payer_policies     — CMS NCDs/LCDs + commercial/IRDAI policies
    3. denial_patterns    — Historical claim-outcome pairs (feedback loop)
    4. clinical_guidelines — USPSTF/WHO clinical recommendations

Usage:
    python -m backend.rag.setup
"""

from __future__ import annotations

import sys
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    VectorParams,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import settings  # noqa: E402

# Embedding dimension for nomic-embed-text
VECTOR_SIZE = 768
DISTANCE_METRIC = Distance.COSINE


def get_qdrant_client() -> QdrantClient:
    """
    Returns a Qdrant client connected to the Qdrant Cloud cluster.

    Raises:
        ValueError: If QDRANT_URL or QDRANT_API_KEY is not configured.
    """
    if not settings.QDRANT_URL:
        raise ValueError("QDRANT_URL is not configured. Check your .env file.")
    if not settings.QDRANT_API_KEY:
        raise ValueError("QDRANT_API_KEY is not configured. Check your .env file.")

    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )


# =============================================================================
# Collection Definitions
# =============================================================================

COLLECTIONS = {
    "coding_rules": {
        "description": "ICD-10-CM/CPT code descriptors and AHA Coding Clinic guidelines",
        "vector_params": VectorParams(size=VECTOR_SIZE, distance=DISTANCE_METRIC),
        "payload_indexes": {
            "code": PayloadSchemaType.KEYWORD,
            "code_type": PayloadSchemaType.KEYWORD,  # ICD10, CPT, HCPCS
            "chapter": PayloadSchemaType.KEYWORD,
            "category": PayloadSchemaType.KEYWORD,
            "payer_specificity": PayloadSchemaType.KEYWORD,  # UNIVERSAL or payer name
            "source": PayloadSchemaType.KEYWORD,  # CMS, AHA_GUIDELINE
            "market": PayloadSchemaType.KEYWORD,
        },
    },
    "payer_policies": {
        "description": "CMS NCDs/LCDs, commercial payer policies, IRDAI circulars",
        "vector_params": VectorParams(size=VECTOR_SIZE, distance=DISTANCE_METRIC),
        "payload_indexes": {
            "payer_name": PayloadSchemaType.KEYWORD,
            "policy_id": PayloadSchemaType.KEYWORD,
            "policy_type": PayloadSchemaType.KEYWORD,  # NCD, LCD, COMMERCIAL, IRDAI
            "effective_date": PayloadSchemaType.KEYWORD,
            "market": PayloadSchemaType.KEYWORD,  # US, INDIA
            "page_number": PayloadSchemaType.INTEGER,
            "section_header": PayloadSchemaType.KEYWORD,
        },
    },
    "denial_patterns": {
        "description": "Historical claim-outcome pairs for denial prediction",
        "vector_params": VectorParams(size=VECTOR_SIZE, distance=DISTANCE_METRIC),
        "payload_indexes": {
            "payer_name": PayloadSchemaType.KEYWORD,
            "outcome": PayloadSchemaType.KEYWORD,  # APPROVED, DENIED, etc.
            "facility_type": PayloadSchemaType.KEYWORD,
            "denial_reason_code": PayloadSchemaType.KEYWORD,
            "market": PayloadSchemaType.KEYWORD,
            "billed_amount_range": PayloadSchemaType.KEYWORD,  # LOW, MEDIUM, HIGH
        },
    },
    "clinical_guidelines": {
        "description": "USPSTF recommendations, CMS clinical criteria, WHO guidelines",
        "vector_params": VectorParams(size=VECTOR_SIZE, distance=DISTANCE_METRIC),
        "payload_indexes": {
            "guideline_source": PayloadSchemaType.KEYWORD,  # USPSTF, CMS, WHO, NICE
            "evidence_level": PayloadSchemaType.KEYWORD,  # A, B, C, D, I
            "clinical_topic": PayloadSchemaType.KEYWORD,
            "market": PayloadSchemaType.KEYWORD,
        },
    },
}


def create_collections(recreate: bool = False) -> None:
    """
    Create all four Qdrant collections with vector config and payload indexes.

    Args:
        recreate: If True, delete existing collections before creating.
                  Use with caution — this destroys all indexed data.
    """
    print("=" * 60)
    print("MedClaim — Qdrant Collection Setup")
    print("=" * 60)

    client = get_qdrant_client()

    # Get existing collections
    existing = {c.name for c in client.get_collections().collections}
    print(f"\nExisting collections: {existing or 'none'}")

    for name, config in COLLECTIONS.items():
        print(f"\n{'─' * 40}")
        print(f"Collection: {name}")
        print(f"  {config['description']}")

        if name in existing:
            if recreate:
                print("  ⚠️  Deleting existing collection...")
                client.delete_collection(name)
            else:
                print("  ✅ Already exists — skipping (use --recreate to reset)")
                continue

        # Create collection
        print(
            f"  📦 Creating collection (vector_size={VECTOR_SIZE}, distance={DISTANCE_METRIC})..."
        )
        client.create_collection(
            collection_name=name,
            vectors_config=config["vector_params"],
        )

        # Create payload indexes for efficient filtered search
        print(f"  🔍 Creating {len(config['payload_indexes'])} payload indexes...")
        for field_name, field_type in config["payload_indexes"].items():
            client.create_payload_index(
                collection_name=name,
                field_name=field_name,
                field_schema=field_type,
            )
            print(f"     ✓ {field_name} ({field_type})")

        print(f"  ✅ Collection '{name}' created successfully")

    # Summary
    print(f"\n{'=' * 60}")
    updated = {c.name for c in client.get_collections().collections}
    print(f"Collections now available: {updated}")
    print("Setup complete!")


def verify_collections() -> dict[str, dict]:
    """
    Verify all collections exist and return their info.

    Returns:
        Dict mapping collection name → {point_count, vector_size, status}.
    """
    client = get_qdrant_client()
    results = {}

    for name in COLLECTIONS:
        try:
            info = client.get_collection(name)
            status_attr = getattr(info, "status", None)
            results[name] = {
                "points_count": getattr(info, "points_count", 0),
                "status": status_attr.value if status_attr else None,
                "vector_size": getattr(info.config.params.vectors, "size", 768),
            }
        except Exception as e:
            results[name] = {"error": str(e)}

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MedClaim Qdrant Collection Setup")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate existing collections (destroys all data)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify existing collections, don't create",
    )
    args = parser.parse_args()

    if args.verify:
        info = verify_collections()
        for name, details in info.items():
            print(f"{name}: {details}")
    else:
        create_collections(recreate=args.recreate)

"""
MedClaim — Master Ingestion Runner

Runs all data ingestion pipelines in the correct order:
    1. Download source data files
    2. Create Qdrant collections (if not existing)
    3. Ingest coding rules (ICD-10-CM + CPT)
    4. Ingest payer policies
    5. Ingest clinical guidelines
    6. Verify collection point counts

Usage:
    python -m data.ingestion.run_all
    python -m data.ingestion.run_all --skip-download
    python -m data.ingestion.run_all --collections-only
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def run_all(
    skip_download: bool = False,
    collections_only: bool = False,
    icd10_limit: int | None = None,
) -> None:
    """Execute all ingestion pipelines."""
    print("=" * 60)
    print("MedClaim — Full Data Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Download source data
    if not skip_download and not collections_only:
        print("\n" + "=" * 60)
        print("STEP 1: Downloading source data")
        print("=" * 60)
        from data.ingestion.download_sources import download_all
        download_all()

    # Step 2: Create Qdrant collections
    print("\n" + "=" * 60)
    print("STEP 2: Creating Qdrant collections")
    print("=" * 60)
    from backend.rag.setup import create_collections
    create_collections(recreate=False)

    if collections_only:
        print("\n✅ Collections created. Skipping data ingestion.")
        return

    # Step 3: Ingest coding rules
    print("\n" + "=" * 60)
    print("STEP 3: Ingesting coding rules")
    print("=" * 60)
    from data.ingestion.ingest_coding_rules import run as ingest_coding
    ingest_coding(limit=icd10_limit)

    # Step 4: Ingest payer policies
    print("\n" + "=" * 60)
    print("STEP 4: Ingesting payer policies")
    print("=" * 60)
    from data.ingestion.ingest_payer_policies import run as ingest_policies
    ingest_policies()

    # Step 5: Ingest clinical guidelines
    print("\n" + "=" * 60)
    print("STEP 5: Ingesting clinical guidelines")
    print("=" * 60)
    from data.ingestion.ingest_clinical_guidelines import run as ingest_guidelines
    ingest_guidelines()

    # Step 6: Verify
    print("\n" + "=" * 60)
    print("STEP 6: Verification")
    print("=" * 60)
    from backend.rag.setup import verify_collections
    info = verify_collections()
    for name, details in info.items():
        count = details.get("points_count", "?")
        status = details.get("status", "?")
        print(f"  {name}: {count} points ({status})")

    print(f"\n{'=' * 60}")
    print("✅ Full ingestion pipeline complete!")
    print("   denial_patterns collection is intentionally empty")
    print("   (populated by synthetic claim generator in Phase 2)")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Run all MedClaim data ingestion")
    p.add_argument("--skip-download", action="store_true", help="Skip downloading source files")
    p.add_argument("--collections-only", action="store_true", help="Only create collections")
    p.add_argument("--icd10-limit", type=int, default=None, help="Limit ICD-10 codes (for testing)")
    args = p.parse_args()

    run_all(
        skip_download=args.skip_download,
        collections_only=args.collections_only,
        icd10_limit=args.icd10_limit,
    )

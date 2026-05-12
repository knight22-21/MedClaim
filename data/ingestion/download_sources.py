"""
MedClaim — Data Source Downloader

Downloads public domain medical/regulatory data for Qdrant collections.

Usage:
    python -m data.ingestion.download_sources
    python -m data.ingestion.download_sources --source icd10
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

SOURCES = {
    "icd10_codes": {
        "desc": "ICD-10-CM 2025 Code Descriptions (Long Format)",
        "url": "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip",
        "filename": "icd10cm_codes_2025.zip",
        "extracted": "icd10cm_order_2025.txt",
    },
    "icd10_guidelines": {
        "desc": "ICD-10-CM Official Guidelines FY2025 (PDF)",
        "url": "https://www.cms.gov/files/document/fy-2025-icd-10-cm-coding-guidelines.pdf",
        "filename": "icd10cm_guidelines_2025.pdf",
    },
    "uspstf": {
        "desc": "USPSTF Clinical Recommendations (JSON)",
        "url": "https://data.uspreventiveservicestaskforce.org/api/json",
        "filename": "uspstf_recommendations.json",
    },
}


def _download(url: str, dest: Path, desc: str = "") -> bool:
    """Download a file. Skips if already exists."""
    if dest.exists():
        print(f"  ⏭️  Exists: {dest.name}")
        return True
    print(f"  ⬇️  {desc or dest.name}")
    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            mb = len(r.content) / (1024 * 1024)
            print(f"  ✅ {dest.name} ({mb:.1f} MB)")
            return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def download_icd10_codes() -> Path | None:
    """Download and extract ICD-10-CM 2025 code file."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    s = SOURCES["icd10_codes"]
    zip_path = RAW_DATA_DIR / s["filename"]
    txt_path = RAW_DATA_DIR / s["extracted"]

    if txt_path.exists():
        print(f"  ⏭️  Exists: {txt_path.name}")
        return txt_path

    if not _download(s["url"], zip_path, s["desc"]):
        return None

    print(f"  📦 Extracting...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(RAW_DATA_DIR)

    # Find the order file (name may vary)
    for f in RAW_DATA_DIR.iterdir():
        if "order" in f.name.lower() and f.suffix == ".txt":
            return f
    return txt_path if txt_path.exists() else None


def download_icd10_guidelines() -> Path | None:
    s = SOURCES["icd10_guidelines"]
    dest = RAW_DATA_DIR / s["filename"]
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return dest if _download(s["url"], dest, s["desc"]) else None


def download_uspstf() -> Path | None:
    s = SOURCES["uspstf"]
    dest = RAW_DATA_DIR / s["filename"]
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return dest if _download(s["url"], dest, s["desc"]) else None


def download_all() -> dict[str, Path | None]:
    print("=" * 60)
    print("MedClaim — Data Source Downloader")
    print(f"📂 Target: {RAW_DATA_DIR}")
    print("=" * 60)

    results = {}

    print("\n1. ICD-10-CM 2025 Codes")
    results["icd10_codes"] = download_icd10_codes()

    print("\n2. ICD-10-CM Guidelines PDF")
    results["icd10_guidelines"] = download_icd10_guidelines()

    print("\n3. USPSTF Recommendations")
    results["uspstf"] = download_uspstf()

    print(f"\n{'=' * 60}")
    for name, path in results.items():
        s = "✅" if path and path.exists() else "❌"
        print(f"  {s} {name}: {path or 'FAILED'}")
    return results


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Download MedClaim data sources")
    p.add_argument("--source", choices=["icd10", "guidelines", "uspstf", "all"], default="all")
    args = p.parse_args()

    if args.source == "icd10":
        download_icd10_codes()
    elif args.source == "guidelines":
        download_icd10_guidelines()
    elif args.source == "uspstf":
        download_uspstf()
    else:
        download_all()

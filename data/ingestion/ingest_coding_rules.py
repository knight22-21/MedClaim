"""
MedClaim — Coding Rules Ingestion

Parses ICD-10-CM 2025 code descriptions from the CMS flat file and
upserts them into the coding_rules Qdrant collection.

The CMS order file format (fixed-width):
    Col 1-5:   Order number
    Col 7-13:  ICD-10-CM code (no dot)
    Col 15:    Header flag (0=billable, 1=header)
    Col 17+:   Short description / Long description

Usage:
    python -m data.ingestion.ingest_coding_rules
    python -m data.ingestion.ingest_coding_rules --limit 500
"""

from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import time
from qdrant_client.http.exceptions import ResponseHandlingException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import settings  # noqa: E402
from backend.rag.embeddings import embed_batch, get_embedding_function  # noqa: E402

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "raw"
COLLECTION = "coding_rules"
BATCH_SIZE = 100


def safe_upsert(client, collection, points, retries=3):
    for i in range(retries):
        try:
            return client.upsert(
                collection_name=collection,
                points=points
            )
        except Exception as e:
            print(f"⚠️ Upsert failed (attempt {i+1}/{retries}): {e}")
            time.sleep(2)
    raise Exception("❌ Upsert failed after retries")

def classify_icd10_chapter(code: str) -> str:
    """Map an ICD-10-CM code to its chapter letter range."""
    first = code[0].upper()
    chapter_map = {
        "A": "A00-B99 Infectious diseases",
        "B": "A00-B99 Infectious diseases",
        "C": "C00-D49 Neoplasms",
        "D": "D50-D89 Blood diseases",
        "E": "E00-E89 Endocrine/metabolic",
        "F": "F01-F99 Mental/behavioral",
        "G": "G00-G99 Nervous system",
        "H": "H00-H59 Eye / H60-H95 Ear",
        "I": "I00-I99 Circulatory system",
        "J": "J00-J99 Respiratory system",
        "K": "K00-K95 Digestive system",
        "L": "L00-L99 Skin/subcutaneous",
        "M": "M00-M99 Musculoskeletal",
        "N": "N00-N99 Genitourinary",
        "O": "O00-O9A Pregnancy/childbirth",
        "P": "P00-P96 Perinatal conditions",
        "Q": "Q00-Q99 Congenital anomalies",
        "R": "R00-R99 Symptoms/signs",
        "S": "S00-T88 Injury/poisoning",
        "T": "S00-T88 Injury/poisoning",
        "V": "V00-Y99 External causes",
        "W": "V00-Y99 External causes",
        "X": "V00-Y99 External causes",
        "Y": "V00-Y99 External causes",
        "Z": "Z00-Z99 Health encounters",
    }
    return chapter_map.get(first, "Unknown")


def format_icd10_code(raw: str) -> str:
    """Insert dot after 3rd character: 'J189' → 'J18.9'."""
    raw = raw.strip()
    if len(raw) > 3:
        return f"{raw[:3]}.{raw[3:]}"
    return raw


def parse_icd10_order_file(filepath: Path, limit: int | None = None) -> list[dict]:
    """
    Parse the CMS ICD-10-CM order file into structured records.

    Returns list of dicts with keys: code, description, is_billable, chapter, category.
    """
    records = []
    print(f"  📄 Parsing: {filepath.name}")

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line.strip()) < 17:
                continue

            try:
                raw_code = line[6:13].strip()
                is_header = line[14:15].strip() == "1"
                description = line[16:].strip()
            except IndexError:
                continue

            if not raw_code or not description:
                continue

            code = format_icd10_code(raw_code)
            chapter = classify_icd10_chapter(raw_code)
            # Category = first 3 chars (e.g., J18 from J18.9)
            category = raw_code[:3] if len(raw_code) >= 3 else raw_code

            records.append({
                "code": code,
                "raw_code": raw_code,
                "description": description,
                "is_billable": not is_header,
                "chapter": chapter,
                "category": category,
                "code_type": "ICD10",
                "payer_specificity": "UNIVERSAL",
                "source": "CMS",
            })

            if limit and len(records) >= limit:
                break

    print(f"  ✅ Parsed {len(records)} codes")
    return records


# --- Curated CPT short descriptors (CMS public short descriptors) ---
CURATED_CPT_CODES = [
    {"code": "99213", "description": "Office/outpatient visit est patient low complexity", "category": "E/M"},
    {"code": "99214", "description": "Office/outpatient visit est patient moderate complexity", "category": "E/M"},
    {"code": "99215", "description": "Office/outpatient visit est patient high complexity", "category": "E/M"},
    {"code": "99283", "description": "Emergency department visit moderate severity", "category": "E/M"},
    {"code": "99284", "description": "Emergency department visit high severity", "category": "E/M"},
    {"code": "99285", "description": "Emergency department visit high severity with threat", "category": "E/M"},
    {"code": "27447", "description": "Total knee replacement arthroplasty", "category": "Musculoskeletal"},
    {"code": "27130", "description": "Total hip replacement arthroplasty", "category": "Musculoskeletal"},
    {"code": "43239", "description": "Upper GI endoscopy with biopsy", "category": "Digestive"},
    {"code": "45378", "description": "Diagnostic colonoscopy", "category": "Digestive"},
    {"code": "45380", "description": "Colonoscopy with biopsy", "category": "Digestive"},
    {"code": "47562", "description": "Laparoscopic cholecystectomy", "category": "Digestive"},
    {"code": "44970", "description": "Laparoscopic appendectomy", "category": "Digestive"},
    {"code": "66984", "description": "Cataract extraction with IOL insertion", "category": "Eye"},
    {"code": "92920", "description": "Percutaneous transluminal coronary angioplasty", "category": "Cardiovascular"},
    {"code": "92928", "description": "Intravascular coronary stent placement", "category": "Cardiovascular"},
    {"code": "93000", "description": "Electrocardiogram 12-lead complete", "category": "Cardiovascular"},
    {"code": "93306", "description": "Transthoracic echocardiography complete", "category": "Cardiovascular"},
    {"code": "37184", "description": "Primary percutaneous mechanical thrombectomy", "category": "Cardiovascular"},
    {"code": "70553", "description": "MRI brain with and without contrast", "category": "Radiology"},
    {"code": "71260", "description": "CT chest with contrast", "category": "Radiology"},
    {"code": "74177", "description": "CT abdomen and pelvis with contrast", "category": "Radiology"},
    {"code": "90471", "description": "Immunization administration first vaccine", "category": "Immunization"},
    {"code": "90686", "description": "Influenza vaccine quadrivalent", "category": "Immunization"},
    {"code": "81001", "description": "Urinalysis automated with microscopy", "category": "Pathology"},
    {"code": "85025", "description": "Complete blood count with differential automated", "category": "Pathology"},
    {"code": "80053", "description": "Comprehensive metabolic panel", "category": "Pathology"},
    {"code": "31500", "description": "Emergency endotracheal intubation", "category": "Respiratory"},
    {"code": "94003", "description": "Ventilator management initial day", "category": "Respiratory"},
    {"code": "94640", "description": "Nebulizer treatment inhalation", "category": "Respiratory"},
    {"code": "59400", "description": "Routine obstetric care including delivery", "category": "Maternity"},
    {"code": "59510", "description": "Cesarean delivery including postpartum care", "category": "Maternity"},
    {"code": "27236", "description": "Open treatment femoral fracture internal fixation", "category": "Musculoskeletal"},
    {"code": "63030", "description": "Lumbar laminotomy with decompression", "category": "Spine"},
    {"code": "22612", "description": "Lumbar arthrodesis posterior technique", "category": "Spine"},
    {"code": "32405", "description": "Thoracentesis with imaging guidance", "category": "Respiratory"},
    {"code": "32555", "description": "Pleural drainage percutaneous", "category": "Respiratory"},
]


def build_cpt_records() -> list[dict]:
    """Build CPT code records from curated short descriptors."""
    records = []
    for cpt in CURATED_CPT_CODES:
        records.append({
            "code": cpt["code"],
            "raw_code": cpt["code"],
            "description": cpt["description"],
            "is_billable": True,
            "chapter": cpt["category"],
            "category": cpt["category"],
            "code_type": "CPT",
            "payer_specificity": "UNIVERSAL",
            "source": "CMS",
        })
    return records


def ingest_to_qdrant(records: list[dict], batch_size: int = BATCH_SIZE) -> int:
    """Embed records and upsert into the coding_rules Qdrant collection."""
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    embed_fn = get_embedding_function()

    total_upserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(records) + batch_size - 1) // batch_size

        # Build text for embedding: "CODE: description"
        texts = [f"{r['code']}: {r['description']}" for r in batch]

        print(f"  Batch {batch_num}/{total_batches}: embedding {len(texts)} codes...", end=" ")
        vectors = embed_fn.embed_documents(texts)

        points = []
        for rec, vec in zip(batch, vectors):
            points.append(PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"coding_{rec['code']}")),
                vector=vec,
                payload={
                    "code": rec["code"],
                    "description": rec["description"],
                    "code_type": rec["code_type"],
                    "chapter": rec["chapter"],
                    "category": rec["category"],
                    "payer_specificity": rec["payer_specificity"],
                    "source": rec["source"],
                    "is_billable": rec["is_billable"],
                    "text": texts[batch.index(rec)],
                },
            ))

        safe_upsert(client, COLLECTION, points)
        total_upserted += len(points)
        print(f"✓ ({total_upserted}/{len(records)})")

    return total_upserted


def run(limit: int | None = None) -> None:
    """Main ingestion pipeline for coding_rules."""
    print("=" * 60)
    print("MedClaim — Coding Rules Ingestion")
    print("=" * 60)

    all_records: list[dict] = []

    # 1. Parse ICD-10-CM codes
    order_file = RAW_DATA_DIR / "icd10cm_order_2025.txt"
    if order_file.exists():
        print("\n📋 ICD-10-CM Codes:")
        icd_records = parse_icd10_order_file(order_file, limit=limit)
        all_records.extend(icd_records)
    else:
        # Look for any .txt file in raw dir that might be the order file
        found = False
        if RAW_DATA_DIR.exists():
            for f in RAW_DATA_DIR.iterdir():
                if "order" in f.name.lower() and f.suffix == ".txt":
                    print(f"\n📋 ICD-10-CM Codes (found as {f.name}):")
                    icd_records = parse_icd10_order_file(f, limit=limit)
                    all_records.extend(icd_records)
                    found = True
                    break
        if not found:
            print("\n⚠️  ICD-10-CM order file not found. Run download first:")
            print("   python -m data.ingestion.download_sources --source icd10")

    # 2. Add curated CPT codes
    print("\n📋 CPT Codes (curated short descriptors):")
    cpt_records = build_cpt_records()
    all_records.extend(cpt_records)
    print(f"  ✅ {len(cpt_records)} CPT codes")

    if not all_records:
        print("\n❌ No records to ingest.")
        return

    # 3. Upsert to Qdrant
    print(f"\n🔄 Upserting {len(all_records)} records to '{COLLECTION}' collection...")
    count = ingest_to_qdrant(all_records)

    print(f"\n{'=' * 60}")
    print(f"✅ Ingested {count} coding rules into Qdrant")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="Max ICD-10 codes to ingest")
    args = p.parse_args()
    run(limit=args.limit)

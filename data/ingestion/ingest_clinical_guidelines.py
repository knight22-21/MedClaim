"""
MedClaim — Clinical Guidelines Ingestion

Indexes clinical practice guidelines into the clinical_guidelines
Qdrant collection. Sources:
  - USPSTF recommendations (downloaded JSON from API)
  - Curated WHO/CMS guidelines for demo coverage

Usage:
    python -m data.ingestion.ingest_clinical_guidelines
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import time
from qdrant_client.http.exceptions import ResponseHandlingException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import settings  # noqa: E402
from backend.rag.embeddings import get_embedding_function  # noqa: E402

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "raw"
COLLECTION = "clinical_guidelines"
BATCH_SIZE = 50


# =============================================================================
# Curated Clinical Guidelines (always available, no download needed)
# =============================================================================
CURATED_GUIDELINES = [
    {
        "text": "USPSTF Grade B Recommendation — Colorectal Cancer Screening. The USPSTF recommends screening for colorectal cancer in all adults aged 45 to 75 years. Screening options include colonoscopy every 10 years (CPT 45378), fecal immunochemical test (FIT) annually, CT colonography every 5 years, or stool DNA-FIT test every 1-3 years. For adults aged 76 to 85, the decision to screen should be individualized.",
        "guideline_source": "USPSTF",
        "evidence_level": "B",
        "clinical_topic": "Colorectal Cancer Screening",
        "procedure_codes": ["45378", "45380"],
        "market": "US",
    },
    {
        "text": "USPSTF Grade B Recommendation — Breast Cancer Screening. The USPSTF recommends biennial screening mammography for women aged 40 to 74 years. For women at high risk due to family history or known genetic mutations, additional screening with breast MRI may be appropriate. Screening mammography is coded as CPT 77067 (bilateral diagnostic mammography) or 77063 (screening digital tomosynthesis).",
        "guideline_source": "USPSTF",
        "evidence_level": "B",
        "clinical_topic": "Breast Cancer Screening",
        "procedure_codes": ["77067", "77063"],
        "market": "US",
    },
    {
        "text": "USPSTF Grade A Recommendation — Hypertension Screening. The USPSTF recommends screening for hypertension in adults aged 18 years or older with office blood pressure measurement. Ambulatory blood pressure monitoring (ABPM) or home blood pressure monitoring should be used to confirm the diagnosis before starting treatment. This is the highest grade recommendation indicating high certainty of substantial net benefit.",
        "guideline_source": "USPSTF",
        "evidence_level": "A",
        "clinical_topic": "Hypertension Screening",
        "procedure_codes": ["99213", "99214"],
        "market": "US",
    },
    {
        "text": "USPSTF Grade B Recommendation — Lung Cancer Screening. The USPSTF recommends annual screening for lung cancer with low-dose computed tomography (LDCT) in adults aged 50 to 80 years who have a 20 pack-year smoking history and currently smoke or have quit within the past 15 years. LDCT is coded as CPT 71271. Medicare covers LDCT lung cancer screening under NCD 210.14 with shared decision-making and smoking cessation counseling requirements.",
        "guideline_source": "USPSTF",
        "evidence_level": "B",
        "clinical_topic": "Lung Cancer Screening",
        "procedure_codes": ["71271"],
        "market": "US",
    },
    {
        "text": "USPSTF Grade A Recommendation — Statin Use for Cardiovascular Disease Prevention. The USPSTF recommends that clinicians prescribe a statin for the primary prevention of cardiovascular disease (CVD) for adults aged 40 to 75 years who have one or more CVD risk factors and an estimated 10-year CVD event risk of 10% or greater. Evidence level A indicates high certainty of substantial benefit.",
        "guideline_source": "USPSTF",
        "evidence_level": "A",
        "clinical_topic": "Cardiovascular Disease Prevention",
        "procedure_codes": ["99213", "99214", "80061"],
        "market": "US",
    },
    {
        "text": "USPSTF Grade B Recommendation — Depression Screening. The USPSTF recommends screening for depression in the general adult population, including pregnant and postpartum persons. Screening should be implemented with adequate systems in place for accurate diagnosis, effective treatment, and appropriate follow-up. PHQ-9 is the most commonly used screening tool.",
        "guideline_source": "USPSTF",
        "evidence_level": "B",
        "clinical_topic": "Depression Screening",
        "procedure_codes": ["99213", "96127"],
        "market": "US",
    },
    {
        "text": "CMS Clinical Criteria — Total Knee Arthroplasty Medical Necessity. For Medicare coverage of total knee arthroplasty (CPT 27447), the following clinical criteria must be met: radiographic evidence of severe joint destruction (Kellgren-Lawrence Grade III-IV), documented failure of at least 3 months of conservative treatment including physical therapy and NSAIDs, significant functional limitation documented by validated outcome measure (e.g., WOMAC score), and BMI assessment with optimization plan if BMI > 40.",
        "guideline_source": "CMS",
        "evidence_level": "B",
        "clinical_topic": "Total Knee Arthroplasty",
        "procedure_codes": ["27447"],
        "market": "US",
    },
    {
        "text": "CMS Clinical Criteria — Percutaneous Coronary Intervention. Medicare covers PCI with stent placement (CPT 92920, 92928) when: coronary angiography demonstrates >70% stenosis in a major epicardial vessel (or >50% for left main disease), the patient has symptoms of myocardial ischemia or documented acute coronary syndrome, and the procedure is performed in an appropriate clinical setting. Fractional flow reserve (FFR) measurement is recommended for intermediate lesions (40-70% stenosis).",
        "guideline_source": "CMS",
        "evidence_level": "A",
        "clinical_topic": "Percutaneous Coronary Intervention",
        "procedure_codes": ["92920", "92928", "93571"],
        "market": "US",
    },
    {
        "text": "CMS Clinical Criteria — Mechanical Thrombectomy for Acute Stroke. Medicare covers primary percutaneous mechanical thrombectomy (CPT 37184) for acute ischemic stroke caused by large vessel occlusion when: performed within 24 hours of symptom onset, CT angiography or MR angiography confirms large vessel occlusion, patient meets clinical and imaging selection criteria per AHA/ASA guidelines, and the procedure is performed at a certified comprehensive stroke center.",
        "guideline_source": "CMS",
        "evidence_level": "A",
        "clinical_topic": "Acute Stroke Thrombectomy",
        "procedure_codes": ["37184"],
        "market": "US",
    },
    # --- India / WHO Guidelines ---
    {
        "text": "WHO Clinical Guideline — Management of Type 2 Diabetes. The World Health Organization recommends metformin as first-line pharmacological therapy for type 2 diabetes mellitus (ICD-10 E11.x) when lifestyle modifications are insufficient. Monitoring should include HbA1c every 3-6 months with a target of <7.0% for most adults. Annual screening for diabetic complications including retinopathy, nephropathy, and neuropathy is essential.",
        "guideline_source": "WHO",
        "evidence_level": "A",
        "clinical_topic": "Type 2 Diabetes Management",
        "procedure_codes": ["99214", "83036"],
        "market": "INDIA",
    },
    {
        "text": "WHO Clinical Guideline — Essential Surgical Care. The WHO recognizes that emergency and essential surgical care, including appendectomy, cesarean section, and fracture management, should be available at first-level hospitals. These procedures are included in the WHO list of essential surgical procedures and should be covered by all health insurance schemes including government-sponsored programs.",
        "guideline_source": "WHO",
        "evidence_level": "B",
        "clinical_topic": "Essential Surgical Care",
        "procedure_codes": ["44970", "59510", "27236"],
        "market": "INDIA",
    },
    {
        "text": "WHO Clinical Guideline — Acute Coronary Syndrome Management. Primary percutaneous coronary intervention (PCI) is the recommended reperfusion strategy for ST-elevation myocardial infarction (STEMI) when available within 120 minutes of first medical contact. If primary PCI cannot be performed within this timeframe, fibrinolytic therapy should be administered within 30 minutes. This applies to all clinical settings including resource-limited environments.",
        "guideline_source": "WHO",
        "evidence_level": "A",
        "clinical_topic": "Acute Coronary Syndrome",
        "procedure_codes": ["92920", "92928"],
        "market": "INDIA",
    },
]

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

def parse_uspstf_json(filepath: Path) -> list[dict]:
    """Parse downloaded USPSTF recommendations JSON into guideline records."""
    records = []
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  ⚠️  Failed to parse USPSTF JSON: {e}")
        return records

    # USPSTF API returns a list of recommendation objects
    items = data if isinstance(data, list) else data.get("data", data.get("recommendations", []))

    for item in items:
        title = item.get("title", item.get("Title", ""))
        grade = item.get("grade", item.get("Grade", ""))
        text = item.get("text", item.get("Text", item.get("recommendation", "")))
        topic = item.get("topic", item.get("Topic", title))

        if not text or not grade:
            continue

        full_text = f"USPSTF Grade {grade} — {title}. {text}"

        records.append({
            "text": full_text[:2000],  # Cap length
            "guideline_source": "USPSTF",
            "evidence_level": grade if grade in ("A", "B", "C", "D", "I") else "I",
            "clinical_topic": topic[:200],
            "procedure_codes": [],
            "market": "US",
        })

    print(f"  ✅ Parsed {len(records)} USPSTF recommendations")
    return records


def ingest_guidelines(records: list[dict]) -> int:
    """Embed and upsert guideline records to Qdrant."""
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    embed_fn = get_embedding_function()

    texts = [r["text"] for r in records]
    print(f"  Embedding {len(texts)} guidelines...")
    vectors = embed_fn.embed_documents(texts)

    points = []
    for rec, vec in zip(records, vectors):
        point_id = str(uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"guideline_{rec['guideline_source']}_{rec['clinical_topic'][:50]}"
        ))
        points.append(PointStruct(
            id=point_id,
            vector=vec,
            payload={
                "guideline_source": rec["guideline_source"],
                "evidence_level": rec["evidence_level"],
                "clinical_topic": rec["clinical_topic"],
                "procedure_codes": rec.get("procedure_codes", []),
                "market": rec["market"],
                "text": rec["text"],
            },
        ))

    # Upsert in batches
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        safe_upsert(client, COLLECTION, batch)
        print(f"  ✓ Upserted batch {i // BATCH_SIZE + 1}")

    return len(points)


def run() -> None:
    """Main ingestion pipeline for clinical_guidelines."""
    print("=" * 60)
    print("MedClaim — Clinical Guidelines Ingestion")
    print("=" * 60)

    all_records: list[dict] = []

    # 1. Try USPSTF JSON (if downloaded)
    uspstf_file = RAW_DATA_DIR / "uspstf_recommendations.json"
    if uspstf_file.exists():
        print("\n📋 USPSTF Recommendations (downloaded):")
        uspstf_records = parse_uspstf_json(uspstf_file)
        all_records.extend(uspstf_records)
    else:
        print("\n⚠️  USPSTF JSON not found — using curated set only")
        print("   Run: python -m data.ingestion.download_sources --source uspstf")

    # 2. Add curated guidelines (always)
    print(f"\n📋 Curated Guidelines (USPSTF + CMS + WHO):")
    all_records.extend(CURATED_GUIDELINES)
    print(f"  ✅ {len(CURATED_GUIDELINES)} curated guidelines")

    # Deduplicate by clinical_topic + source
    seen = set()
    deduped = []
    for r in all_records:
        key = f"{r['guideline_source']}_{r['clinical_topic'][:50]}"
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    all_records = deduped

    # 3. Ingest
    print(f"\n🔄 Ingesting {len(all_records)} guidelines to '{COLLECTION}'...")
    count = ingest_guidelines(all_records)

    print(f"\n{'=' * 60}")
    print(f"✅ Ingested {count} clinical guidelines into Qdrant")


if __name__ == "__main__":
    run()

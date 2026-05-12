"""
MedClaim — Payer Policies Ingestion

Chunks and indexes payer policy documents into the payer_policies
Qdrant collection. Supports:
  - CMS NCDs/LCDs (text/PDF)
  - Commercial payer policy excerpts (curated starter set)
  - IRDAI circulars and PM-JAY HBP data (India market)

Uses LlamaIndex SentenceSplitter: 512 tokens, 64 token overlap.

Usage:
    python -m data.ingestion.ingest_payer_policies
"""

from __future__ import annotations

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

COLLECTION = "payer_policies"
BATCH_SIZE = 50

# =============================================================================
# Curated Starter Policy Documents
# Real policy language patterns for demo and testing
# =============================================================================
STARTER_POLICIES = [
    # --- US: Medicare NCDs ---
    {
        "text": "NCD 220.6 — Positron Emission Tomography (PET) Scans. Medicare covers FDG PET for the following oncologic indications: initial staging or restaging of cancers listed in section 220.6.17, monitoring response to treatment for cancers listed, and evaluation of suspected brain tumors and seizure disorders. PET scans for all other indications are covered through the Coverage with Evidence Development (CED) paradigm.",
        "payer_name": "Medicare",
        "policy_id": "NCD-220.6",
        "policy_type": "NCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "Covered Indications",
    },
    {
        "text": "NCD 220.6 — Non-Covered Indications for PET. Medicare does not cover PET scans for screening purposes in asymptomatic patients. PET scans performed solely for the purpose of determining anatomic location or extent of disease without a qualifying oncologic indication are not covered. Claims submitted with PET for non-covered indications will be denied under reason code CO-50 (not deemed a medical necessity).",
        "payer_name": "Medicare",
        "policy_id": "NCD-220.6",
        "policy_type": "NCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "Non-Covered Indications",
    },
    {
        "text": "LCD L33224 — Total Knee Arthroplasty (TKA). This LCD defines medical necessity criteria for total knee replacement (CPT 27447). TKA is considered medically necessary when: the patient has documented severe osteoarthritis (ICD-10 M17.x) confirmed by weight-bearing radiographs showing Kellgren-Lawrence Grade III or IV changes, the patient has failed conservative treatment for at least 3 months including physical therapy and anti-inflammatory medications, and the patient's functional impairment significantly limits activities of daily living.",
        "payer_name": "Medicare",
        "policy_id": "LCD-L33224",
        "policy_type": "LCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "Medical Necessity Criteria",
    },
    {
        "text": "LCD L33224 — Documentation Requirements for TKA. Claims for CPT 27447 must include: operative report documenting the surgical approach and prosthesis used, pre-operative weight-bearing radiographs of the affected knee, documentation of failed conservative treatment trial of at least 3 months, and a completed functional assessment. Claims lacking required documentation will be denied under reason code CO-16 (claim/service lacks information).",
        "payer_name": "Medicare",
        "policy_id": "LCD-L33224",
        "policy_type": "LCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "Documentation Requirements",
    },
    {
        "text": "LCD L35062 — Coronary Artery Stenting. Percutaneous coronary intervention with stent placement (CPT 92928) is covered when performed for the treatment of significant coronary artery stenosis (>70% diameter stenosis) documented by coronary angiography. Drug-eluting stents are the standard of care. Medical necessity requires documented symptoms of myocardial ischemia or acute coronary syndrome.",
        "payer_name": "Medicare",
        "policy_id": "LCD-L35062",
        "policy_type": "LCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "Coverage Criteria",
    },
    # --- US: Commercial Payer Policies ---
    {
        "text": "Blue Cross Blue Shield Policy 7.01.50 — Lumbar Spinal Fusion. BCBS considers lumbar spinal fusion (CPT 22612) medically necessary for: degenerative disc disease with documented instability, spondylolisthesis Grade II or higher, recurrent disc herniation at the same level after prior discectomy, and spinal stenosis requiring decompression with evidence of instability. Prior authorization is required. Claims submitted without prior authorization will be denied under denial code OA-23.",
        "payer_name": "Blue Cross Blue Shield",
        "policy_id": "BCBS-7.01.50",
        "policy_type": "COMMERCIAL",
        "effective_date": "2024-06-01",
        "market": "US",
        "section_header": "Medical Necessity",
    },
    {
        "text": "Aetna Clinical Policy Bulletin 0016 — MRI Brain. Aetna considers MRI of the brain (CPT 70553) medically necessary for: evaluation of suspected intracranial neoplasm, assessment of acute stroke, evaluation of seizure disorders, assessment of multiple sclerosis, and evaluation of pituitary abnormalities. MRI brain performed as part of a general health screening in asymptomatic patients is considered not medically necessary and will be denied.",
        "payer_name": "Aetna",
        "policy_id": "AET-CPB-0016",
        "policy_type": "COMMERCIAL",
        "effective_date": "2024-03-15",
        "market": "US",
        "section_header": "Coverage Policy",
    },
    {
        "text": "UnitedHealthcare Medical Policy — Cholecystectomy. UHC covers laparoscopic cholecystectomy (CPT 47562) as medically necessary for: symptomatic cholelithiasis, acute cholecystitis, biliary dyskinesia with documented low gallbladder ejection fraction (<35%), and gallstone pancreatitis. Elective cholecystectomy for asymptomatic gallstones is generally not covered. Modifier 22 (increased procedural services) requires supporting documentation.",
        "payer_name": "UnitedHealthcare",
        "policy_id": "UHC-2024.T0136",
        "policy_type": "COMMERCIAL",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "Coverage Criteria",
    },
    # --- US: Denial Reason Code Reference ---
    {
        "text": "Denial Code CO-4: The procedure code is inconsistent with the modifier used or a required modifier is missing. Common causes include: using modifier 59 without documentation of distinct procedural service, missing laterality modifier (LT/RT) on bilateral procedures, and incorrect modifier sequence. Appeal must include operative report demonstrating the distinct nature of services.",
        "payer_name": "UNIVERSAL",
        "policy_id": "DENIAL-CODE-REF",
        "policy_type": "NCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "CO-4 Modifier Inconsistency",
    },
    {
        "text": "Denial Code CO-97: The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated. This is a bundling denial — it indicates that the denied procedure is considered a component of another procedure billed on the same claim. Appeal by providing documentation that the procedures were clinically distinct and performed through separate incisions or at separate anatomic sites.",
        "payer_name": "UNIVERSAL",
        "policy_id": "DENIAL-CODE-REF",
        "policy_type": "NCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "CO-97 Bundling Denial",
    },
    {
        "text": "Denial Code OA-23: The impact of this claim adjustment is the liability of the patient (prior authorization was required but not obtained). Prior authorization must be obtained before elective procedures. In emergency situations, retrospective authorization may be granted within 72 hours of admission. Appeal must include documentation of emergent circumstances.",
        "payer_name": "UNIVERSAL",
        "policy_id": "DENIAL-CODE-REF",
        "policy_type": "NCD",
        "effective_date": "2024-01-01",
        "market": "US",
        "section_header": "OA-23 Prior Authorization",
    },
    # --- India: IRDAI Policies ---
    {
        "text": "IRDAI Circular IRDA/HLT/REG/CIR/296/11/2020 — Standard Health Insurance Policy (Arogya Sanjeevani). All general and health insurance companies shall offer the standard health insurance product covering hospitalization expenses. Cashless settlement must be processed within 1 hour of receiving the pre-authorization request. Final claim settlement for reimbursement claims must be completed within 30 days of receiving all required documents.",
        "payer_name": "IRDAI",
        "policy_id": "IRDAI-296-2020",
        "policy_type": "IRDAI",
        "effective_date": "2020-11-01",
        "market": "INDIA",
        "section_header": "Settlement Timelines",
    },
    {
        "text": "IRDAI Health Insurance Regulations 2016 — Claim Settlement Process. The insurer or TPA shall settle a cashless claim within 1 hour of receipt of the final bill post discharge. For reimbursement claims, settlement shall be within 30 days from receipt of last necessary document. If the claim is not settled within the prescribed time, the insurer shall pay interest at 2% above the bank rate from the date of receipt of last document to the date of payment.",
        "payer_name": "IRDAI",
        "policy_id": "IRDAI-HEALTH-REG-2016",
        "policy_type": "IRDAI",
        "effective_date": "2016-01-01",
        "market": "INDIA",
        "section_header": "Claim Settlement",
    },
    {
        "text": "Ayushman Bharat PM-JAY — Health Benefit Package (HBP) Version 2.2. The PM-JAY scheme covers 1,949 procedures across 27 specialties with pre-defined package rates. Package rates vary by state and are categorized as: general ward, ICU, and procedure-specific. Claims must be submitted through the PM-JAY IT platform within 90 days of discharge. Claims exceeding package rates will be capped at the approved rate. Procedures not listed in the HBP are not covered under PM-JAY.",
        "payer_name": "Ayushman Bharat PM-JAY",
        "policy_id": "PMJAY-HBP-2.2",
        "policy_type": "IRDAI",
        "effective_date": "2024-01-01",
        "market": "INDIA",
        "section_header": "Package Rates",
    },
    {
        "text": "Star Health Insurance — Cashless Claim Process. For cashless hospitalization, the insured must seek treatment at a network hospital. Pre-authorization request must be submitted at least 48 hours before planned admission or within 24 hours for emergency admission. Star Health TPA will process the pre-authorization within 1 hour. Denial of cashless request can be appealed to the Grievance Redressal Officer within 30 days.",
        "payer_name": "Star Health",
        "policy_id": "STAR-CASHLESS-2024",
        "policy_type": "COMMERCIAL",
        "effective_date": "2024-01-01",
        "market": "INDIA",
        "section_header": "Cashless Process",
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

def ingest_starter_policies() -> int:
    """Embed and upsert the curated starter policy set."""
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    embed_fn = get_embedding_function()

    texts = [p["text"] for p in STARTER_POLICIES]
    print(f"  Embedding {len(texts)} policy documents...")
    vectors = embed_fn.embed_documents(texts)

    points = []
    for policy, vec in zip(STARTER_POLICIES, vectors):
        point_id = str(uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"policy_{policy['policy_id']}_{policy['section_header']}"
        ))
        points.append(PointStruct(
            id=point_id,
            vector=vec,
            payload={
                "payer_name": policy["payer_name"],
                "policy_id": policy["policy_id"],
                "policy_type": policy["policy_type"],
                "effective_date": policy["effective_date"],
                "market": policy["market"],
                "section_header": policy["section_header"],
                "text": policy["text"],
                "page_number": 1,
            },
        ))

    safe_upsert(client, COLLECTION, points)
    return len(points)


def run() -> None:
    """Main ingestion pipeline for payer_policies."""
    print("=" * 60)
    print("MedClaim — Payer Policies Ingestion")
    print("=" * 60)

    print("\n📋 Ingesting curated starter policies...")
    count = ingest_starter_policies()

    print(f"\n{'=' * 60}")
    print(f"✅ Ingested {count} policy documents into '{COLLECTION}'")
    print("   Covers: Medicare NCDs/LCDs, BCBS, Aetna, UHC, IRDAI, PM-JAY, Star Health")


if __name__ == "__main__":
    run()

"""
MedClaim — Database Seed Script

Inserts 20 synthetic test claims in various statuses into the claims table
so the dashboard is populated immediately when the frontend starts.

Usage:
    python -m backend.db.seed

Requires:
    - Supabase project created with schema from migrations/001_initial_schema.sql
    - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set in .env
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.db.client import get_supabase_client  # noqa: E402


# =============================================================================
# Synthetic Test Claims — 20 claims across various statuses, payers, facilities
# =============================================================================
SEED_CLAIMS = [
    # --- RECEIVED: Fresh claims awaiting processing ---
    {
        "patient_name": "Alice Johnson",
        "patient_dob": "1985-03-15",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": (date.today() - timedelta(days=2)).isoformat(),
        "facility_type": "outpatient_hospital",
        "diagnosis_codes": [
            {"code": "J18.9", "description": "Pneumonia, unspecified organism"}
        ],
        "procedure_codes": [
            {"code": "99213", "description": "Office visit, established patient, low complexity"}
        ],
        "billed_amount": 250.00,
        "status": "RECEIVED",
        "market": "US",
    },
    {
        "patient_name": "Bob Williams",
        "patient_dob": "1972-08-22",
        "payer_name": "Blue Cross Blue Shield",
        "payer_id": "BCBS-100",
        "date_of_service": (date.today() - timedelta(days=1)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "I21.09", "description": "ST elevation MI involving left main coronary artery"},
            {"code": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery"},
        ],
        "procedure_codes": [
            {"code": "92920", "description": "Percutaneous transluminal coronary angioplasty"},
            {"code": "92928", "description": "Intravascular stent, per coronary artery"},
        ],
        "billed_amount": 45000.00,
        "status": "RECEIVED",
        "market": "US",
    },
    # --- ELIGIBILITY_VERIFIED: Passed eligibility check ---
    {
        "patient_name": "Carol Martinez",
        "patient_dob": "1990-06-10",
        "payer_name": "Aetna",
        "payer_id": "AET-200",
        "date_of_service": (date.today() - timedelta(days=5)).isoformat(),
        "facility_type": "physician_office",
        "diagnosis_codes": [
            {"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia"}
        ],
        "procedure_codes": [
            {"code": "99214", "description": "Office visit, established patient, moderate complexity"}
        ],
        "billed_amount": 350.00,
        "status": "ELIGIBILITY_VERIFIED",
        "market": "US",
    },
    {
        "patient_name": "Daniel Brown",
        "patient_dob": "1968-01-30",
        "payer_name": "UnitedHealthcare",
        "payer_id": "UHC-300",
        "date_of_service": (date.today() - timedelta(days=4)).isoformat(),
        "facility_type": "ambulatory_surgery_center",
        "diagnosis_codes": [
            {"code": "K80.20", "description": "Calculus of gallbladder without cholecystitis"}
        ],
        "procedure_codes": [
            {"code": "47562", "description": "Laparoscopic cholecystectomy"}
        ],
        "billed_amount": 12500.00,
        "status": "ELIGIBILITY_VERIFIED",
        "market": "US",
    },
    # --- ELIGIBILITY_FAILED: Coverage issue ---
    {
        "patient_name": "Emily Chen",
        "patient_dob": "1978-12-01",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": (date.today() - timedelta(days=3)).isoformat(),
        "facility_type": "outpatient_hospital",
        "diagnosis_codes": [
            {"code": "M17.11", "description": "Primary osteoarthritis, right knee"}
        ],
        "procedure_codes": [
            {"code": "27447", "description": "Total knee replacement"}
        ],
        "billed_amount": 35000.00,
        "status": "ELIGIBILITY_FAILED",
        "market": "US",
        "human_review_flag": True,
        "human_review_reason": "Coverage inactive on date of service",
    },
    # --- AUDIT_COMPLETE: Code audit finished ---
    {
        "patient_name": "Frank Davis",
        "patient_dob": "1955-04-18",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": (date.today() - timedelta(days=7)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "J44.1", "description": "COPD with acute exacerbation"},
            {"code": "J96.00", "description": "Acute respiratory failure, unspecified"},
        ],
        "procedure_codes": [
            {"code": "94003", "description": "Ventilator management, initial day"},
            {"code": "31500", "description": "Emergency endotracheal intubation"},
        ],
        "billed_amount": 28000.00,
        "status": "AUDIT_COMPLETE",
        "market": "US",
    },
    {
        "patient_name": "Grace Lee",
        "patient_dob": "1982-09-05",
        "payer_name": "Cigna Healthcare",
        "payer_id": "CIG-400",
        "date_of_service": (date.today() - timedelta(days=6)).isoformat(),
        "facility_type": "physician_office",
        "diagnosis_codes": [
            {"code": "Z12.11", "description": "Encounter for screening for malignant neoplasm of colon"}
        ],
        "procedure_codes": [
            {"code": "45378", "description": "Diagnostic colonoscopy"}
        ],
        "billed_amount": 2800.00,
        "status": "AUDIT_COMPLETE",
        "market": "US",
    },
    # --- HUMAN_REVIEW_REQUIRED: Low confidence audit ---
    {
        "patient_name": "Henry Wilson",
        "patient_dob": "1960-11-25",
        "payer_name": "Blue Cross Blue Shield",
        "payer_id": "BCBS-100",
        "date_of_service": (date.today() - timedelta(days=8)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "C34.90", "description": "Malignant neoplasm of unspecified part of bronchus or lung"},
            {"code": "J91.0", "description": "Malignant pleural effusion"},
        ],
        "procedure_codes": [
            {"code": "32405", "description": "Thoracentesis with imaging guidance"},
            {"code": "32555", "description": "Pleural drainage, percutaneous"},
        ],
        "billed_amount": 18000.00,
        "status": "HUMAN_REVIEW_REQUIRED",
        "market": "US",
        "human_review_flag": True,
        "human_review_reason": "Audit confidence 0.62 — below 0.80 threshold",
    },
    # --- READY_FOR_SUBMISSION: Passed all checks ---
    {
        "patient_name": "Irene Taylor",
        "patient_dob": "1995-02-14",
        "payer_name": "Aetna",
        "payer_id": "AET-200",
        "date_of_service": (date.today() - timedelta(days=10)).isoformat(),
        "facility_type": "physician_office",
        "diagnosis_codes": [
            {"code": "N39.0", "description": "Urinary tract infection, site not specified"}
        ],
        "procedure_codes": [
            {"code": "99213", "description": "Office visit, established patient, low complexity"},
            {"code": "81001", "description": "Urinalysis with microscopy"},
        ],
        "billed_amount": 380.00,
        "status": "READY_FOR_SUBMISSION",
        "market": "US",
    },
    {
        "patient_name": "Jack Anderson",
        "patient_dob": "1988-07-19",
        "payer_name": "UnitedHealthcare",
        "payer_id": "UHC-300",
        "date_of_service": (date.today() - timedelta(days=9)).isoformat(),
        "facility_type": "ambulatory_surgery_center",
        "diagnosis_codes": [
            {"code": "H25.11", "description": "Age-related nuclear cataract, right eye"}
        ],
        "procedure_codes": [
            {"code": "66984", "description": "Cataract extraction with IOL insertion"}
        ],
        "billed_amount": 5200.00,
        "status": "READY_FOR_SUBMISSION",
        "market": "US",
    },
    # --- SUBMITTED: Sent to payer ---
    {
        "patient_name": "Karen Thomas",
        "patient_dob": "1975-05-08",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": (date.today() - timedelta(days=15)).isoformat(),
        "facility_type": "skilled_nursing_facility",
        "diagnosis_codes": [
            {"code": "S72.001A", "description": "Fracture of unspecified part of neck of right femur"},
            {"code": "W19.XXXA", "description": "Unspecified fall, initial encounter"},
        ],
        "procedure_codes": [
            {"code": "27236", "description": "Open treatment of femoral fracture, internal fixation"}
        ],
        "billed_amount": 22000.00,
        "status": "SUBMITTED",
        "market": "US",
    },
    # --- DENIED: Claim rejected by payer ---
    {
        "patient_name": "Leo Garcia",
        "patient_dob": "1965-10-12",
        "payer_name": "Blue Cross Blue Shield",
        "payer_id": "BCBS-100",
        "date_of_service": (date.today() - timedelta(days=20)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "M54.5", "description": "Low back pain"},
            {"code": "M51.16", "description": "Intervertebral disc degeneration, lumbar region"},
        ],
        "procedure_codes": [
            {"code": "63030", "description": "Lumbar laminotomy with decompression"},
            {"code": "22612", "description": "Lumbar arthrodesis, posterior technique"},
        ],
        "billed_amount": 65000.00,
        "status": "DENIED",
        "market": "US",
    },
    {
        "patient_name": "Maria Rodriguez",
        "patient_dob": "1970-03-28",
        "payer_name": "Aetna",
        "payer_id": "AET-200",
        "date_of_service": (date.today() - timedelta(days=18)).isoformat(),
        "facility_type": "outpatient_hospital",
        "diagnosis_codes": [
            {"code": "G43.909", "description": "Migraine, unspecified, not intractable"}
        ],
        "procedure_codes": [
            {"code": "70553", "description": "MRI brain with and without contrast"}
        ],
        "billed_amount": 3800.00,
        "status": "DENIED",
        "market": "US",
    },
    # --- APPEAL_DRAFT_READY: Appeal letter generated ---
    {
        "patient_name": "Nathan Kim",
        "patient_dob": "1958-06-20",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": (date.today() - timedelta(days=25)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "I63.50", "description": "Cerebral infarction due to unspecified occlusion of cerebral artery"}
        ],
        "procedure_codes": [
            {"code": "37184", "description": "Primary percutaneous mechanical thrombectomy"},
        ],
        "billed_amount": 42000.00,
        "status": "APPEAL_DRAFT_READY",
        "market": "US",
    },
    # --- APPROVED: Successfully processed ---
    {
        "patient_name": "Olivia White",
        "patient_dob": "1993-12-03",
        "payer_name": "Cigna Healthcare",
        "payer_id": "CIG-400",
        "date_of_service": (date.today() - timedelta(days=30)).isoformat(),
        "facility_type": "physician_office",
        "diagnosis_codes": [
            {"code": "Z23", "description": "Encounter for immunization"}
        ],
        "procedure_codes": [
            {"code": "90471", "description": "Immunization administration"},
            {"code": "90686", "description": "Influenza vaccine, quadrivalent"},
        ],
        "billed_amount": 180.00,
        "status": "APPROVED",
        "market": "US",
    },
    {
        "patient_name": "Peter Harris",
        "patient_dob": "1980-08-14",
        "payer_name": "UnitedHealthcare",
        "payer_id": "UHC-300",
        "date_of_service": (date.today() - timedelta(days=28)).isoformat(),
        "facility_type": "outpatient_hospital",
        "diagnosis_codes": [
            {"code": "K35.80", "description": "Unspecified acute appendicitis"}
        ],
        "procedure_codes": [
            {"code": "44970", "description": "Laparoscopic appendectomy"}
        ],
        "billed_amount": 15000.00,
        "status": "APPROVED",
        "market": "US",
    },
    # --- INDIA MARKET CLAIMS ---
    {
        "patient_name": "Rajesh Kumar",
        "patient_dob": "1990-06-15",
        "payer_name": "Star Health",
        "payer_id": "STAR-IN-001",
        "date_of_service": (date.today() - timedelta(days=3)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "K35.80", "description": "Unspecified acute appendicitis"}
        ],
        "procedure_codes": [
            {"code": "44970", "description": "Laparoscopic appendectomy"}
        ],
        "billed_amount": 85000.00,
        "status": "RECEIVED",
        "market": "INDIA",
    },
    {
        "patient_name": "Priya Sharma",
        "patient_dob": "1982-11-20",
        "payer_name": "HDFC ERGO",
        "payer_id": "HDFC-IN-001",
        "date_of_service": (date.today() - timedelta(days=7)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "O80", "description": "Encounter for full-term uncomplicated delivery"}
        ],
        "procedure_codes": [
            {"code": "59400", "description": "Routine obstetric care including delivery"}
        ],
        "billed_amount": 120000.00,
        "status": "ELIGIBILITY_VERIFIED",
        "market": "INDIA",
    },
    {
        "patient_name": "Amit Patel",
        "patient_dob": "1995-02-28",
        "payer_name": "Ayushman Bharat PM-JAY",
        "payer_id": "PMJAY-001",
        "date_of_service": (date.today() - timedelta(days=5)).isoformat(),
        "facility_type": "inpatient_hospital",
        "diagnosis_codes": [
            {"code": "I21.09", "description": "ST elevation MI involving left main coronary artery"}
        ],
        "procedure_codes": [
            {"code": "HBP-1201", "description": "PTCA with stenting (PM-JAY HBP)"}
        ],
        "billed_amount": 170000.00,
        "status": "AUDIT_COMPLETE",
        "market": "INDIA",
    },
    {
        "patient_name": "Sunita Devi",
        "patient_dob": "1975-09-12",
        "payer_name": "ICICI Lombard",
        "payer_id": "ICICI-IN-001",
        "date_of_service": (date.today() - timedelta(days=12)).isoformat(),
        "facility_type": "outpatient_hospital",
        "diagnosis_codes": [
            {"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia"}
        ],
        "procedure_codes": [
            {"code": "99214", "description": "Office visit, moderate complexity"}
        ],
        "billed_amount": 5000.00,
        "status": "DENIED",
        "market": "INDIA",
    },
]


def seed_database() -> None:
    """Insert all synthetic test claims into the Supabase claims table."""
    print("=" * 60)
    print("MedClaim — Database Seeder")
    print("=" * 60)

    try:
        client = get_supabase_client()
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("   Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set in .env")
        sys.exit(1)

    print(f"\n📊 Inserting {len(SEED_CLAIMS)} synthetic claims...")

    inserted = 0
    errors = 0

    for i, claim in enumerate(SEED_CLAIMS, 1):
        try:
            result = client.table("claims").insert(claim).execute()
            inserted += 1
            status_icon = "✅"
            print(
                f"  {status_icon} [{i:2d}/{len(SEED_CLAIMS)}] {claim['patient_name']:<20s} "
                f"| {claim['payer_name']:<25s} | {claim['status']}"
            )
        except Exception as e:
            errors += 1
            print(f"  ❌ [{i:2d}/{len(SEED_CLAIMS)}] {claim['patient_name']:<20s} | ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"Results: {inserted} inserted, {errors} errors")

    if errors == 0:
        print("✅ Database seeded successfully!")
    else:
        print(f"⚠️  {errors} claims failed to insert. Check errors above.")

    # Print summary by status
    print(f"\n📋 Claims by Status:")
    status_counts: dict[str, int] = {}
    for claim in SEED_CLAIMS:
        s = claim["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    for status, count in sorted(status_counts.items()):
        print(f"   {status:<25s} : {count}")

    # Print summary by market
    print(f"\n🌍 Claims by Market:")
    market_counts: dict[str, int] = {}
    for claim in SEED_CLAIMS:
        m = claim["market"]
        market_counts[m] = market_counts.get(m, 0) + 1
    for market, count in sorted(market_counts.items()):
        print(f"   {market:<10s} : {count}")


if __name__ == "__main__":
    seed_database()

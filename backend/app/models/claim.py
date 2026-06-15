"""
MedClaim — Claim Pydantic Models

Defines the ClaimSchema for API request validation, ClaimStatus enum
for lifecycle tracking, and parsing logic for both simplified JSON
and FHIR Claim resource formats.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from uuid import UUID


class ClaimStatus(StrEnum):
    """All valid claim lifecycle statuses."""

    RECEIVED = "RECEIVED"
    ELIGIBILITY_FAILED = "ELIGIBILITY_FAILED"
    ELIGIBILITY_VERIFIED = "ELIGIBILITY_VERIFIED"
    AUDIT_COMPLETE = "AUDIT_COMPLETE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    CORRECTION_PENDING = "CORRECTION_PENDING"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    DENIED = "DENIED"
    APPEAL_DRAFT_READY = "APPEAL_DRAFT_READY"
    APPEAL_PENDING_APPROVAL = "APPEAL_PENDING_APPROVAL"
    APPEAL_SUBMITTED = "APPEAL_SUBMITTED"
    APPROVED = "APPROVED"
    APPROVED_ON_APPEAL = "APPROVED_ON_APPEAL"
    FINAL_DENIED = "FINAL_DENIED"


class FacilityType(StrEnum):
    """Valid healthcare facility types."""

    INPATIENT_HOSPITAL = "inpatient_hospital"
    OUTPATIENT_HOSPITAL = "outpatient_hospital"
    PHYSICIAN_OFFICE = "physician_office"
    AMBULATORY_SURGERY_CENTER = "ambulatory_surgery_center"
    SKILLED_NURSING_FACILITY = "skilled_nursing_facility"


class Market(StrEnum):
    """Target market for the claim."""

    US = "US"
    INDIA = "INDIA"


class DiagnosisCode(BaseModel):
    """ICD-10-CM diagnosis code with description."""

    code: str = Field(..., min_length=3, max_length=10, examples=["J18.9"])
    description: str = Field("", max_length=500)


class ProcedureCode(BaseModel):
    """CPT/HCPCS procedure code with description."""

    code: str = Field(..., min_length=3, max_length=10, examples=["99213"])
    description: str = Field("", max_length=500)
    modifiers: list[str] = Field(default_factory=list)


# ── Request Models ───────────────────────────────────────────


class ClaimCreate(BaseModel):
    """Schema for creating a new claim via POST /claims."""

    patient_name: str = Field(..., min_length=1, max_length=200)
    patient_dob: date
    payer_name: str = Field(..., min_length=1, max_length=200)
    payer_id: str = Field(..., min_length=1, max_length=50)
    date_of_service: date
    facility_type: FacilityType
    diagnosis_codes: list[DiagnosisCode] = Field(..., min_length=1)
    procedure_codes: list[ProcedureCode] = Field(default_factory=list)
    billed_amount: float = Field(..., ge=0)
    market: Market = Market.US
    assigned_user_id: str | None = None

    @field_validator("date_of_service")
    @classmethod
    def dos_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of service cannot be in the future")
        return v

    @field_validator("diagnosis_codes")
    @classmethod
    def validate_diagnosis_codes(cls, v: list[DiagnosisCode]) -> list[DiagnosisCode]:
        codes = [dc.code for dc in v]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate diagnosis codes are not allowed")
        return v


class EOBCreate(BaseModel):
    """Schema for ingesting an Explanation of Benefits (denial)."""

    denial_reason_code: str = Field(..., min_length=1, max_length=20, examples=["CO-4"])
    denial_reason_description: str = Field("", max_length=1000)
    denied_procedure_codes: list[str] = Field(default_factory=list)
    payer_remarks: str = Field("", max_length=2000)


class ClaimApproval(BaseModel):
    """Schema for approving a corrected claim or appeal letter."""

    human_approved: bool = Field(..., description="Must be true to proceed")
    approved_by: str = Field(..., min_length=1)
    notes: str = Field("", max_length=1000)


# ── Response Models ──────────────────────────────────────────


class ClaimResponse(BaseModel):
    """Full claim data returned by the API."""

    id: UUID
    patient_name: str
    patient_dob: date
    payer_name: str
    payer_id: str
    date_of_service: date
    facility_type: str
    diagnosis_codes: list[dict[str, Any]]
    procedure_codes: list[dict[str, Any]]
    billed_amount: float
    status: ClaimStatus
    market: str
    assigned_user_id: str | None = None
    human_review_flag: bool = False
    human_review_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    audit_findings: list[dict[str, Any]] | None = None
    audit_confidence: float | None = None
    denial_risk_score: int | None = None
    risk_factors: list[dict[str, Any]] | None = None


class ClaimListResponse(BaseModel):
    """Paginated list of claims."""

    claims: list[ClaimResponse]
    total: int
    page: int
    page_size: int


# ── FHIR Parsing ─────────────────────────────────────────────


def parse_fhir_claim(fhir_resource: dict[str, Any]) -> ClaimCreate:
    """
    Parse a FHIR R4 Claim resource into a ClaimCreate schema.

    Handles the FHIR Claim resource structure:
    - patient → Patient reference
    - insurer → Payer reference
    - diagnosis[] → ICD-10 codes
    - procedure[] / item[] → CPT codes
    - total → billed amount

    Args:
        fhir_resource: FHIR Claim resource as a dict.

    Returns:
        ClaimCreate instance.

    Raises:
        ValueError: If required FHIR fields are missing.
    """
    resource_type = fhir_resource.get("resourceType", "")
    if resource_type != "Claim":
        raise ValueError(f"Expected resourceType 'Claim', got '{resource_type}'")

    # Extract patient name (from contained Patient or reference)
    patient_name = "Unknown Patient"
    patient_dob = date(1900, 1, 1)
    for contained in fhir_resource.get("contained", []):
        if contained.get("resourceType") == "Patient":
            names = contained.get("name", [{}])
            if names:
                given = " ".join(names[0].get("given", []))
                family = names[0].get("family", "")
                patient_name = f"{given} {family}".strip()
            if contained.get("birthDate"):
                patient_dob = date.fromisoformat(contained["birthDate"])
            break

    # Extract payer
    payer_name = "Unknown Payer"
    payer_id = "UNKNOWN"
    insurer = fhir_resource.get("insurer", {})
    if insurer.get("display"):
        payer_name = insurer["display"]
    if insurer.get("identifier", {}).get("value"):
        payer_id = insurer["identifier"]["value"]

    # Extract diagnosis codes
    diagnosis_codes = []
    for diag in fhir_resource.get("diagnosis", []):
        coding_list = diag.get("diagnosisCodeableConcept", {}).get("coding", [])
        for coding in coding_list:
            if coding.get("code"):
                diagnosis_codes.append(
                    DiagnosisCode(
                        code=coding["code"],
                        description=coding.get("display", ""),
                    )
                )

    if not diagnosis_codes:
        raise ValueError("FHIR Claim has no diagnosis codes")

    # Extract procedure codes from items
    procedure_codes = []
    for item in fhir_resource.get("item", []):
        coding_list = item.get("productOrService", {}).get("coding", [])
        for coding in coding_list:
            if coding.get("code"):
                modifiers = []
                for mod in item.get("modifier", []):
                    for mc in mod.get("coding", []):
                        if mc.get("code"):
                            modifiers.append(mc["code"])
                procedure_codes.append(
                    ProcedureCode(
                        code=coding["code"],
                        description=coding.get("display", ""),
                        modifiers=modifiers,
                    )
                )

    # Extract dates and amounts
    dos_str = fhir_resource.get("billablePeriod", {}).get("start", "")
    dos = date.fromisoformat(dos_str) if dos_str else date.today()

    total = fhir_resource.get("total", {}).get("value", 0)

    # Facility type (from FHIR type coding)
    facility_type = FacilityType.OUTPATIENT_HOSPITAL
    type_coding = fhir_resource.get("type", {}).get("coding", [])
    for tc in type_coding:
        code_val = tc.get("code", "").lower()
        if "inpatient" in code_val:
            facility_type = FacilityType.INPATIENT_HOSPITAL
        elif "office" in code_val or "professional" in code_val:
            facility_type = FacilityType.PHYSICIAN_OFFICE

    return ClaimCreate(
        patient_name=patient_name,
        patient_dob=patient_dob,
        payer_name=payer_name,
        payer_id=payer_id,
        date_of_service=dos,
        facility_type=facility_type,
        diagnosis_codes=diagnosis_codes,
        procedure_codes=procedure_codes,
        billed_amount=float(total),
    )

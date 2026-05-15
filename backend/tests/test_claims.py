"""MedClaim — Claim API Tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from backend.app.main import app

# A minimal valid JSON payload for creating a claim
VALID_CLAIM_JSON = {
    "patient_name": "Test Patient",
    "patient_dob": "1990-01-01",
    "payer_name": "Medicare",
    "payer_id": "MCR",
    "date_of_service": "2024-01-01",
    "facility_type": "physician_office",
    "diagnosis_codes": [{"code": "J18.9", "description": "Pneumonia"}],
    "procedure_codes": [{"code": "99213", "description": "Office visit"}],
    "billed_amount": 150.0,
    "market": "US",
}

# A minimal FHIR R4 Claim resource payload
VALID_FHIR_CLAIM = {
    "resourceType": "Claim",
    "id": "12345",
    "status": "active",
    "type": {
        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]
    },
    "patient": {"reference": "Patient/1"},
    "contained": [
        {
            "resourceType": "Patient",
            "id": "1",
            "name": [{"family": "Patient", "given": ["Test"]}],
            "birthDate": "1990-01-01"
        }
    ],
    "created": "2024-01-01T12:00:00Z",
    "insurer": {"identifier": {"value": "MCR"}, "display": "Medicare"},
    "diagnosis": [
        {
            "sequence": 1,
            "diagnosisCodeableConcept": {
                "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "J18.9"}]
            }
        }
    ],
    "item": [
        {
            "sequence": 1,
            "productOrService": {
                "coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "99213"}]
            }
        }
    ],
    "total": {"value": 150.0, "currency": "USD"}
}


def test_claim_validation_future_dos():
    """Test that claims with future dates of service are rejected."""
    invalid_claim = VALID_CLAIM_JSON.copy()
    invalid_claim["date_of_service"] = "2099-01-01"  # Future date

    with TestClient(app) as client:
        response = client.post("/claims", json=invalid_claim)
        assert response.status_code == 422
        assert "future" in response.text.lower()


def test_claim_validation_duplicate_diagnosis():
    """Test that claims with duplicate diagnosis codes are rejected."""
    invalid_claim = VALID_CLAIM_JSON.copy()
    invalid_claim["diagnosis_codes"] = [
        {"code": "J18.9", "description": "Pneumonia"},
        {"code": "J18.9", "description": "Pneumonia, again"},
    ]

    with TestClient(app) as client:
        response = client.post("/claims", json=invalid_claim)
        assert response.status_code == 422
        assert "duplicate" in response.text.lower()


def test_fhir_claim_parser_missing_diagnosis():
    """Test that FHIR claims missing required data fail validation cleanly."""
    invalid_fhir = VALID_FHIR_CLAIM.copy()
    invalid_fhir.pop("diagnosis")

    with TestClient(app) as client:
        response = client.post("/claims", json=invalid_fhir)
        assert response.status_code == 422
        assert "diagnosis" in response.text.lower()

"""
MedClaim — Shared Test Fixtures

Provides reusable pytest fixtures for the test suite including
the FastAPI test client, mock claim data, and test configuration overrides.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture()
def client() -> TestClient:
    """FastAPI test client for HTTP endpoint testing."""
    return TestClient(app)


@pytest.fixture()
def sample_claim_data() -> dict:
    """
    Minimal synthetic claim data for testing.
    Represents a simple outpatient visit with one diagnosis and one procedure.
    """
    return {
        "patient_name": "John Doe",
        "patient_dob": "1985-03-15",
        "payer_name": "Medicare",
        "payer_id": "MCR-001",
        "date_of_service": "2025-11-20",
        "facility_type": "outpatient_hospital",
        "diagnosis_codes": [
            {"code": "J18.9", "description": "Pneumonia, unspecified organism"}
        ],
        "procedure_codes": [
            {"code": "99213", "description": "Office visit, established patient, low complexity"}
        ],
        "billed_amount": 250.00,
    }


@pytest.fixture()
def sample_denied_claim_data(sample_claim_data: dict) -> dict:
    """Synthetic denied claim with EOB denial reason code."""
    return {
        **sample_claim_data,
        "status": "DENIED",
        "denial_reason_code": "CO-4",
        "denial_reason": "The procedure code is inconsistent with the modifier used.",
    }

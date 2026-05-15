"""
MedClaim — HAPI FHIR R4 Client

Wraps the HAPI FHIR REST API for creating and retrieving FHIR resources.
Used for EHR integration in dual-mode claim ingestion (direct JSON or FHIR).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.config import settings

logger = logging.getLogger("medclaim.services.fhir")


class FHIRClient:
    """
    Client for the HAPI FHIR R4 Server.

    Provides methods for CRUD operations on Patient, Encounter,
    Claim, and ExplanationOfBenefit FHIR resources.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.HAPI_FHIR_URL).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Content-Type": "application/fhir+json"},
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ── Health ────────────────────────────────────────────────

    async def check_connectivity(self) -> dict[str, Any]:
        """Check FHIR server connectivity via metadata endpoint."""
        try:
            r = await self._client.get("/metadata")
            r.raise_for_status()
            data = r.json()
            return {
                "status": "connected",
                "fhir_version": data.get("fhirVersion", "unknown"),
                "software": data.get("software", {}).get("name", "unknown"),
            }
        except Exception as e:
            logger.warning("fhir.connectivity_failed", error=str(e))
            return {"status": "disconnected", "error": str(e)}

    # ── Patient ───────────────────────────────────────────────

    async def create_patient(
        self, given_name: str, family_name: str, birth_date: str, gender: str = "unknown"
    ) -> dict[str, Any]:
        """Create a FHIR Patient resource."""
        resource = {
            "resourceType": "Patient",
            "name": [{"given": [given_name], "family": family_name}],
            "birthDate": birth_date,
            "gender": gender,
        }
        r = await self._client.post("/Patient", json=resource)
        r.raise_for_status()
        result = r.json()
        logger.info("fhir.patient_created", patient_id=result.get("id"))
        return result

    async def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        """Retrieve a Patient resource by ID."""
        r = await self._client.get(f"/Patient/{patient_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    # ── Encounter ─────────────────────────────────────────────

    async def create_encounter(
        self, patient_id: str, encounter_class: str = "AMB", status: str = "finished"
    ) -> dict[str, Any]:
        """Create a FHIR Encounter resource."""
        resource = {
            "resourceType": "Encounter",
            "status": status,
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": encounter_class,
            },
            "subject": {"reference": f"Patient/{patient_id}"},
        }
        r = await self._client.post("/Encounter", json=resource)
        r.raise_for_status()
        result = r.json()
        logger.info("fhir.encounter_created", encounter_id=result.get("id"))
        return result

    # ── Claim ─────────────────────────────────────────────────

    async def create_claim(self, claim_resource: dict[str, Any]) -> dict[str, Any]:
        """Create a FHIR Claim resource."""
        claim_resource["resourceType"] = "Claim"
        r = await self._client.post("/Claim", json=claim_resource)
        r.raise_for_status()
        result = r.json()
        logger.info("fhir.claim_created", claim_id=result.get("id"))
        return result

    async def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        """Retrieve a Claim resource by ID."""
        r = await self._client.get(f"/Claim/{claim_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    # ── ExplanationOfBenefit ──────────────────────────────────

    async def get_eob(self, eob_id: str) -> dict[str, Any] | None:
        """Retrieve an ExplanationOfBenefit resource by ID."""
        r = await self._client.get(f"/ExplanationOfBenefit/{eob_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

"""
MedClaim — Code Audit Agent

The most RAG-intensive agent. Audits ICD-10-CM and CPT/HCPCS codes
against the coding_rules Qdrant collection, AHA Coding Clinic guidelines,
and payer-specific LCDs. Produces structured AuditReport via Groq/Gemini.

Implementation: Subphase 2.3
"""

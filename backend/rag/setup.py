"""
MedClaim — Qdrant Collection Setup

Creates and configures the four Qdrant vector collections:
- coding_rules (768-dim, cosine, indexed on: code, code_type, payer_specificity)
- payer_policies (768-dim, cosine, indexed on: payer_name, policy_id, policy_type)
- denial_patterns (768-dim, cosine, indexed on: payer_name, outcome, facility_type)
- clinical_guidelines (768-dim, cosine, indexed on: guideline_source, evidence_level)

Vector size matches nomic-embed-text output (768 dimensions).
Distance metric: cosine similarity.

Implementation: Subphase 1.3
"""

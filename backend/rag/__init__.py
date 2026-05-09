"""
MedClaim — RAG Pipeline Package

Contains modules for Qdrant collection setup, embedding generation,
and per-collection retriever configurations for the four knowledge domains:
- coding_rules: ICD-10-CM / CPT codes + AHA guidelines
- payer_policies: CMS NCDs/LCDs + commercial/IRDAI policies
- denial_patterns: Historical claim-outcome pairs (feedback loop)
- clinical_guidelines: USPSTF / WHO clinical recommendations
"""

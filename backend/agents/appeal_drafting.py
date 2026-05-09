"""
MedClaim — Appeal Drafting Agent

Generates payer-specific appeal letters for denied claims.
Dual RAG retrieval: payer_policies (policy clause) + clinical_guidelines
(medical necessity evidence). Uses Gemini 1.5 Flash for long-context
policy documents. Output rendered via Jinja2 + WeasyPrint to PDF.

Implementation: Subphase 2.6
"""

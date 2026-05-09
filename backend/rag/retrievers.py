"""
MedClaim — RAG Retrievers

Configures LangChain Qdrant retrievers for each collection with
appropriate search parameters, metadata filters, and minimum
similarity thresholds (0.70 cosine for LOW_CONFIDENCE flagging).

Each agent calls the retriever relevant to its function:
- CodeAuditAgent → coding_rules retriever
- DenialPredictionAgent → denial_patterns retriever
- AppealDraftingAgent → payer_policies + clinical_guidelines retrievers

Implementation: Subphase 1.3 (config) / Phase 2 (integration)
"""

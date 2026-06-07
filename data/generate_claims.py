"""
MedClaim — Synthetic Claim Generator & Denial Patterns Seeder

Generates realistic medical claims using the Groq LLM and upserts them into
the `denial_patterns` Qdrant collection as historical claim-outcome pairs
for the Denial Prediction Agent's RAG pipeline.

Implementation: Missed Subphase 2.5
"""

import asyncio
import json
import logging
from typing import Any

from dotenv import load_dotenv
import structlog

# Load environment before local imports
load_dotenv()

from backend.agents.llm import query_llm
from backend.rag.setup import get_qdrant_client
from qdrant_client.models import PointStruct
from uuid import uuid4

logger = structlog.get_logger("medclaim.data.generator")

# The prompt instructions for synthetic generation
GENERATOR_PROMPT = """
Generate a batch of {batch_size} synthetic medical claims.
These claims should be realistic and cover a variety of facility types (inpatient_hospital, outpatient_hospital, physician_office), payers (Medicare, Aetna, Blue Cross, UnitedHealth), and markets ({market}).

Include a mix of:
1. Clean claims that were APPROVED.
2. Claims with coding errors (e.g., missing modifier, unbundled codes) that were DENIED.
3. Claims denied for eligibility reasons (e.g., not covered, out of network).
4. Claims denied for medical necessity.

Format your output STRICTLY as a JSON array of objects. Each object must have the following schema:
{
    "patient_name": "string",
    "payer_name": "string",
    "facility_type": "string",
    "market": "US or INDIA",
    "billed_amount": float,
    "diagnosis_codes": [{"code": "string", "description": "string"}],
    "procedure_codes": [{"code": "string", "description": "string", "modifiers": ["string"]}],
    "denial_reason_code": "string or null",
    "outcome": "APPROVED or DENIED or APPROVED_ON_APPEAL or FINAL_DENIED"
}
"""

async def generate_claim_batch(batch_size: int = 10, market: str = "US") -> list[dict[str, Any]]:
    """Generate a batch of synthetic claims using Groq."""
    prompt = GENERATOR_PROMPT.format(batch_size=batch_size, market=market)
    system_prompt = "You are a realistic medical claims data generator. Output strict JSON only, with a top-level key 'claims' containing the array."
    
    logger.info("generator.llm.start", batch_size=batch_size, market=market)
    res = await query_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        preferred_provider="groq",
        json_mode=True,
        temperature=0.7, # Higher temp for variance
        max_tokens=4000
    )
    
    data = res.get("json", {})
    claims = data.get("claims", [])
    logger.info("generator.llm.complete", generated_count=len(claims))
    return claims


async def seed_denial_patterns(total_claims: int = 50, batch_size: int = 10):
    """Generate claims and upsert them into the denial_patterns Qdrant collection."""
    logger.info("generator.seed.start", total_claims=total_claims)
    
    # We need embeddings for Qdrant. Since Ollama is local, we'll use Langchain's OllamaEmbeddings
    from langchain_community.embeddings import OllamaEmbeddings
    from backend.app.config import settings
    
    # We fallback to a dummy embedding if Ollama isn't running, but prompt says Ollama is used.
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    qdrant = get_qdrant_client()
    collection_name = "denial_patterns"
    
    generated_so_far = 0
    while generated_so_far < total_claims:
        current_batch_size = min(batch_size, total_claims - generated_so_far)
        claims = await generate_claim_batch(current_batch_size)
        
        if not claims:
            logger.error("generator.seed.failed_batch")
            continue
            
        points = []
        for claim in claims:
            # Create a textual representation for embedding
            dx_str = ", ".join([f"{d['code']} ({d.get('description', '')})" for d in claim.get("diagnosis_codes", [])])
            px_str = ", ".join([f"{p['code']} ({p.get('description', '')})" for p in claim.get("procedure_codes", [])])
            content = (
                f"Payer: {claim.get('payer_name')} | Facility: {claim.get('facility_type')} | "
                f"Diagnoses: {dx_str} | Procedures: {px_str} | "
                f"Outcome: {claim.get('outcome')} | Denial Reason: {claim.get('denial_reason_code')}"
            )
            
            # Generate embedding
            try:
                vector = embeddings.embed_query(content)
            except Exception as e:
                logger.warning("generator.embed.failed", error=str(e), action="Using zero vector for demo if ollama is down")
                vector = [0.0] * 768 # nomic-embed-text dimensionality
            
            points.append(PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "page_content": content,
                    "metadata": claim
                }
            ))
            
        if points:
            qdrant.upsert(
                collection_name=collection_name,
                points=points
            )
            generated_so_far += len(points)
            logger.info("generator.seed.upserted", count=len(points), total_so_far=generated_so_far)
            
    logger.info("generator.seed.complete", total_upserted=generated_so_far)

if __name__ == "__main__":
    # Run the seeder. Defaulting to 50 for demo speed, but can be scaled to 10000.
    asyncio.run(seed_denial_patterns(total_claims=50, batch_size=10))

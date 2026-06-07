"""
MedClaim — LangSmith Evaluation Suite

Creates a dataset of synthetic claims with expected outputs and runs a
CorrectnessEvaluator against the Code Audit Agent to detect prompt regressions.

Implementation: Missed Subphase 4.2
"""

import asyncio
import os
import logging
from typing import Any

from dotenv import load_dotenv
import structlog

from langsmith import Client
from langsmith.evaluation import evaluate

# Load environment before local imports
load_dotenv()

from backend.agents.code_audit import run_code_audit
from backend.agents.state import ClaimState

logger = structlog.get_logger("medclaim.llmops.evaluate")

# Sample synthetic evaluation dataset
EVAL_DATASET_NAME = "medclaim-code-audit-evals"

EVAL_EXAMPLES = [
    {
        "inputs": {
            "claim_id": "eval-001",
            "market": "US",
            "payer_name": "Medicare",
            "facility_type": "physician_office",
            "diagnosis_codes": [{"code": "J01.90", "description": "Acute sinusitis, unspecified"}],
            "procedure_codes": [{"code": "99214", "description": "Office or other outpatient visit"}],
            "billed_amount": 150.00
        },
        "outputs": {
            # Expected to find an UPCODING issue because sinusitis alone rarely justifies level 4 visit
            "expected_finding_type": "UPCODED"
        }
    },
    {
        "inputs": {
            "claim_id": "eval-002",
            "market": "US",
            "payer_name": "Blue Cross",
            "facility_type": "outpatient_hospital",
            "diagnosis_codes": [{"code": "M54.5", "description": "Low back pain"}],
            "procedure_codes": [
                {"code": "22551", "description": "Arthrodesis, anterior interbody"},
                {"code": "22845", "description": "Anterior instrumentation"}
            ],
            "billed_amount": 15000.00
        },
        "outputs": {
            # Standard bundle: instrumentation is typically included or requires specific context.
            "expected_finding_type": "CORRECT" # or unbundled depending on rules, we test stability.
        }
    }
]

def prepare_dataset(client: Client):
    """Create or update the LangSmith dataset."""
    if not client.has_dataset(dataset_name=EVAL_DATASET_NAME):
        dataset = client.create_dataset(
            dataset_name=EVAL_DATASET_NAME,
            description="Evaluation dataset for the Code Audit Agent prompt testing."
        )
        for example in EVAL_EXAMPLES:
            client.create_example(
                inputs=example["inputs"],
                outputs=example["outputs"],
                dataset_id=dataset.id,
            )
        logger.info("evaluate.dataset.created", name=EVAL_DATASET_NAME)
    else:
        logger.info("evaluate.dataset.exists", name=EVAL_DATASET_NAME)


def finding_type_evaluator(run: Any, example: Any) -> dict:
    """
    Evaluator that checks if the expected finding type is present in the LLM output.
    """
    expected_type = example.outputs.get("expected_finding_type")
    
    # run.outputs is the dictionary returned by run_code_audit
    actual_findings = run.outputs.get("audit_findings", [])
    
    # Extract just the finding_type or issue_type from the list of findings
    actual_types = [f.get("finding_type", f.get("issue_type", "")) for f in actual_findings]
    
    # Score 1.0 if the expected finding type is in the actual output, else 0.0
    if expected_type in actual_types or (expected_type == "CORRECT" and not actual_types):
        score = 1.0
    else:
        score = 0.0
        
    return {
        "key": "finding_type_match",
        "score": score,
        "comment": f"Expected: {expected_type}, Got: {actual_types}"
    }

async def target_function(inputs: dict) -> dict:
    """The function we are evaluating: the Code Audit Agent node."""
    # Convert inputs to ClaimState
    state = ClaimState(**inputs)
    # The run_code_audit returns a dict of updates to the state
    return await run_code_audit(state)

async def run_evaluation():
    """Run the LangSmith evaluation suite."""
    if not os.getenv("LANGSMITH_API_KEY"):
        logger.warning("evaluate.skip.no_api_key")
        return
        
    client = Client()
    prepare_dataset(client)
    
    logger.info("evaluate.run.start", dataset=EVAL_DATASET_NAME)
    
    # LangSmith evaluate() expects a sync or async function that takes inputs and returns outputs
    results = await evaluate(
        target_function,
        data=EVAL_DATASET_NAME,
        evaluators=[finding_type_evaluator],
        experiment_prefix="code-audit-eval",
        client=client
    )
    
    logger.info("evaluate.run.complete")
    return results

if __name__ == "__main__":
    asyncio.run(run_evaluation())

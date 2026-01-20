"""Replay engine for determinism verification.

Re-runs evaluations and compares hashes.
"""
from typing import List, Optional, Tuple

from app.schemas.evaluation import (
    EvaluationRequest,
    ReplayResult,
    canonicalize_json,
    compute_sha256,
)
from app.core.engine import run_evaluation
from app.audit.store import (
    load_evaluation_input,
    load_evaluation_output,
    load_evaluation_manifest,
    evaluation_exists,
)


def replay_evaluation(evaluation_id: str) -> Tuple[Optional[ReplayResult], Optional[str]]:
    """Replay an evaluation and verify determinism.
    
    Steps:
    1. Load saved input.json
    2. Re-run engine producing new output
    3. Recompute hashes
    4. Compare with saved output.json + manifest hashes
    5. If any mismatch -> FAIL CLOSED with explicit mismatch report
    
    Returns (ReplayResult, error_message) where error_message is set if evaluation not found.
    """
    if not evaluation_exists(evaluation_id):
        return None, f"Evaluation not found: {evaluation_id}"
    
    saved_input = load_evaluation_input(evaluation_id)
    if saved_input is None:
        return None, f"input.json not found for: {evaluation_id}"
    
    saved_output = load_evaluation_output(evaluation_id)
    if saved_output is None:
        return None, f"output.json not found for: {evaluation_id}"
    
    saved_manifest = load_evaluation_manifest(evaluation_id)
    if saved_manifest is None:
        return None, f"manifest.json not found for: {evaluation_id}"
    
    try:
        request = EvaluationRequest(**saved_input)
    except Exception as e:
        return ReplayResult(
            replay_ok=False,
            mismatches=[f"Failed to parse saved input: {e}"]
        ), None
    
    new_result, new_input_sha256 = run_evaluation(request)
    
    mismatches: List[str] = []
    
    if new_result.evaluation_id != evaluation_id:
        mismatches.append(
            f"evaluation_id mismatch: expected={evaluation_id}, got={new_result.evaluation_id}"
        )
    
    if new_result.input_sha256 != saved_output.get("input_sha256"):
        mismatches.append(
            f"input_sha256 mismatch: saved={saved_output.get('input_sha256')}, replayed={new_result.input_sha256}"
        )
    
    saved_output_sha256 = saved_output.get("output_sha256")
    if new_result.output_sha256 != saved_output_sha256:
        mismatches.append(
            f"output_sha256 mismatch: saved={saved_output_sha256}, replayed={new_result.output_sha256}"
        )
    
    if new_result.decision != saved_output.get("decision"):
        mismatches.append(
            f"decision mismatch: saved={saved_output.get('decision')}, replayed={new_result.decision}"
        )
    
    saved_manifest_sha256 = saved_manifest.get("manifest_sha256")
    
    if mismatches:
        return ReplayResult(replay_ok=False, mismatches=mismatches), None
    
    return ReplayResult(replay_ok=True, mismatches=[]), None

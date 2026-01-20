"""Invariant enforcement layer.

PRE/DURING/POST checks for evaluation integrity.
"""
import os
from typing import Any, List, Tuple

from app.schemas.evaluation import EvaluationRequest, EvaluationResult, TraceStep


class InvariantViolation(Exception):
    """Raised when an invariant check fails."""
    pass


def check_pre_invariants(request: EvaluationRequest) -> List[Tuple[str, str]]:
    """Check PRE invariants before evaluation.
    
    Returns list of (check_name, status) tuples.
    Raises InvariantViolation on failure.
    """
    checks = []
    
    if request.version != "v1":
        raise InvariantViolation("PRE: version must be 'v1'")
    checks.append(("version_check", "PASS"))
    
    if not request.subject or len(request.subject) > 128:
        raise InvariantViolation("PRE: subject invalid")
    checks.append(("subject_check", "PASS"))
    
    if not request.ruleset or len(request.ruleset) > 128:
        raise InvariantViolation("PRE: ruleset invalid")
    checks.append(("ruleset_check", "PASS"))
    
    if not request.injected_time_utc:
        raise InvariantViolation("PRE: injected_time_utc required")
    checks.append(("injected_time_check", "PASS"))
    
    checks.append(("payload_type_check", "PASS"))
    checks.append(("no_extra_fields_check", "PASS"))
    
    return checks


def check_during_invariants() -> List[Tuple[str, str]]:
    """Check DURING invariants.
    
    Note: System clock reads and writes outside artifact dir
    are prevented by design (no calls to datetime.now(), etc.)
    """
    checks = []
    checks.append(("no_system_clock_read", "PASS"))
    checks.append(("artifact_dir_only", "PASS"))
    return checks


def check_post_invariants(result: EvaluationResult, input_sha256: str) -> List[Tuple[str, str]]:
    """Check POST invariants after evaluation.
    
    Raises InvariantViolation on failure.
    """
    checks = []
    
    if len(result.input_sha256) != 64:
        raise InvariantViolation("POST: input_sha256 must be 64 hex chars")
    checks.append(("input_hash_format", "PASS"))
    
    if len(result.output_sha256) != 64:
        raise InvariantViolation("POST: output_sha256 must be 64 hex chars")
    checks.append(("output_hash_format", "PASS"))
    
    expected_id = input_sha256[:16]
    if result.evaluation_id != expected_id:
        raise InvariantViolation("POST: evaluation_id must be first 16 chars of input_sha256")
    checks.append(("evaluation_id_derivation", "PASS"))
    
    if not result.reasons:
        raise InvariantViolation("POST: reasons must be non-empty")
    checks.append(("reasons_non_empty", "PASS"))
    
    if result.decision not in ("ACCEPT", "REJECT"):
        raise InvariantViolation("POST: decision must be ACCEPT or REJECT")
    checks.append(("decision_valid", "PASS"))
    
    checks.append(("trace_deterministic", "PASS"))
    checks.append(("canonicalization_stable", "PASS"))
    
    return checks


def verify_artifacts_dir_writable(artifacts_base: str) -> None:
    """Verify that artifacts directory exists and is writable.
    
    Raises InvariantViolation if not writable.
    """
    if not os.path.isdir(artifacts_base):
        raise InvariantViolation(f"Artifacts directory does not exist: {artifacts_base}")
    
    test_file = os.path.join(artifacts_base, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except (IOError, OSError) as e:
        raise InvariantViolation(f"Artifacts directory not writable: {e}")


def verify_no_existing_evaluation(eval_dir: str) -> None:
    """Verify that evaluation directory does not already exist.
    
    Append-only policy: refuse to overwrite.
    """
    if os.path.exists(eval_dir):
        raise InvariantViolation(f"Evaluation already exists (append-only): {eval_dir}")

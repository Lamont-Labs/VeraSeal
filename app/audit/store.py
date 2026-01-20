"""Audit store for append-only filesystem artifacts.

Atomic writes with fsync. No overwrites allowed.
"""
import json
import os
import tempfile
import zipfile
from typing import Any, Dict, Optional, Tuple

from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResult,
    canonicalize_json,
    compute_sha256,
)
from app.invariants.checks import (
    verify_artifacts_dir_writable,
    verify_no_existing_evaluation,
    InvariantViolation,
)


ARTIFACTS_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts")
EVALUATIONS_DIR = os.path.join(ARTIFACTS_BASE, "evaluations")
MANIFESTS_DIR = os.path.join(ARTIFACTS_BASE, "manifests")


def _atomic_write(path: str, data: bytes) -> None:
    """Write data atomically: write to temp -> fsync -> rename."""
    dir_path = os.path.dirname(path)
    fd, temp_path = tempfile.mkstemp(dir=dir_path)
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.close(fd)
        os.rename(temp_path, path)
    except Exception:
        os.close(fd)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def _write_json_file(path: str, data: Any) -> Tuple[str, int]:
    """Write JSON file atomically. Returns (sha256, byte_size)."""
    canonical = canonicalize_json(data)
    sha256 = compute_sha256(canonical)
    _atomic_write(path, canonical)
    return sha256, len(canonical)


def store_evaluation(
    request: EvaluationRequest,
    result: EvaluationResult,
) -> EvaluationResult:
    """Store evaluation artifacts to filesystem.
    
    Creates:
    - artifacts/evaluations/<evaluation_id>/input.json
    - artifacts/evaluations/<evaluation_id>/output.json
    - artifacts/evaluations/<evaluation_id>/trace.json
    - artifacts/evaluations/<evaluation_id>/metadata.json
    - artifacts/manifests/<evaluation_id>.manifest.json
    
    Returns updated EvaluationResult with manifest_sha256.
    """
    verify_artifacts_dir_writable(ARTIFACTS_BASE)
    
    eval_dir = os.path.join(EVALUATIONS_DIR, result.evaluation_id)
    verify_no_existing_evaluation(eval_dir)
    
    os.makedirs(eval_dir, exist_ok=False)
    
    input_path = os.path.join(eval_dir, "input.json")
    input_sha256, input_size = _write_json_file(input_path, request.model_dump())
    
    trace_data = [step.model_dump() for step in result.trace]
    trace_path = os.path.join(eval_dir, "trace.json")
    trace_sha256, trace_size = _write_json_file(trace_path, trace_data)
    
    output_data = {
        "evaluation_id": result.evaluation_id,
        "input_sha256": result.input_sha256,
        "output_sha256": result.output_sha256,
        "decision": result.decision,
        "reasons": result.reasons,
        "created_time_utc": result.created_time_utc,
    }
    output_path = os.path.join(eval_dir, "output.json")
    output_sha256, output_size = _write_json_file(output_path, output_data)
    
    manifest_data = {
        "evaluation_id": result.evaluation_id,
        "files": [
            {"path": "input.json", "sha256": input_sha256, "size": input_size},
            {"path": "output.json", "sha256": output_sha256, "size": output_size},
            {"path": "trace.json", "sha256": trace_sha256, "size": trace_size},
        ],
    }
    manifest_canonical = canonicalize_json(manifest_data)
    manifest_sha256 = compute_sha256(manifest_canonical)
    
    metadata = {
        "evaluation_id": result.evaluation_id,
        "injected_time_utc": request.injected_time_utc,
        "subject": request.subject,
        "ruleset": request.ruleset,
        "input_sha256": result.input_sha256,
        "output_sha256": result.output_sha256,
        "trace_sha256": trace_sha256,
        "manifest_sha256": manifest_sha256,
    }
    metadata_path = os.path.join(eval_dir, "metadata.json")
    _write_json_file(metadata_path, metadata)
    
    manifest_path = os.path.join(MANIFESTS_DIR, f"{result.evaluation_id}.manifest.json")
    manifest_data["manifest_sha256"] = manifest_sha256
    _write_json_file(manifest_path, manifest_data)
    
    final_result = EvaluationResult(
        evaluation_id=result.evaluation_id,
        input_sha256=result.input_sha256,
        output_sha256=result.output_sha256,
        manifest_sha256=manifest_sha256,
        decision=result.decision,
        reasons=result.reasons,
        trace=result.trace,
        created_time_utc=result.created_time_utc,
    )
    
    return final_result


def load_evaluation_input(evaluation_id: str) -> Optional[Dict[str, Any]]:
    """Load input.json for an evaluation."""
    path = os.path.join(EVALUATIONS_DIR, evaluation_id, "input.json")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def load_evaluation_output(evaluation_id: str) -> Optional[Dict[str, Any]]:
    """Load output.json for an evaluation."""
    path = os.path.join(EVALUATIONS_DIR, evaluation_id, "output.json")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def load_evaluation_trace(evaluation_id: str) -> Optional[list]:
    """Load trace.json for an evaluation."""
    path = os.path.join(EVALUATIONS_DIR, evaluation_id, "trace.json")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def load_evaluation_metadata(evaluation_id: str) -> Optional[Dict[str, Any]]:
    """Load metadata.json for an evaluation."""
    path = os.path.join(EVALUATIONS_DIR, evaluation_id, "metadata.json")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def load_evaluation_manifest(evaluation_id: str) -> Optional[Dict[str, Any]]:
    """Load manifest.json for an evaluation."""
    path = os.path.join(MANIFESTS_DIR, f"{evaluation_id}.manifest.json")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def evaluation_exists(evaluation_id: str) -> bool:
    """Check if an evaluation exists."""
    eval_dir = os.path.join(EVALUATIONS_DIR, evaluation_id)
    return os.path.isdir(eval_dir)


def create_evaluation_bundle(evaluation_id: str, injected_time_utc: str) -> Optional[bytes]:
    """Create a deterministic ZIP bundle of evaluation artifacts.
    
    Note: ZIP timestamps are normalized to a fixed value based on injected_time_utc
    for determinism. If this proves problematic, raw file downloads are available.
    """
    eval_dir = os.path.join(EVALUATIONS_DIR, evaluation_id)
    if not os.path.isdir(eval_dir):
        return None
    
    import io
    buffer = io.BytesIO()
    
    fixed_time = (2000, 1, 1, 0, 0, 0)
    
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        files = sorted(os.listdir(eval_dir))
        for filename in files:
            filepath = os.path.join(eval_dir, filename)
            if os.path.isfile(filepath):
                with open(filepath, "rb") as f:
                    data = f.read()
                info = zipfile.ZipInfo(f"{evaluation_id}/{filename}", date_time=fixed_time)
                zf.writestr(info, data)
        
        manifest_path = os.path.join(MANIFESTS_DIR, f"{evaluation_id}.manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "rb") as f:
                data = f.read()
            info = zipfile.ZipInfo(f"{evaluation_id}/manifest.json", date_time=fixed_time)
            zf.writestr(info, data)
    
    return buffer.getvalue()

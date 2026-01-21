"""Deterministic evaluation engine.

Pure functions only. No randomness. No system clock reads.
"""
from typing import Any, Dict, List, Tuple

from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResult,
    TraceStep,
    canonicalize_json,
    compute_sha256,
)
from app.invariants.checks import (
    check_pre_invariants,
    check_during_invariants,
    check_post_invariants,
)
from app.policy import (
    load_policy,
    get_default_policy_id,
    evaluate_with_policy,
)


def run_evaluation(
    request: EvaluationRequest,
    policy_id: str | None = None
) -> Tuple[EvaluationResult, str]:
    """Run deterministic evaluation on request.
    
    Returns (EvaluationResult, input_sha256).
    
    This is a pure function:
    - No randomness
    - No system clock reads
    - Deterministic output for identical input
    
    Args:
        request: The evaluation request
        policy_id: Optional policy ID override (for replay compatibility)
    """
    trace_steps: List[TraceStep] = []
    
    if policy_id is None:
        policy_id = get_default_policy_id()
    
    policy = load_policy(policy_id)
    
    trace_steps.append(TraceStep(
        step_name="load_policy",
        status="PASS",
        details=f"Loaded policy: {policy_id}"
    ))
    
    pre_checks = check_pre_invariants(request)
    for check_name, status in pre_checks:
        trace_steps.append(TraceStep(
            step_name=f"pre_{check_name}",
            status=status,
            details=f"PRE invariant check: {check_name}"
        ))
    
    input_dict = request.model_dump()
    input_canonical = canonicalize_json(input_dict)
    input_sha256 = compute_sha256(input_canonical)
    
    trace_steps.append(TraceStep(
        step_name="canonicalize_input",
        status="PASS",
        details=f"Input canonicalized, sha256={input_sha256}"
    ))
    
    evaluation_id = input_sha256[:16]
    
    trace_steps.append(TraceStep(
        step_name="derive_evaluation_id",
        status="PASS",
        details=f"evaluation_id={evaluation_id}"
    ))
    
    during_checks = check_during_invariants()
    for check_name, status in during_checks:
        trace_steps.append(TraceStep(
            step_name=f"during_{check_name}",
            status=status,
            details=f"DURING invariant check: {check_name}"
        ))
    
    decision, reasons, rule_trace = evaluate_with_policy(policy, request.payload)
    
    for rt in rule_trace:
        trace_steps.append(TraceStep(
            step_name=f"rule_{rt['rule_id']}_{rt['rule_name']}",
            status=rt["status"],
            details=rt["detail"]
        ))
    
    trace_steps.append(TraceStep(
        step_name="policy_evaluation_complete",
        status="PASS",
        details=f"Policy {policy_id} applied: decision={decision}, reasons_count={len(reasons)}"
    ))
    
    output_for_hash = {
        "evaluation_id": evaluation_id,
        "input_sha256": input_sha256,
        "policy_id": policy_id,
        "decision": decision,
        "reasons": reasons,
        "trace": [s.model_dump() for s in trace_steps],
        "created_time_utc": request.injected_time_utc,
    }
    output_canonical = canonicalize_json(output_for_hash)
    output_sha256 = compute_sha256(output_canonical)
    
    trace_steps.append(TraceStep(
        step_name="compute_output_hash",
        status="PASS",
        details=f"output_sha256={output_sha256}"
    ))
    
    result = EvaluationResult(
        evaluation_id=evaluation_id,
        input_sha256=input_sha256,
        output_sha256=output_sha256,
        manifest_sha256="",
        policy_id=policy_id,
        decision=decision,
        reasons=reasons,
        trace=trace_steps,
        created_time_utc=request.injected_time_utc,
    )
    
    post_checks = check_post_invariants(result, input_sha256)
    for check_name, status in post_checks:
        trace_steps.append(TraceStep(
            step_name=f"post_{check_name}",
            status=status,
            details=f"POST invariant check: {check_name}"
        ))
    
    final_result = EvaluationResult(
        evaluation_id=evaluation_id,
        input_sha256=input_sha256,
        output_sha256=output_sha256,
        manifest_sha256="",
        policy_id=policy_id,
        decision=decision,
        reasons=reasons,
        trace=trace_steps,
        created_time_utc=request.injected_time_utc,
    )
    
    return final_result, input_sha256


def run_pure_evaluation(request: EvaluationRequest) -> Tuple[str, str, str]:
    """Run pure evaluation without side effects.
    
    Returns (evaluation_id, input_sha256, output_sha256) for testing determinism.
    """
    result, input_sha256 = run_evaluation(request)
    return result.evaluation_id, input_sha256, result.output_sha256

"""Policy module for deterministic evaluation rules."""
import json
import os
from typing import Any, Dict, List, Tuple

POLICY_DIR = os.path.dirname(__file__)

_LEGACY_POLICY_ID = "mvp-placeholder-v0"


def load_policy(policy_id: str) -> Dict[str, Any]:
    """Load a policy by ID.
    
    Returns policy dict or raises FileNotFoundError.
    """
    if policy_id == _LEGACY_POLICY_ID:
        return {
            "policy_id": _LEGACY_POLICY_ID,
            "policy_version": "0.0.0",
            "description": "Legacy MVP placeholder rule (assert == true)",
            "legacy": True
        }
    
    policy_file = os.path.join(POLICY_DIR, f"{policy_id.replace('-', '_')}.json")
    if not os.path.exists(policy_file):
        policy_file = os.path.join(POLICY_DIR, "evaluation_policy_v1.json")
    
    with open(policy_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_default_policy_id() -> str:
    """Return the default policy ID for new evaluations."""
    return "evaluation-policy-v1"


def evaluate_with_policy(
    policy: Dict[str, Any],
    payload: Dict[str, Any]
) -> Tuple[str, List[str], List[Dict[str, str]]]:
    """Evaluate payload against policy rules.
    
    Returns (decision, reasons, rule_trace).
    
    Deterministic: same policy + payload = same output.
    Fail-closed: any rule failure results in REJECT.
    """
    if policy.get("legacy"):
        return _evaluate_legacy_rule(payload)
    
    reasons: List[str] = []
    rule_trace: List[Dict[str, str]] = []
    
    decision_requested = payload.get("decision_requested")
    if decision_requested is None:
        reasons.append("R001:MISSING_DECISION_REQUESTED: Required field 'decision_requested' is missing from payload")
        rule_trace.append({
            "rule_id": "R001",
            "rule_name": "check_decision_requested_present",
            "status": "FAIL",
            "detail": "payload.decision_requested not found"
        })
        return "REJECT", reasons, rule_trace
    
    rule_trace.append({
        "rule_id": "R001",
        "rule_name": "check_decision_requested_present",
        "status": "PASS",
        "detail": f"payload.decision_requested = {decision_requested}"
    })
    
    if decision_requested not in ("ACCEPT", "REJECT"):
        reasons.append(f"R002:INVALID_DECISION_REQUESTED: Field 'decision_requested' must be exactly 'ACCEPT' or 'REJECT', got '{decision_requested}'")
        rule_trace.append({
            "rule_id": "R002",
            "rule_name": "check_decision_requested_valid",
            "status": "FAIL",
            "detail": f"decision_requested = '{decision_requested}' is not valid"
        })
        return "REJECT", reasons, rule_trace
    
    rule_trace.append({
        "rule_id": "R002",
        "rule_name": "check_decision_requested_valid",
        "status": "PASS",
        "detail": f"decision_requested = '{decision_requested}' is valid"
    })
    
    justification = payload.get("justification")
    if justification is None:
        reasons.append("R003:MISSING_JUSTIFICATION: Required field 'justification' is missing from payload")
        rule_trace.append({
            "rule_id": "R003",
            "rule_name": "check_justification_present",
            "status": "FAIL",
            "detail": "payload.justification not found"
        })
        return "REJECT", reasons, rule_trace
    
    rule_trace.append({
        "rule_id": "R003",
        "rule_name": "check_justification_present",
        "status": "PASS",
        "detail": "payload.justification found"
    })
    
    if not isinstance(justification, str) or len(justification.strip()) == 0:
        reasons.append("R004:EMPTY_JUSTIFICATION: Field 'justification' must be a non-empty string")
        rule_trace.append({
            "rule_id": "R004",
            "rule_name": "check_justification_non_empty",
            "status": "FAIL",
            "detail": f"justification is empty or not a string"
        })
        return "REJECT", reasons, rule_trace
    
    rule_trace.append({
        "rule_id": "R004",
        "rule_name": "check_justification_non_empty",
        "status": "PASS",
        "detail": f"justification has {len(justification)} chars"
    })
    
    reasons.append(f"R005:DECISION_RECORDED: Decision '{decision_requested}' recorded with justification")
    rule_trace.append({
        "rule_id": "R005",
        "rule_name": "apply_decision",
        "status": "PASS",
        "detail": f"Recording decision={decision_requested}"
    })
    
    return decision_requested, reasons, rule_trace


def _evaluate_legacy_rule(payload: Dict[str, Any]) -> Tuple[str, List[str], List[Dict[str, str]]]:
    """Legacy MVP rule for replay compatibility.
    
    Rule: IF payload.assert == true -> ACCEPT else REJECT
    """
    rule_trace: List[Dict[str, str]] = []
    
    if payload.get("assert") is True:
        rule_trace.append({
            "rule_id": "LEGACY",
            "rule_name": "mvp_assert_check",
            "status": "PASS",
            "detail": "payload.assert == true"
        })
        return "ACCEPT", ["Legacy MVP rule: payload.assert == true"], rule_trace
    else:
        if "assert" not in payload:
            reason = "Legacy MVP rule: payload.assert key not present"
            detail = "assert key missing"
        else:
            reason = f"Legacy MVP rule: payload.assert == {payload.get('assert')} (not true)"
            detail = f"assert = {payload.get('assert')}"
        
        rule_trace.append({
            "rule_id": "LEGACY",
            "rule_name": "mvp_assert_check",
            "status": "FAIL",
            "detail": detail
        })
        return "REJECT", [reason], rule_trace

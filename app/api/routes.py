"""FastAPI routes for the evaluation API."""
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import os
import json
import subprocess

from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResult,
    ReplayResult,
    HealthResponse,
)
from app.core.engine import run_evaluation
from app.audit.store import (
    store_evaluation,
    load_evaluation_input,
    load_evaluation_output,
    load_evaluation_trace,
    load_evaluation_metadata,
    load_evaluation_manifest,
    evaluation_exists,
    create_evaluation_bundle,
)
from app.replay.replay import replay_evaluation
from app.invariants.checks import InvariantViolation


VERSION = "1.0.0"

def _get_git_commit() -> str:
    """Get current git commit hash (short form)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _format_validation_error(e: ValidationError) -> dict:
    """Format Pydantic validation error for user-friendly display."""
    errors = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        err_type = err.get("type", "")
        
        field_error = {
            "field": loc,
            "message": msg,
            "type": err_type,
        }
        
        if err_type == "missing":
            field_error["fix"] = f"Add the required field '{loc}' to your request"
        elif err_type == "extra_forbidden":
            field_error["fix"] = f"Remove the unexpected field '{loc}' from your request"
        elif "string" in err_type:
            field_error["fix"] = f"Ensure '{loc}' is a string value"
        elif "bool" in err_type:
            field_error["fix"] = f"Ensure '{loc}' is true or false (not quoted)"
        
        errors.append(field_error)
    
    return {
        "error": "Validation failed",
        "details": errors,
        "hint": "Check the /schema endpoint for the expected request format"
    }


router = APIRouter()

templates_path = os.path.join(os.path.dirname(__file__), "..", "web", "templates")
templates = Jinja2Templates(directory=templates_path)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the index page with evaluation submission form."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/evaluate")
async def evaluate(request: Request):
    """Process an evaluation request.
    
    Accepts JSON body with EvaluationRequest schema.
    Returns evaluation_id and result.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid JSON",
                "message": str(e),
                "fix": "Ensure your request body is valid JSON"
            }
        )
    
    try:
        eval_request = EvaluationRequest(**body)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=_format_validation_error(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    try:
        result, input_sha256 = run_evaluation(eval_request)
    except InvariantViolation as e:
        raise HTTPException(status_code=400, detail=f"Invariant violation: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")
    
    try:
        final_result = store_evaluation(eval_request, result)
    except InvariantViolation as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Duplicate evaluation",
                "message": "This exact evaluation already exists (append-only policy)",
                "evaluation_id": result.evaluation_id,
                "fix": "Each unique input can only be evaluated once. View the existing record instead."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage failed: {e}")
    
    return JSONResponse(content={
        "evaluation_id": final_result.evaluation_id,
        "result": final_result.model_dump(),
    })


@router.get("/evaluations/{evaluation_id}", response_class=HTMLResponse)
async def get_evaluation_page(request: Request, evaluation_id: str):
    """Render the evaluation detail page."""
    if not evaluation_exists(evaluation_id):
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Evaluation not found: {evaluation_id}"},
            status_code=404,
        )
    
    output = load_evaluation_output(evaluation_id)
    metadata = load_evaluation_metadata(evaluation_id)
    manifest = load_evaluation_manifest(evaluation_id)
    
    return templates.TemplateResponse("evaluation.html", {
        "request": request,
        "evaluation_id": evaluation_id,
        "output": output,
        "metadata": metadata,
        "manifest": manifest,
    })


@router.get("/evaluations/{evaluation_id}/input")
async def get_evaluation_input(evaluation_id: str):
    """Return raw input.json for an evaluation."""
    data = load_evaluation_input(evaluation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return JSONResponse(content=data)


@router.get("/evaluations/{evaluation_id}/output")
async def get_evaluation_output(evaluation_id: str):
    """Return raw output.json for an evaluation."""
    data = load_evaluation_output(evaluation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return JSONResponse(content=data)


@router.get("/evaluations/{evaluation_id}/trace")
async def get_evaluation_trace(evaluation_id: str):
    """Return raw trace.json for an evaluation."""
    data = load_evaluation_trace(evaluation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return JSONResponse(content=data)


@router.get("/evaluations/{evaluation_id}/meta")
async def get_evaluation_metadata(evaluation_id: str):
    """Return raw metadata.json for an evaluation."""
    data = load_evaluation_metadata(evaluation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return JSONResponse(content=data)


@router.get("/evaluations/{evaluation_id}/manifest")
async def get_evaluation_manifest(evaluation_id: str):
    """Return raw manifest.json for an evaluation."""
    data = load_evaluation_manifest(evaluation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return JSONResponse(content=data)


@router.get("/evaluations/{evaluation_id}/bundle")
async def get_evaluation_bundle(evaluation_id: str):
    """Return a ZIP bundle of all evaluation artifacts."""
    metadata = load_evaluation_metadata(evaluation_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    injected_time = metadata.get("injected_time_utc", "2000-01-01T00:00:00Z")
    bundle = create_evaluation_bundle(evaluation_id, injected_time)
    
    if bundle is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    return Response(
        content=bundle,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={evaluation_id}.zip"},
    )


@router.post("/replay/{evaluation_id}")
async def replay(evaluation_id: str):
    """Replay an evaluation and verify determinism."""
    result, error = replay_evaluation(evaluation_id)
    
    if error:
        raise HTTPException(status_code=404, detail=error)
    
    if result is None:
        raise HTTPException(status_code=500, detail="Replay failed unexpectedly")
    
    return JSONResponse(content=result.model_dump())


@router.get("/replay/{evaluation_id}", response_class=HTMLResponse)
async def get_replay_page(request: Request, evaluation_id: str):
    """Render the replay result page."""
    result, error = replay_evaluation(evaluation_id)
    
    if error:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": error},
            status_code=404,
        )
    
    if result is None:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Replay failed unexpectedly"},
            status_code=500,
        )
    
    return templates.TemplateResponse("replay.html", {
        "request": request,
        "evaluation_id": evaluation_id,
        "result": result.model_dump(),
    })


@router.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse(content=HealthResponse(
        status="ok",
        strict_mode=True,
    ).model_dump())


@router.get("/version")
async def version():
    """Version endpoint with commit hash."""
    return JSONResponse(content={
        "version": VERSION,
        "commit": _get_git_commit(),
        "name": "VeraSeal",
        "description": "Deterministic evaluation with cryptographic provenance"
    })


@router.get("/schema")
async def schema():
    """Return the authoritative JSON schema for evaluation requests."""
    schema_data = {
        "request": {
            "type": "object",
            "required": ["version", "subject", "ruleset", "payload", "injected_time_utc"],
            "additionalProperties": False,
            "properties": {
                "version": {
                    "type": "string",
                    "const": "v1",
                    "description": "Schema version, must be 'v1'"
                },
                "subject": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "What is being decided (e.g., vendor-approval, access-request)"
                },
                "ruleset": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "Which rules/policy are being applied"
                },
                "payload": {
                    "type": "object",
                    "description": "Decision data. Must contain 'assert': true for ACCEPT, any other value for REJECT"
                },
                "injected_time_utc": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$",
                    "description": "RFC3339/ISO8601 timestamp in UTC (e.g., 2024-01-15T10:30:00Z)"
                }
            }
        },
        "response": {
            "type": "object",
            "properties": {
                "evaluation_id": {"type": "string", "description": "Unique ID derived from input hash"},
                "result": {
                    "type": "object",
                    "properties": {
                        "evaluation_id": {"type": "string"},
                        "input_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                        "output_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                        "manifest_sha256": {"type": "string"},
                        "decision": {"type": "string", "enum": ["ACCEPT", "REJECT"]},
                        "reasons": {"type": "array", "items": {"type": "string"}},
                        "trace": {"type": "array"},
                        "created_time_utc": {"type": "string"}
                    }
                }
            }
        },
        "mvp_rule": "IF payload.assert === true THEN ACCEPT ELSE REJECT"
    }
    return JSONResponse(content=schema_data)


@router.get("/examples")
async def examples():
    """Return canonical example payloads for common use cases."""
    example_data = {
        "vendor_approval": {
            "description": "Approve a new vendor for onboarding",
            "request": {
                "version": "v1",
                "subject": "vendor-approval",
                "ruleset": "vendor-onboarding-policy",
                "payload": {
                    "assert": True,
                    "vendor_name": "Acme Corp",
                    "country": "US",
                    "requires_nda": True
                },
                "injected_time_utc": "2024-01-15T10:30:00Z"
            },
            "expected_decision": "ACCEPT"
        },
        "policy_exception": {
            "description": "Request exception to standard policy",
            "request": {
                "version": "v1",
                "subject": "policy-exception",
                "ruleset": "exception-review",
                "payload": {
                    "assert": True,
                    "policy_id": "SEC-001",
                    "exception_reason": "Legacy system integration",
                    "duration_days": 90
                },
                "injected_time_utc": "2024-01-15T14:00:00Z"
            },
            "expected_decision": "ACCEPT"
        },
        "risk_rejection": {
            "description": "Reject a high-risk proposal",
            "request": {
                "version": "v1",
                "subject": "risk-acceptance",
                "ruleset": "risk-assessment",
                "payload": {
                    "assert": False,
                    "risk_id": "RISK-2024-001",
                    "risk_level": "high",
                    "reason": "Insufficient mitigation controls"
                },
                "injected_time_utc": "2024-01-15T16:00:00Z"
            },
            "expected_decision": "REJECT"
        },
        "access_approval": {
            "description": "Approve access request",
            "request": {
                "version": "v1",
                "subject": "access-approval",
                "ruleset": "access-control",
                "payload": {
                    "assert": True,
                    "resource": "production-database",
                    "access_level": "read-only",
                    "requestor": "user@example.com"
                },
                "injected_time_utc": "2024-01-15T09:00:00Z"
            },
            "expected_decision": "ACCEPT"
        }
    }
    return JSONResponse(content=example_data)


@router.get("/system-check", response_class=HTMLResponse)
async def system_check(request: Request):
    """Render the system self-test page.
    
    Runs deterministic internal checks with no side effects:
    - Schema validity
    - Hash determinism
    - Replay integrity (logic only, no disk I/O)
    """
    from app.schemas.evaluation import (
        EvaluationRequest,
        canonicalize_json,
        compute_sha256,
    )
    from app.core.engine import run_evaluation
    
    checks = {
        "schema_valid": False,
        "hash_determinism": False,
        "replay_integrity": False,
    }
    
    test_input = {
        "version": "v1",
        "subject": "self-test",
        "ruleset": "determinism-check",
        "payload": {"assert": True, "test_key": "test_value"},
        "injected_time_utc": "2000-01-01T00:00:00Z",
    }
    
    try:
        req = EvaluationRequest(**test_input)
        checks["schema_valid"] = True
    except Exception:
        req = None
    
    if req:
        try:
            canonical1 = canonicalize_json(test_input)
            hash1 = compute_sha256(canonical1)
            canonical2 = canonicalize_json(test_input)
            hash2 = compute_sha256(canonical2)
            checks["hash_determinism"] = (hash1 == hash2)
        except Exception:
            pass
        
        try:
            result1, _ = run_evaluation(req)
            result2, _ = run_evaluation(req)
            checks["replay_integrity"] = (
                result1.evaluation_id == result2.evaluation_id and
                result1.input_sha256 == result2.input_sha256 and
                result1.decision == result2.decision
            )
        except Exception:
            pass
    
    all_pass = all(checks.values())
    
    return templates.TemplateResponse("system_check.html", {
        "request": request,
        "checks": checks,
        "all_pass": all_pass,
    })

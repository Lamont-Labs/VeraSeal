"""FastAPI routes for the evaluation API."""
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
import os
import json

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
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    try:
        eval_request = EvaluationRequest(**body)
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
        raise HTTPException(status_code=409, detail=f"Storage failed (append-only violation): {e}")
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

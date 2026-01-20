# VeraSeal

## Overview
VeraSeal is a deterministic evaluator that records decisions with verifiable proof. It is a strict, append-only evaluation system with cryptographic provenance.

## Project Status
**Complete MVP with UI Improvements** - All features implemented and tested.

## Key Architecture Decisions
- **TZ=UTC**: Forced at process start for determinism
- **No randomness**: No uuid4, random, or secrets in evaluation path
- **No system clock**: Uses injected_time_utc only
- **Append-only**: Artifacts cannot be overwritten
- **Strict schemas**: Pydantic with extra="forbid"
- **Atomic writes**: temp file -> fsync -> rename

## Recent UI Improvements (Jan 2026)
- Guided decision form as primary input (not raw JSON)
- Raw JSON moved to Advanced Mode toggle
- Decision templates: Vendor Approval, Policy Exception, Risk Acceptance, Access Approval
- Human-readable summary above technical proof on result pages
- First-run walkthrough (4-step, dismissible, localStorage only)
- System self-test page at /system-check
- Local-only telemetry (page views, submissions via localStorage)

## Project Structure
```
app/
├── main.py              # Entry point (port 5000)
├── api/routes.py        # FastAPI routes
├── core/engine.py       # Deterministic evaluation engine (pure functions)
├── schemas/             # Pydantic v2 schemas
├── invariants/          # Pre/during/post checks
├── audit/store.py       # Filesystem artifact storage
├── replay/              # Replay verification
└── web/
    ├── templates/       # Jinja2 HTML templates
    │   ├── index.html
    │   ├── evaluation.html
    │   ├── replay.html
    │   ├── error.html
    │   └── system_check.html
    └── static/          # CSS and assets
artifacts/
├── evaluations/         # Per-evaluation artifact folders
└── manifests/           # Manifest JSON files
tests/
├── hostile/             # Hostile input tests
├── determinism/         # Determinism tests
└── replay/              # Replay integrity tests
docs/
└── VERASEAL_COMPLETE_DOCUMENTATION.md
```

## Commands
- **Run server**: `python -m app.main`
- **Run tests**: `pytest tests/ -v`

## API Endpoints
- `GET /` - Homepage with guided form
- `POST /evaluate` - Submit evaluation
- `GET /evaluations/{id}` - Proof detail page
- `GET /replay/{id}` - Verification result page
- `GET /system-check` - System self-test (no side effects)
- `GET /health` - Health check

## Dependencies
- fastapi, uvicorn[standard], pydantic, jinja2, python-multipart, pytest, httpx

## MVP Rule
IF payload.assert == true → ACCEPT, else → REJECT

## Constraints Preserved
- Evaluation logic: UNCHANGED
- Schemas: UNCHANGED
- Hashing: UNCHANGED
- Artifact storage: UNCHANGED
- Determinism: PRESERVED

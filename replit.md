# VeraSeal

## Overview
VeraSeal is a deterministic evaluator that records decisions with verifiable proof. It is a strict, append-only evaluation system with cryptographic provenance.

## Project Status
**Complete MVP** - All features implemented and tested.

## Key Architecture Decisions
- **TZ=UTC**: Forced at process start for determinism
- **No randomness**: No uuid4, random, or secrets in evaluation path
- **No system clock**: Uses injected_time_utc only
- **Append-only**: Artifacts cannot be overwritten
- **Strict schemas**: Pydantic with extra="forbid"
- **Atomic writes**: temp file -> fsync -> rename

## Project Structure
```
app/
├── main.py           # Entry point (port 5000)
├── api/routes.py     # FastAPI routes
├── core/engine.py    # Deterministic evaluation engine
├── schemas/          # Pydantic v2 schemas
├── invariants/       # Pre/during/post checks
├── audit/store.py    # Filesystem artifact storage
├── replay/           # Replay verification
└── web/templates/    # Jinja2 HTML templates
artifacts/
├── evaluations/      # Per-evaluation artifact folders
└── manifests/        # Manifest JSON files
tests/
├── hostile/          # Hostile input tests
├── determinism/      # Determinism tests
└── replay/           # Replay integrity tests
```

## Commands
- **Run server**: `python -m app.main`
- **Run tests**: `pytest tests/ -v`

## Dependencies
- fastapi, uvicorn[standard], pydantic, jinja2, python-multipart, pytest, httpx

## MVP Rule
IF payload.assert == true → ACCEPT, else → REJECT

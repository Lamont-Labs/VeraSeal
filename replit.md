# VeraSeal

## Overview
VeraSeal is a deterministic evaluator that records decisions with verifiable proof. It is a strict, append-only evaluation system with cryptographic provenance. Target audience: compliance, risk, audit, legal, and governance teams.

## Project Status
**Complete MVP with Real Policy-Based Evaluation** - Placeholder logic removed, replaced with evaluation-policy-v1. 248 tests passing.

## Key Architecture Decisions
- **TZ=UTC**: Forced at process start for determinism
- **No randomness**: No uuid4, random, or secrets in evaluation path
- **No system clock**: Uses injected_time_utc only
- **Append-only**: Artifacts cannot be overwritten
- **Strict schemas**: Pydantic with extra="forbid"
- **Atomic writes**: temp file -> fsync -> rename
- **Fail-closed**: Any missing or invalid field results in REJECT

## Evaluation Policy v1 (Current)
The system now uses **evaluation-policy-v1** with real business rules:

### Required Payload Fields
- **decision_requested**: Must be exactly `"ACCEPT"` or `"REJECT"`
- **justification**: Must be a non-empty string

### Evaluation Rules (in order)
| Rule | Check | Failure |
|------|-------|---------|
| R001 | decision_requested field present | REJECT |
| R002 | decision_requested is "ACCEPT" or "REJECT" | REJECT |
| R003 | justification field present | REJECT |
| R004 | justification is non-empty string | REJECT |
| R005 | Record the decision | (success) |

### No Type Coercion
- `"accept"`, `true`, `1` are all INVALID (must be exactly `"ACCEPT"`)
- Empty or whitespace-only justification is REJECTED

## Recent Changes (Jan 2026)
- **Placeholder Removal**: Removed MVP rule (`payload.assert == true`)
- **Policy v1 Implementation**: Real evaluation policy with decision_requested and justification
- **Fail-Closed Behavior**: Missing/invalid fields always result in REJECT
- **Replay Compatibility**: Legacy artifacts auto-detect and replay correctly
- **UI Updated**: Form now uses decision_requested/justification instead of assert

## Project Structure
```
app/
├── main.py              # Entry point (port 5000)
├── api/routes.py        # FastAPI routes
├── core/engine.py       # Deterministic evaluation engine (pure functions)
├── policy/              # Evaluation policy definitions
│   ├── __init__.py      # Policy loading and evaluation
│   └── evaluation_policy_v1.json
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
│   ├── test_hostile_inputs.py
│   └── test_adversarial.py   # Type coercion resistance tests
├── determinism/         # Determinism tests
│   ├── test_determinism.py
│   └── test_determinism_hard.py
├── replay/              # Replay integrity tests
│   ├── test_replay_integrity.py
│   └── test_replay_hard.py
├── api/                 # API endpoint tests
│   ├── test_api_endpoints.py
│   └── test_new_endpoints.py
├── schemas/             # Schema validation tests
│   └── test_schema_validation.py
└── invariants/          # Invariant check tests
    └── test_invariants.py
docs/
└── VERASEAL_COMPLETE_DOCUMENTATION.md
tools/
└── verify_published.py  # Deployment verification script
```

## Commands
- **Run server**: `python -m app.main`
- **Run tests**: `pytest tests/ -v`
- **Verify deployment**: `python tools/verify_published.py [BASE_URL]`

## API Endpoints
- `GET /` - Homepage with guided decision form
- `POST /evaluate` - Submit evaluation (with policy-based validation)
- `GET /evaluations/{id}` - Proof detail page
- `GET /evaluations/{id}/output` - Output JSON
- `GET /evaluations/{id}/bundle` - Download ZIP bundle
- `POST /replay/{id}` - Verification result
- `GET /replay/{id}` - Replay result page
- `GET /system-check` - System self-test (no side effects)
- `GET /health` - Health check
- `GET /version` - Version and git commit info
- `GET /schema` - Authoritative JSON schema with policy rules
- `GET /examples` - Canonical example payloads

## Dependencies
- fastapi, uvicorn[standard], pydantic, jinja2, python-multipart, pytest, httpx

## Test Suite (248 tests, 12 skipped)
- **Type coercion resistance**: lowercase, boolean, integer values rejected
- **Fail-closed behavior**: Missing decision_requested/justification -> REJECT
- **Determinism**: Canonicalization, parallel evaluation, hash stability
- **Replay**: Tamper detection, legacy compatibility
- **API endpoints**: All routes tested
- **Schema validation**: Comprehensive Pydantic v2 tests

## Replay Compatibility
- **New evaluations** (policy_id: evaluation-policy-v1): Use policy-based evaluation
- **Legacy evaluations** (missing policy_id): Auto-detect and use legacy MVP rule for replay

## Constraints Preserved
- Evaluation logic: DETERMINISTIC (no changes between runs)
- Schemas: STRICT (extra="forbid")
- Hashing: SHA-256, 64 hex chars
- Artifact storage: APPEND-ONLY
- Determinism: TZ=UTC, no randomness, no system clock

# Veritas / Sentinel Core

Deterministic Infrastructure Evaluator

## Overview

A strict, deterministic evaluation system that:
- Accepts structured evaluation requests
- Produces deterministic, reproducible outputs
- Stores all artifacts with cryptographic provenance
- Supports replay verification

## Quick Start

### Run the Server

```bash
python -m app.main
```

The server starts on port 5000 (or PORT env variable).

### Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Web UI for submitting evaluations |
| POST | /evaluate | Submit evaluation request (JSON) |
| GET | /evaluations/{id} | View evaluation details (HTML) |
| GET | /evaluations/{id}/input | Download input.json |
| GET | /evaluations/{id}/output | Download output.json |
| GET | /evaluations/{id}/trace | Download trace.json |
| GET | /evaluations/{id}/meta | Download metadata.json |
| GET | /evaluations/{id}/manifest | Download manifest.json |
| GET | /evaluations/{id}/bundle | Download ZIP bundle |
| POST | /replay/{id} | Verify replay determinism |
| GET | /replay/{id} | View replay result (HTML) |
| GET | /health | Health check |

## Example Request

```json
{
  "version": "v1",
  "subject": "test-subject",
  "ruleset": "test-ruleset",
  "payload": {
    "assert": true
  },
  "injected_time_utc": "2024-01-01T00:00:00Z"
}
```

## MVP Rule

The minimal evaluation rule:
- IF payload contains key "assert" with value `true` → ACCEPT
- Otherwise → REJECT

This is a placeholder rule for end-to-end system validation.

## Key Properties

- **Determinism**: Same input always produces same output
- **Append-only**: Artifacts cannot be overwritten
- **Provenance**: All artifacts are hashed and manifested
- **Replay**: Any evaluation can be re-run and verified

## Project Structure

```
app/
├── main.py           # Entry point
├── api/routes.py     # FastAPI routes
├── core/engine.py    # Deterministic engine
├── schemas/          # Pydantic schemas
├── invariants/       # Invariant checks
├── audit/store.py    # Artifact storage
├── replay/           # Replay verification
└── web/templates/    # HTML templates
artifacts/
├── evaluations/      # Per-evaluation folders
└── manifests/        # Manifest files
tests/
├── hostile/          # Hostile input tests
├── determinism/      # Determinism tests
└── replay/           # Replay tests
```

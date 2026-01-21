# VeraSeal

**Deterministic evaluation recording with cryptographic provenance for compliance, audit, legal, and governance teams.**

## What This Is

VeraSeal is a strict, append-only evaluation system that records decisions with verifiable proof. It is designed for teams that need to **prove** decisions after the fact — not make them.

**Who This Is For:**
- Teams responsible for decisions that must stand up to audits, reviews, or legal scrutiny
- Organizations that need to prove *why* a decision was made, not just *what* was decided
- Regulated or high-stakes environments: compliance, risk, legal, governance

**Who This Is NOT For:**
- If you want decisions automated, this is not for you
- If you're looking for analytics, optimization, or AI recommendations, this is not for you
- If you've never had to explain a past decision under scrutiny, this is not for you

## Quick Start

### 1. Open the UI Builder
Navigate to the homepage and use the guided form to create an evaluation request.

### 2. Generate JSON
The form generates valid JSON automatically. You can:
- Copy the JSON (pretty or minified)
- Copy the cURL command for API integration
- Submit directly from the form

### 3. Post to /evaluate
```bash
curl -X POST 'http://localhost:5000/evaluate' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": "v1",
    "subject": "vendor-approval",
    "ruleset": "vendor-onboarding-policy",
    "payload": {
      "decision_requested": "ACCEPT",
      "justification": "Vendor passed due diligence review. NDA signed. SOC2 certified."
    },
    "injected_time_utc": "2024-01-15T10:30:00Z"
  }'
```

## Evaluation Policy v1

VeraSeal uses **evaluation-policy-v1** to evaluate all decisions. This policy enforces:

### Required Payload Fields
1. **decision_requested**: Must be exactly `"ACCEPT"` or `"REJECT"`
2. **justification**: Must be a non-empty string explaining the decision

### Evaluation Rules (in order)
| Rule | Check | Failure |
|------|-------|---------|
| R001 | `decision_requested` field present | REJECT |
| R002 | `decision_requested` is "ACCEPT" or "REJECT" | REJECT |
| R003 | `justification` field present | REJECT |
| R004 | `justification` is non-empty string | REJECT |
| R005 | Record the decision | (success) |

### Fail-Closed Behavior
- Any rule failure results in **REJECT**
- No coercion: `"accept"`, `true`, `1` are all invalid (must be exactly `"ACCEPT"`)
- Empty or whitespace-only justification is rejected

## Example Payloads

**Vendor Approval (ACCEPT):**
```json
{
  "version": "v1",
  "subject": "vendor-approval",
  "ruleset": "vendor-onboarding-policy",
  "payload": {
    "decision_requested": "ACCEPT",
    "justification": "Vendor Acme Corp passed due diligence review. NDA signed 2024-01-10. SOC2 Type II certified."
  },
  "injected_time_utc": "2024-01-15T10:30:00Z"
}
```

**Risk Rejection (REJECT):**
```json
{
  "version": "v1",
  "subject": "risk-acceptance",
  "ruleset": "risk-assessment",
  "payload": {
    "decision_requested": "REJECT",
    "justification": "Risk RISK-2024-001 rejected due to insufficient mitigation controls. Residual risk exceeds acceptable threshold."
  },
  "injected_time_utc": "2024-01-15T16:00:00Z"
}
```

**Policy Exception (ACCEPT):**
```json
{
  "version": "v1",
  "subject": "policy-exception",
  "ruleset": "exception-review",
  "payload": {
    "decision_requested": "ACCEPT",
    "justification": "Exception granted for legacy system integration. Compensating controls in place. Review scheduled for 90 days."
  },
  "injected_time_utc": "2024-01-15T14:00:00Z"
}
```

## Why JSON-Only?

VeraSeal enforces strict JSON input for critical reasons:

1. **Determinism**: Every input must produce the exact same output, every time. Natural language parsing, CSV interpretation, or "smart" coercion would introduce non-determinism.

2. **Audit Trail**: JSON provides an unambiguous, machine-readable record that can be verified years later without interpretation.

3. **Provenance**: Cryptographic hashes are computed on canonical JSON. Any ambiguity in input format would break hash verification.

4. **Legal Standing**: When decisions need to stand up to legal scrutiny, there can be no room for "the system interpreted my input differently than I intended."

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Web UI with JSON builder |
| POST | /evaluate | Submit evaluation request |
| GET | /evaluations/{id} | View evaluation details |
| GET | /evaluations/{id}/output | Get output.json |
| GET | /evaluations/{id}/bundle | Download ZIP bundle |
| POST | /replay/{id} | Verify replay determinism |
| GET | /replay/{id} | View replay result |
| GET | /health | Health check |
| GET | /version | Version and commit info |
| GET | /schema | Authoritative JSON schema |
| GET | /examples | Canonical example payloads |
| GET | /system-check | System self-test page |

## Key Properties

- **Determinism**: Same input always produces same output (TZ=UTC, no randomness, no system clock)
- **Append-only**: Artifacts cannot be overwritten or modified (409 on collision)
- **Provenance**: All artifacts are hashed with SHA-256 and manifested
- **Replay**: Any evaluation can be re-run and verified at any time
- **Strict Schemas**: Pydantic with `extra="forbid"` — no unknown fields allowed
- **Fail-Closed**: Missing or invalid fields always result in REJECT

## Running the Server

```bash
python -m app.main
```

Server starts on port 5000 (or PORT environment variable).

## Running Tests

```bash
pytest tests/ -v
```

**Test Suite**: 240+ tests covering:
- Adversarial inputs (type coercion, injection, boundaries)
- Determinism (canonicalization, parallel evaluation, hash stability)
- Replay (tamper detection, edge cases)
- API endpoints (all routes, error handling)
- Schema validation (Pydantic strict mode)
- Invariant checks (pre/during/post)
- Fail-closed behavior (missing fields, invalid values)

## Verification Script

Run the published deployment verification:

```bash
python tools/verify_published.py http://localhost:5000
```

This script verifies:
- Health, version, schema, examples endpoints
- Evaluation submission with policy v1
- Fail-closed behavior for missing/invalid fields
- Replay determinism
- Policy ID in results

## Project Structure

```
app/
├── main.py              # Entry point (port 5000)
├── api/routes.py        # FastAPI routes
├── core/engine.py       # Deterministic evaluation engine
├── policy/              # Evaluation policy definitions
│   ├── __init__.py      # Policy loading and evaluation
│   └── evaluation_policy_v1.json
├── schemas/             # Pydantic v2 schemas
├── invariants/          # Pre/during/post checks
├── audit/store.py       # Filesystem artifact storage
├── replay/              # Replay verification
└── web/
    ├── templates/       # Jinja2 HTML templates
    └── static/          # CSS and assets
artifacts/
├── evaluations/         # Per-evaluation artifact folders
└── manifests/           # Manifest JSON files
tests/
├── hostile/             # Hostile input tests
├── determinism/         # Determinism tests
├── replay/              # Replay integrity tests
├── api/                 # API endpoint tests
├── schemas/             # Schema validation tests
└── invariants/          # Invariant check tests
tools/
└── verify_published.py  # Deployment verification script
docs/
└── VERASEAL_COMPLETE_DOCUMENTATION.md
```

## Replay Compatibility

VeraSeal supports replay for both new and legacy evaluations:

- **New evaluations** (policy_id: evaluation-policy-v1): Use the new policy-based evaluation
- **Legacy evaluations** (missing policy_id): Automatically use legacy MVP rule for replay

This ensures all historical artifacts remain verifiable.

## Changes from MVP

The original MVP used a placeholder rule (`payload.assert == true`). This has been replaced with:

- **evaluation-policy-v1**: A real, deterministic policy with required fields
- **decision_requested**: Explicit "ACCEPT" or "REJECT" value
- **justification**: Mandatory explanation for every decision
- **Fail-closed**: Any rule failure results in REJECT
- **policy_id in results**: Every evaluation records which policy was used

Legacy artifacts that used the placeholder rule remain replayable through automatic compatibility mode.

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
  -d '{"version":"v1","subject":"vendor-approval","ruleset":"vendor-onboarding-policy","payload":{"assert":true,"vendor_name":"Acme Corp"},"injected_time_utc":"2024-01-15T10:30:00Z"}'
```

### Example Payloads

**Vendor Approval (ACCEPT):**
```json
{
  "version": "v1",
  "subject": "vendor-approval",
  "ruleset": "vendor-onboarding-policy",
  "payload": {
    "assert": true,
    "vendor_name": "Acme Corp",
    "country": "US"
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
    "assert": false,
    "risk_id": "RISK-2024-001",
    "reason": "Insufficient mitigation"
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
    "assert": true,
    "policy_id": "SEC-001",
    "duration_days": 90
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

**The UI builder is a deterministic transform** — it takes explicit form fields and converts them 1:1 to the JSON schema. No interpretation, no guessing, no natural language parsing.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Web UI with JSON builder |
| POST | /evaluate | Submit evaluation request |
| GET | /evaluations/{id} | View evaluation details |
| GET | /evaluations/{id}/bundle | Download ZIP bundle |
| POST | /replay/{id} | Verify replay determinism |
| GET | /replay/{id} | View replay result |
| GET | /health | Health check |
| GET | /version | Version and commit info |
| GET | /schema | Authoritative JSON schema |
| GET | /examples | Canonical example payloads |
| GET | /system-check | System self-test page |

## MVP Rule

The current evaluation rule is minimal:
- IF `payload.assert === true` → **ACCEPT**
- Otherwise → **REJECT**

This is a placeholder rule for end-to-end validation. Production systems would implement domain-specific rules.

## Key Properties

- **Determinism**: Same input always produces same output (TZ=UTC, no randomness, no system clock)
- **Append-only**: Artifacts cannot be overwritten or modified
- **Provenance**: All artifacts are hashed with SHA-256 and manifested
- **Replay**: Any evaluation can be re-run and verified at any time
- **Strict Schemas**: Pydantic with `extra="forbid"` — no unknown fields allowed

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

## Verification Script

Run the published deployment verification:

```bash
python tools/verify_published.py http://localhost:5000
```

This script verifies:
- Health endpoint accessibility
- Version and schema endpoints
- Evaluation submission and replay
- Deterministic hash computation

## Project Structure

```
app/
├── main.py              # Entry point (port 5000)
├── api/routes.py        # FastAPI routes
├── core/engine.py       # Deterministic evaluation engine
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

## What Changed (January 2026)

### New Features
- **JSON Builder UI**: Guided form with templates (Vendor Approval, Policy Exception, Risk Acceptance, Access Approval)
- **Copy Buttons**: Copy JSON, minified JSON, or cURL command with one click
- **/version endpoint**: Returns version and git commit hash
- **/schema endpoint**: Returns authoritative JSON schema
- **/examples endpoint**: Returns canonical example payloads
- **Improved Error Messages**: Validation errors now include field, message, type, and suggested fix
- **Verification Script**: `tools/verify_published.py` for end-to-end deployment testing

### Improvements
- Enhanced test suite (240+ tests, 8.8x increase from original 26)
- Better validation error formatting with hints
- UI links to schema, examples, and version endpoints
- Documentation updated for compliance/audit audience

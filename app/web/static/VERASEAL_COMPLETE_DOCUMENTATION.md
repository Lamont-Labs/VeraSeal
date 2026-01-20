# VERASEAL - COMPLETE SYSTEM DOCUMENTATION

## Deterministic Decision Evaluator with Cryptographic Provenance

---

## 1. SYSTEM OVERVIEW

VeraSeal is a deterministic infrastructure evaluator that records decisions with verifiable proof. It is a strict, append-only evaluation system with cryptographic provenance.

**PURPOSE:**
- Record decisions with permanent, tamper-evident proof
- Prove how and why a decision was made
- Enable replay verification to confirm records haven't been altered
- Serve compliance, risk, audit, legal, and governance teams

**WHAT IT DOES:**
- Evaluates structured inputs under fixed rules
- Produces permanent verifiable records
- Supports replay verification
- Maintains strict determinism

**WHAT IT DOES NOT DO:**
- Take actions
- Execute transactions
- Change external systems
- Run autonomously
- Make decisions for you
- Provide analytics, optimization, or recommendations

---

## 2. TARGET AUDIENCE

**WHO THIS IS FOR:**
- Teams responsible for decisions that must stand up to audits, reviews, or legal scrutiny
- Organizations that need to prove WHY a decision was made, not just WHAT was decided
- Regulated or high-stakes environments: compliance, risk, legal, governance

**WHO THIS IS NOT FOR:**
- If you want decisions automated, this is not for you
- If you've never had to explain a past decision under scrutiny, this is not for you
- If you're looking for analytics, optimization, or recommendations, this is not for you

---

## 3. KEY ARCHITECTURE DECISIONS

**DETERMINISM GUARANTEES:**
- TZ=UTC: Forced at process start for determinism
- No randomness: No uuid4, random, or secrets in evaluation path
- No system clock: Uses injected_time_utc only (caller provides timestamp)
- Same input ALWAYS produces same output

**DATA INTEGRITY:**
- Append-only: Artifacts cannot be overwritten
- Strict schemas: Pydantic with extra="forbid" (no extra fields allowed)
- Atomic writes: temp file → fsync → rename (prevents partial writes)
- Cryptographic hashes: SHA-256 for all artifacts

**FAIL-CLOSED DESIGN:**
- Any invariant violation → operation fails immediately
- No silent fallbacks
- Explicit error messages for all failure modes

---

## 4. PROJECT STRUCTURE

```
app/
├── main.py              # Entry point (port 5000, forces TZ=UTC)
├── api/routes.py        # FastAPI routes (13 endpoints)
├── core/engine.py       # Deterministic evaluation engine (pure functions)
├── schemas/             # Pydantic v2 schemas
│   └── evaluation.py    # EvaluationRequest, EvaluationResult, TraceStep
├── invariants/          # Pre/during/post checks
│   └── checks.py        # Invariant enforcement layer
├── audit/store.py       # Filesystem artifact storage (atomic writes)
├── replay/              # Replay verification
│   └── replay.py        # Re-runs evaluation and compares hashes
└── web/
    ├── templates/       # Jinja2 HTML templates
    └── static/          # CSS styling

artifacts/
├── evaluations/         # Per-evaluation artifact folders
│   └── <evaluation_id>/ # Each evaluation has its own folder
│       ├── input.json
│       ├── output.json
│       ├── trace.json
│       └── metadata.json
└── manifests/           # Manifest JSON files
```

---

## 5. DATA SCHEMAS

### EVALUATION REQUEST (INPUT):

```json
{
  "version": "v1",
  "subject": "vendor-onboarding",
  "ruleset": "policy-check",
  "payload": {
    "assert": true,
    "vendor_name": "Acme Corp"
  },
  "injected_time_utc": "2024-01-15T10:30:00Z"
}
```

**CONSTRAINTS:**
- extra="forbid" → No extra fields allowed at root level
- Payload must be valid JSON types only (no NaN, Infinity, bytes)
- injected_time_utc must be RFC3339/ISO8601 format

### EVALUATION RESULT (OUTPUT):

```json
{
  "evaluation_id": "987ee59dd9439036",
  "input_sha256": "987ee59dd9439036d4280...",
  "output_sha256": "8c9c9b12570f3b376b7...",
  "manifest_sha256": "ae902e04aae9dc7f9...",
  "decision": "ACCEPT",
  "reasons": ["MVP rule: payload.assert == true"],
  "trace": [...],
  "created_time_utc": "2024-01-15T10:30:00Z"
}
```

---

## 6. EVALUATION LOGIC

### MVP RULE (CURRENT IMPLEMENTATION):

```
IF payload.assert == true → ACCEPT
ELSE → REJECT
```

This is a placeholder minimal rule for demo purposes.

### EVALUATION FLOW:

1. PRE invariants check (version, subject, ruleset, time, payload)
2. Canonicalize input (sorted keys, fixed separators, UTF-8)
3. Compute input SHA-256 hash
4. Derive evaluation_id (first 16 chars of input hash)
5. DURING invariants check (no clock reads, artifact dir only)
6. Apply MVP rule → ACCEPT or REJECT
7. Compute output SHA-256 hash
8. POST invariants check (hash formats, id derivation, non-empty reasons)
9. Store artifacts atomically
10. Compute manifest SHA-256 hash

### DETERMINISM GUARANTEE:

The same input will ALWAYS produce:
- Same evaluation_id
- Same input_sha256
- Same output_sha256
- Same decision
- Same trace

---

## 7. INVARIANT CHECKS

### PRE INVARIANTS (before evaluation):
- version_check: Must be "v1"
- subject_check: Non-empty, max 128 chars
- ruleset_check: Non-empty, max 128 chars
- injected_time_check: Must be provided
- payload_type_check: Must be dict
- no_extra_fields_check: No unknown fields

### DURING INVARIANTS (during evaluation):
- no_system_clock_read: No datetime.now() calls
- artifact_dir_only: Writes only to artifact directory

### POST INVARIANTS (after evaluation):
- input_hash_format: 64 hex chars
- output_hash_format: 64 hex chars
- evaluation_id_derivation: First 16 chars of input hash
- reasons_non_empty: Must have at least one reason
- decision_valid: Must be ACCEPT or REJECT

### STORAGE INVARIANTS:
- artifacts_dir_writable: Must be writable
- no_existing_evaluation: Append-only (no overwrites)

---

## 8. ARTIFACT STORAGE

### STORAGE LOCATION:

```
artifacts/evaluations/<evaluation_id>/
  ├── input.json      # Canonicalized input
  ├── output.json     # Decision result
  ├── trace.json      # Evaluation trace
  └── metadata.json   # Subject, ruleset, timestamps, hashes

artifacts/manifests/<evaluation_id>.manifest.json
  └── File list with SHA-256 hashes and sizes
```

### ATOMIC WRITE PROCESS:

1. Create temporary file in target directory
2. Write data to temp file
3. fsync to ensure data is on disk
4. Rename temp file to final name (atomic on POSIX)

### APPEND-ONLY POLICY:

- If evaluation_id already exists → FAIL with 409 Conflict
- No updates, no deletes, no modifications

---

## 9. REPLAY VERIFICATION

**PURPOSE:** Re-run an evaluation using stored input and verify that output matches. Proves the record has not been tampered with.

**PROCESS:**
1. Load saved input.json
2. Re-run evaluation engine
3. Recompute all hashes
4. Compare with saved output.json + manifest hashes
5. Any mismatch → FAIL CLOSED with explicit mismatch report

**VERIFIED ON REPLAY:**
- evaluation_id matches
- input_sha256 matches
- output_sha256 matches
- decision matches

---

## 10. API ENDPOINTS

### PAGES (HTML):
- `GET /` - Homepage with submission form
- `GET /evaluations/{id}` - Proof detail page
- `GET /replay/{id}` - Verification result page

### EVALUATION API:
- `POST /evaluate` - Submit evaluation request

### ARTIFACT DOWNLOADS:
- `GET /evaluations/{id}/input` - Raw input.json
- `GET /evaluations/{id}/output` - Raw output.json
- `GET /evaluations/{id}/trace` - Raw trace.json
- `GET /evaluations/{id}/meta` - Raw metadata.json
- `GET /evaluations/{id}/manifest` - Raw manifest.json
- `GET /evaluations/{id}/bundle` - ZIP bundle of all artifacts

### REPLAY API:
- `GET /replay/{id}` - HTML verification page
- `POST /replay/{id}` - JSON replay result

### HEALTH:
- `GET /health` - Returns status

---

## 11. ERROR HANDLING

### HTTP STATUS CODES:
- 200: Success
- 400: Invalid JSON or invariant violation
- 404: Evaluation not found
- 409: Append-only violation (duplicate evaluation_id)
- 422: Schema validation error (missing/invalid fields)
- 500: Internal error

### ERROR RESPONSE FORMAT:
```json
{ "detail": "Human-readable error message" }
```

---

## 12. COMMANDS

**Run server:**
```bash
python -m app.main
```

**Run tests:**
```bash
pytest tests/ -v
```

Server runs on port 5000 by default.

---

## 13. DEPENDENCIES

- fastapi
- uvicorn[standard]
- pydantic
- jinja2
- python-multipart
- pytest
- httpx

---

## 14. EXAMPLE USAGE

### SUBMIT EVALUATION (ACCEPT):

```bash
curl -X POST https://your-domain/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "version": "v1",
    "subject": "vendor-onboarding",
    "ruleset": "policy-check",
    "payload": {
      "assert": true,
      "vendor_name": "Acme Corp"
    },
    "injected_time_utc": "2024-01-15T10:30:00Z"
  }'
```

### VERIFY PROOF:

```bash
curl https://your-domain/replay/987ee59dd9439036
```

### DOWNLOAD PROOF BUNDLE:

```bash
curl -O https://your-domain/evaluations/987ee59dd9439036/bundle
```

---

## 15. SECURITY CONSIDERATIONS

- No authentication required (add as needed for production)
- Path traversal prevented (evaluation_id validated)
- No SQL/NoSQL injection (filesystem storage only)
- No secrets in evaluation path
- Append-only prevents data manipulation
- Cryptographic hashes detect tampering

---

## 16. CANONICALIZATION

JSON canonicalization ensures deterministic hashing:
- Sorted keys recursively
- Fixed separators: (",", ":")
- No extra whitespace
- UTF-8 encoding
- No NaN or Infinity allowed
- Dict keys must be strings

Example:
```
Input:  {"b": 2, "a": 1}
Canon:  {"a":1,"b":2}
```

---

## 17. SOURCE CODE

All source code is located in the `app/` directory:

- `app/main.py` - Entry point
- `app/core/engine.py` - Evaluation engine
- `app/schemas/evaluation.py` - Pydantic schemas
- `app/invariants/checks.py` - Invariant checks
- `app/audit/store.py` - Artifact storage
- `app/replay/replay.py` - Replay verification
- `app/api/routes.py` - API routes

---

*This system exists to record and prove decisions — nothing more.*

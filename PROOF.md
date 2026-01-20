# PROOF.md - Veritas / Sentinel Core

## Determinism Guarantees

### What IS Guaranteed

1. **Timezone Locking**: TZ=UTC is forced at process start via `os.environ["TZ"]="UTC"` and `time.tzset()`.

2. **Deterministic JSON Serialization**:
   - All JSON uses `sort_keys=True`
   - Fixed separators `(",", ":")`
   - No extra whitespace
   - UTF-8 encoding
   - NaN/Infinity forbidden

3. **Hash Computation**:
   - SHA-256 computed over canonical JSON bytes
   - evaluation_id = first 16 characters of input_sha256
   - All hashes are 64 lowercase hex characters

4. **No Randomness in Evaluation Path**:
   - No `random`, `uuid4`, `secrets` modules used
   - No system clock reads during evaluation
   - `created_time_utc` equals `injected_time_utc` (data only)

5. **Stable Ordering**:
   - Dict keys sorted recursively
   - Trace steps in deterministic order
   - File writes in stable order

### What IS NOT Allowed

1. **No Runtime Clock Reads**: Evaluation does not call `datetime.now()`, `time.time()`, etc.
2. **No Network Calls**: No external API dependencies
3. **No Database**: All state is filesystem-based
4. **No Background Tasks**: No schedulers, queues, or async jobs
5. **No Randomness**: UUID generation, random sampling, etc. forbidden

## Strict Schema Rules

1. **extra="forbid"**: All Pydantic models reject unknown fields
2. **Required Fields**: All fields are required (no defaults)
3. **Type Validation**: Strict type checking enabled
4. **Payload Validation**:
   - Only JSON-serializable types allowed
   - NaN and Infinity forbidden
   - Dict keys must be strings

## Hash Method and Canonicalization

```python
def canonicalize_json(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    ).encode("utf-8")

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

## Append-Only Artifact Policy

1. **Directory Check**: Before writing, verify directory does not exist
2. **File Check**: If any artifact file exists, fail closed
3. **Atomic Writes**: Write to temp file → fsync → rename
4. **No Overwrites**: Duplicate submissions return 409 Conflict

## Replay Verification Steps

1. Load saved `input.json`
2. Re-run evaluation engine (pure function)
3. Compute new hashes
4. Compare with saved `output.json`:
   - evaluation_id match
   - input_sha256 match
   - output_sha256 match
   - decision match
5. If any mismatch → return `replay_ok: false` with explicit mismatch list

## Known Platform Limitations

1. **ZIP Timestamps**: ZIP file timestamps are normalized to a fixed date (2000-01-01 00:00:00) for determinism. This is documented behavior.

2. **Platform Dependencies**: Replit may inject additional dependencies. Core dependencies are:
   - fastapi
   - uvicorn[standard]
   - pydantic
   - jinja2
   - python-multipart
   - pytest

## Explicit Statement

**Non-executing, evaluates and records only.**

This system:
- Does NOT execute arbitrary code
- Does NOT make network requests
- Does NOT modify external systems
- ONLY evaluates structured input against deterministic rules
- ONLY records provenance artifacts to local filesystem

# Rename Changelog

## Summary
Renamed product from "Veritas / Sentinel Core" and "Decision Proof System" to "VeraSeal".

This is a branding-only change with no behavior modifications.

## Modified Files

| File | Change Type |
|------|-------------|
| README.md | Header and tagline |
| PROOF.md | Header |
| replit.md | Header and overview |
| app/main.py | FastAPI title and description |
| app/web/templates/index.html | Title tag and H1 |
| app/web/templates/error.html | Title tag |
| app/web/templates/evaluation.html | Title tag |
| app/web/templates/replay.html | Title tag |

## Before/After Snippets

### README.md
**Before:**
```markdown
# Veritas / Sentinel Core

Deterministic Infrastructure Evaluator
```

**After:**
```markdown
# VeraSeal

VeraSeal is a deterministic evaluator that records decisions with verifiable proof.
```

### PROOF.md
**Before:**
```markdown
# PROOF.md - Veritas / Sentinel Core
```

**After:**
```markdown
# PROOF.md - VeraSeal
```

### replit.md
**Before:**
```markdown
# Veritas / Sentinel Core

## Overview
Deterministic Infrastructure Evaluator - a strict, append-only evaluation system...
```

**After:**
```markdown
# VeraSeal

## Overview
VeraSeal is a deterministic evaluator that records decisions with verifiable proof. It is a strict, append-only evaluation system...
```

### app/main.py
**Before:**
```python
app = FastAPI(
    title="Veritas / Sentinel Core",
    description="Deterministic Infrastructure Evaluator",
    version="1.0.0",
)
```

**After:**
```python
app = FastAPI(
    title="VeraSeal",
    description="Deterministic evaluator that records decisions with verifiable proof",
    version="1.0.0",
)
```

### app/web/templates/index.html
**Before:**
```html
<title>Decision Proof System</title>
...
<h1>Decision Proof System</h1>
```

**After:**
```html
<title>VeraSeal</title>
...
<h1>VeraSeal</h1>
```

### app/web/templates/error.html
**Before:**
```html
<title>Error - Decision Proof System</title>
```

**After:**
```html
<title>Error - VeraSeal</title>
```

### app/web/templates/evaluation.html
**Before:**
```html
<title>Decision Proof - {{ evaluation_id }}</title>
```

**After:**
```html
<title>VeraSeal - {{ evaluation_id }}</title>
```

### app/web/templates/replay.html
**Before:**
```html
<title>Verify Proof - {{ evaluation_id }}</title>
```

**After:**
```html
<title>VeraSeal - Verify {{ evaluation_id }}</title>
```

## Unchanged
- All API endpoints
- All schema field names
- All module/package names
- All test files
- All evaluation logic
- All hash computation
- All artifact storage

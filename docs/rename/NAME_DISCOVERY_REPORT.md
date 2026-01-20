# Name Discovery Report

## Discovery Date
2024-01-20

## Search Patterns Used
- veritas (case-insensitive)
- sentinel (case-insensitive)
- veragate (case-insensitive)
- truth (case-insensitive)
- HTML `<title>` tags
- HTML `<h1>` tags

## Matches Found

### Pattern: "Veritas / Sentinel Core"

| File Path | Line Number | Exact String | Category |
|-----------|-------------|--------------|----------|
| replit.md | 1 | `# Veritas / Sentinel Core` | docs header |
| PROOF.md | 1 | `# PROOF.md - Veritas / Sentinel Core` | docs header |
| README.md | 1 | `# Veritas / Sentinel Core` | docs header |
| app/main.py | 21 | `title="Veritas / Sentinel Core"` | metadata label |

### Pattern: "Decision Proof System" (UI Product Name)

| File Path | Line Number | Exact String | Category |
|-----------|-------------|--------------|----------|
| app/web/templates/index.html | 6 | `<title>Decision Proof System</title>` | UI title |
| app/web/templates/index.html | 12 | `<h1>Decision Proof System</h1>` | UI header |
| app/web/templates/error.html | 6 | `<title>Error - Decision Proof System</title>` | UI title |

### Pattern: "Decision Proof" (Page-specific titles)

| File Path | Line Number | Exact String | Category |
|-----------|-------------|--------------|----------|
| app/web/templates/evaluation.html | 6 | `<title>Decision Proof - {{ evaluation_id }}</title>` | UI title |
| app/web/templates/evaluation.html | 14 | `<h1>Decision Proof Generated</h1>` | UI header |
| app/web/templates/replay.html | 6 | `<title>Verify Proof - {{ evaluation_id }}</title>` | UI title |
| app/web/templates/replay.html | 15 | `<h1>Verify Proof Record</h1>` | UI header |

## No Matches Found
- veragate: 0 matches
- truth: 0 matches (as product name)

## Conclusion
Two product names are in use:
1. **"Veritas / Sentinel Core"** - Used in documentation and API metadata
2. **"Decision Proof System"** - Used in user-facing UI

Both will be replaced with **"VeraSeal"** as per the rename instruction.

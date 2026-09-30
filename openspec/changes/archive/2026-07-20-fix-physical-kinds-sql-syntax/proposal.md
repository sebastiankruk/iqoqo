---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

The script `fix_physical_kinds.py` throws a `SyntaxError` when attempting to apply format mappings. The error `syntax error at or near ":"` occurs because the raw SQL string contains `:target::text`. SQLAlchemy's `text()` construct interprets colons as bind parameter markers, so `::` confuses the parser. This prevents the script from updating manifestation formats correctly.

## What Changes

- Modify the `_update_manifestation_format` function in `scripts/fix_physical_kinds.py`.
- Replace the PostgreSQL specific type cast `::text` with standard SQL `CAST(:target AS text)` or escape the colon to prevent SQLAlchemy from parsing it incorrectly.

## Capabilities

### New Capabilities

### Modified Capabilities

- `format-mapping-cli`: Update the CLI specification to ensure that database updates are applied without syntax errors.

## Impact

- Backend: `scripts/fix_physical_kinds.py` SQL update queries.

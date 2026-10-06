---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Fix SQL Syntax in Script

- [x] 1.1 Locate `scripts/fix_physical_kinds.py`.
- [x] 1.2 Find the `_update_manifestation_format` function containing the `UPDATE catalog.manifestations` query.
- [x] 1.3 Change `:target::text` to `CAST(:target AS text)` or properly escape the colon so SQLAlchemy doesn't misinterpret it.
- [x] 1.4 Do the same for `_update_manifestation_format_for_nulls` if it uses the same syntax.

## 2. Validation

- [x] 2.1 Run `make fix-physical-kinds ARGS="--apply --dry-run"` to confirm the syntax error is gone and the SQL compiles/runs without modifying data.
- [x] 2.2 Run `make fix-physical-kinds ARGS="--apply"` (if safe in development) to confirm data updates work.

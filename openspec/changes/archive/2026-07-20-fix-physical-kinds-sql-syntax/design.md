---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

The backend maintenance script `fix_physical_kinds.py` fails when attempting to persist format updates to the database (`--apply`). The error trace reveals a `psycopg2.errors.SyntaxError` at `to_jsonb(:target::text)`. SQLAlchemy's text parser intercepts colons `:` as placeholders for bind parameters, so the PostgreSQL double-colon `::` cast operator breaks the query execution.

## Goals / Non-Goals

**Goals:**

- Fix the SQL syntax error so that `make fix-physical-kinds ARGS="--apply"` runs successfully without breaking.

**Non-Goals:**

- Changing the underlying JSONB logic or database schema.

## Decisions

- **Avoid PostgreSQL type cast shorthands in SQLAlchemy `text()`**: We will update `scripts/fix_physical_kinds.py` to use `CAST(:target AS text)` instead of `:target::text`. This is standard SQL syntax and works seamlessly with SQLAlchemy's parameter binding logic.

## Risks / Trade-offs

- [Risk] Other scripts might be using similar PostgreSQL cast shorthands. → [Mitigation] Ensure this script functions first, and leave broad codebase sweeps for a different task.

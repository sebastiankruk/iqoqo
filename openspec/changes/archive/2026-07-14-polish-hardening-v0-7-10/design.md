---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

The system has accrued some minor technical debt (from the v0.7.9 cycle) impacting testing stability, test configuration, and data-layer performance.
Currently, `DataManager.get_faceted_stats` performs aggregation by pulling data into Python memory and utilizing `collections.Counter`. For the FRBR `Work` entity, specifically the `genres` array inside the `meta` JSONB column, this in-memory aggregation is inefficient at scale.
Additionally, backend lint safeguard tests (`tests/test_lint_safeguards.py`) use simple substring matching for pylint directives, which leads to false positives when developers include strings like `# pylint: disable=broad-exception-caught` inside explanatory comments. The frontend `vitest.setup.ts` has a minor duplicate section header.

## Goals / Non-Goals

**Goals:**

- Push faceted stats aggregation down to the PostgreSQL layer to reduce memory consumption and application-side processing time.
- Eliminate false positives in the lint safeguard tests.
- Maintain data parity for faceted stats (the refactored query must produce the exact same counts as the in-memory `Counter`).

**Non-Goals:**

- Refactoring other `DataManager` methods.
- Adding new faceted fields to the analytics dashboard.
- Redesigning the `Work` table schema beyond the addition of a targeted GIN index.

## Decisions

**1. Database Aggregation over In-Memory Counting**
We will replace Python's `Counter` in `DataManager.get_faceted_stats` with native SQLAlchemy queries utilizing `jsonb_array_elements_text`, `GROUP BY`, and `COUNT`.
_Rationale:_ Postgres is heavily optimized for grouping and aggregating sets. Returning pre-aggregated counts saves significant I/O and CPU time compared to returning full rows and counting them in the application layer.

**2. GIN Index with `jsonb_path_ops`**
We will generate an Alembic migration to apply `CREATE INDEX idx_work_meta_genres_gin ON work USING gin ((meta->'genres') jsonb_path_ops)`.
_Rationale:_ Using `jsonb_path_ops` provides a smaller index size and faster execution for `@>` (contains) queries compared to the default `jsonb_ops`. This perfectly aligns with our faceted navigation requirements for genres.

**3. Anchored Regex for Lint Safeguards**
Instead of simple `.contains()` checks, `test_lint_safeguards.py` will use an anchored regular expression (e.g., `^\s*#\s*pylint:\s*disable=broad-exception-caught`) or parsing via Python's `ast` module.
_Rationale:_ An anchored regex ensures the test only catches actual directive usages that start a line (with optional whitespace), ignoring directives embedded in longer explanatory strings or markdown text inside the python file.

## Risks / Trade-offs

- **Risk:** The GIN index increases disk space and introduces a slight write overhead when inserting/updating the `meta` column.
  - **Mitigation:** The read-heavy nature of faceted stats and catalog browsing justifies the trade-off. We are explicitly targeting the `meta->'genres'` path rather than the entire `meta` object to keep the index compact.
- **Risk:** SQL aggregations might behave differently if the JSONB array contains nulls or differing types.
  - **Mitigation:** `jsonb_array_elements_text` normalizes the outputs to text, and we will write Pytest asserts to guarantee exact parity between old and new methods.

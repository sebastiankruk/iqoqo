---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

This change focuses strictly on technical debt and system stability as part of the v0.7.10 Phase 1 release (carry-overs from v0.7.9). The goal is to polish QA/linting safeguards and harden the database schema and data layer to improve performance for faceted stats aggregation.

## What Changes

- Refactor `tests/test_lint_safeguards.py` to correctly identify actual `# pylint: disable=broad-exception-caught` directives (e.g., using anchored regex) rather than matching substrings in explanatory comments or strings.
- Remove duplicate section header in `frontend/vitest.setup.ts:165`.
- Generate and apply an Alembic migration to add a GIN index: `idx_work_meta_genres_gin` on `work` table `meta->'genres'` using `jsonb_path_ops`.
- Refactor `DataManager.get_faceted_stats` to replace the Python-memory `Counter` iteration with optimized SQL aggregations utilizing `jsonb_array_elements_text`, `COUNT`, and `GROUP BY`, leveraging the new GIN index.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- None (Performance and refactoring only, no requirement changes)

## Impact

- **Backend Tests:** Improved resilience of linting safeguard tests (`test_lint_safeguards.py`).
- **Frontend Tests:** Cleaned up test setup configuration (`vitest.setup.ts`).
- **Database:** Faster JSONB queries for genres on the `work` table via GIN index.
- **Backend Data Layer:** Reduced memory footprint and faster execution times for `DataManager.get_faceted_stats`. Aggregate parity must be maintained.

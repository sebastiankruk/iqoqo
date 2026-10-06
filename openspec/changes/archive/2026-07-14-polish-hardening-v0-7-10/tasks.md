---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. QA & Linting Polish (Low Risk)

- [x] 1.1 Refactor backend test `tests/test_lint_safeguards.py` to use anchored regex for `pylint: disable` directives.
- [x] 1.2 Remove duplicate section header comment in frontend `frontend/vitest.setup.ts:165`.
- [x] 1.3 Run backend tests to verify safeguard ignores valid inline strings.
- [x] 1.4 Run frontend tests (`vitest`) to verify test suite integrity.

## 2. Database Schema Hardening

- [x] 2.1 Generate an Alembic migration script for the new index.
- [x] 2.2 Add `CREATE INDEX idx_work_meta_genres_gin ON catalog.works USING gin ((meta::jsonb->'genres') jsonb_path_ops)` to the migration.
- [x] 2.3 Write and run Pytest for the migration upgrade/downgrade paths.
- [x] 2.4 Apply the database migration locally.

## 3. Data Layer Refactoring

- [x] 3.1 Refactor `DataManager.get_faceted_stats` to remove Python `Counter` aggregation.
- [x] 3.2 Implement dialect-aware SQLAlchemy query: PostgreSQL uses `jsonb_array_elements_text`, `COUNT()`, and `GROUP BY`; SQLite falls back to in-memory Counter.
- [x] 3.3 Write/update Pytest tests to verify exact aggregate parity between old and new methods.
- [ ] 3.4 (Optional if existing tests cover it) Run Playwright E2E test to verify analytics/dashboard UI renders faceted stats accurately.

## Why

The `feat/0.8.0/semantic-web` branch contains a complete, tested implementation of the Linked Open Data architecture (SPARQL endpoint, SHACL validation, Schema.org mappings, Data Sovereignty Export, ETL scripts) built during a prior session (2026-05-31). However, the branch is based on v0.7.0 and diverges by 804 files from current `main` — it includes deletions and regressions relative to the v0.7.11–v0.7.18 hardening work. We need to selectively extract only the semantic web additions onto `release/0.8.0` without importing any regressions.

## What Changes

- Cherry-pick **12 new files** from `feat/0.8.0/semantic-web` onto a `chore/0.8.0/cherry-pick-semantic` integration branch:
  - `app/api/sparql.py` — SPARQL blueprint (POST+GET `/api/sparql`)
  - `app/core/sparql_service.py` — In-memory graph materialization + query execution
  - `app/core/shacl_service.py` — pyshacl integration for RDF validation
  - `frontend/app/admin/sparql/page.tsx` — Admin SPARQL explorer UI
  - `scripts/sync_ontology.py` — DB model ↔ OWL ontology drift detection
  - `scripts/audit_frbr_integrity.py` — FRBR data integrity audit
  - `scripts/etl_frbr_strict.py` — Idempotent FRBR data cleanup ETL
  - `tests/test_sparql.py`, `tests/test_data_export.py`, `tests/test_shacl_validation.py`, `tests/test_schema_org_mapping.py`, `tests/test_semantic_web_gaps.py` — Test suites (1227+ lines)
- Selectively merge **7 modified files** — extract only semantic additions (SCHEMA_TYPE_MAP, `_enrich_graph_from_db`, export endpoint, sitemap, JSON-LD expansion, Export UI, Makefile targets)
- Resolve conflicts with v0.7.18 hardened patterns (auth decorators, rate limiters, error handling, Fernet encryption)
- Add `pyshacl>=0.26.0` dependency
- Register `sparql_bp` blueprint in `app/__init__.py`
- **Do NOT cherry-pick** any file deletions, v0.7.x test removals, or openspec spec deletions from the old branch

## Capabilities

### New Capabilities

_None — this change integrates existing code. All behavioral capabilities (SPARQL, SHACL, Schema.org, Export) will be formally specified in subsequent changes (C1–C7) after the code is available on `release/0.8.0`._

### Modified Capabilities

_None — no spec-level behavior changes. This is a pure integration/refactor task._

> **Note:** This change sets `skip_specs: true` because it introduces no new behavioral requirements — it ports existing, tested code to the current branch. The ported features will be formally specified, validated, and extended in changes C1–C7.

## Impact

- **Backend:** New files in `app/api/`, `app/core/`, `scripts/`; modified `app/core/frbr_service.py`, `app/api/system.py`, `app/api/public.py`, `app/__init__.py`, `Makefile`
- **Frontend:** New SPARQL admin page; modified `manifestation/[id]/page.tsx`, `collection/page.tsx`, `profile/page.tsx`
- **Dependencies:** `pyshacl>=0.26.0` added to `pyproject.toml` and `requirements.txt`
- **Tests:** 5 new test files (1227+ lines, ~90 tests)
- **Risk:** Merge conflicts in `frbr_service.py` (855-line diff) require careful selective application

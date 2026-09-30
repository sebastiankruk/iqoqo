## 1. Environment Preparation

- [x] 1.1 Create working branch `chore/0.8.0/cherry-pick-semantic` from `release/0.8.0` and verify the branch is active
- [x] 1.2 Update dependencies in `pyproject.toml` and `requirements.txt` (`pyshacl>=0.26.0`) and verify via `pip install -r requirements.txt`

## 2. Cherry-Pick New Files

- [x] 2.1 Extract completely new backend source files using `git checkout origin/feat/0.8.0/semantic-web -- <file>` for SPARQL and SHACL services, then verify files exist on disk
- [x] 2.2 Extract new scripts (`sync_ontology.py`, `audit_frbr_integrity.py`, `etl_frbr_strict.py`) using the same checkout command and verify they are present
- [x] 2.3 Extract new frontend SPARQL page (`frontend/app/admin/sparql/page.tsx`) and verify the file is present
- [x] 2.4 Extract the 5 new test files (`test_sparql.py`, `test_data_export.py`, etc.) and verify they are present

## 3. Selective Merge of Modified Files

- [x] 3.1 Extract semantic additions (e.g., `SCHEMA_TYPE_MAP`, `_enrich_graph_from_db`) from `app/core/frbr_service.py` into the current file and verify via `make format-python && make lint`
- [x] 3.2 Extract export endpoint additions into `app/api/system.py` and verify via `make lint`
- [x] 3.3 Extract sitemap additions into `app/api/public.py` and verify via `make lint`
- [x] 3.4 Extract semantic additions from `frontend/app/manifestation/[id]/page.tsx`, `collection/page.tsx`, `profile/page.tsx` into current files and verify via `cd frontend && npm run type-check`
- [x] 3.5 Update `Makefile` with the new targets (`audit-frbr`, `etl-frbr`, `sync-ontology`) and verify via `make help` (or visual inspection)
- [x] 3.6 Register `sparql_bp` in `app/__init__.py` and verify the app imports cleanly without syntax errors

## 4. Conflict Resolution & Hardening

- [x] 4.1 Update cherry-picked backend routes to match v0.7.18 auth and rate-limiting patterns, then verify via `make lint`
- [x] 4.2 Update frontend SPARQL page to match v0.7.18 layout/navbar and verify via `cd frontend && npm run lint`

## 5. Verification

- [x] 5.1 Run `make test` and verify all existing and newly cherry-picked tests pass
- [x] 5.2 Run `cd frontend && npx vitest run` and verify frontend tests pass

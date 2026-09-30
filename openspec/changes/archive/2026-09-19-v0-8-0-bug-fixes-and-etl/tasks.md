## 1. Frontend Bug Fixes (Rich Text & FRBR Editor)

- [x] 1.1 Install `dompurify`, `@types/dompurify`, and `react-markdown` in `frontend/package.json`, verifying installation by running `npm --prefix frontend ls dompurify react-markdown`
- [x] 1.2 Update `ExtendedMetadata` in `frontend/components/item/extended-metadata.tsx` to sanitize descriptions with DOMPurify and render markdown safely without raw markup leakage, verifying with unit tests in `frontend/__tests__/components/item/extended-metadata.test.tsx`
- [x] 1.3 Fix value binding and initial state synchronization for the Expression dropdown in `ExpressionEditor` within `frontend/components/admin/frbr-editor.tsx`, verifying with `npm --prefix frontend run test frontend/tests/frbr-editor.test.tsx`
- [x] 1.4 Execute frontend type-check and linting via `npm --prefix frontend run type-check && npm --prefix frontend run lint` to verify zero regressions

## 2. FRBR Database Integrity Audit Script

- [x] 2.1 Implement `scripts/audit_frbr_integrity.py` with `--json` and `--verbose` CLI options to detect orphaned entities, duplicate manifestations/works, and ISBN violations (checksums, length, Work-level placement), verifying with `python3 scripts/audit_frbr_integrity.py --help`
- [x] 2.2 Add unit and regression tests for `audit_frbr_integrity.py` under `tests/test_audit_frbr_integrity.py`, verifying detection of orphaned records, duplicates, and ISBN format anomalies with `pytest tests/test_audit_frbr_integrity.py`

## 3. Strict FRBR ETL Script

- [x] 3.1 Implement `scripts/etl_frbr_strict.py` featuring automated pre-execution database backup, `--dry-run` simulation, ISBN-10 to ISBN-13 normalization, moving Work-level ISBNs to Manifestations, and deduplicating Manifestations with Item reparenting, verifying with `python3 scripts/etl_frbr_strict.py --help`
- [x] 3.2 Add unit tests for `etl_frbr_strict.py` under `tests/test_etl_frbr_strict.py` verifying backup safety, duplicate merging, Item reparenting, and idempotent execution with `pytest tests/test_etl_frbr_strict.py`

## 4. Makefile Operational Targets & Change Validation

- [x] 4.1 Add `audit-frbr`, `etl-frbr`, and `sync-ontology` targets to `Makefile` with help documentation and `PYTHON_CMD` invocation, verifying with `make help`
- [x] 4.2 Verify openspec change artifacts and schema compliance by running `openspec validate v0-8-0-bug-fixes-and-etl`

## 5. Profile Navigation Unification

- [x] 5.1 Fix desktop dropdown in `frontend/components/dashboard/navbar.tsx` to rename "Profile Settings" to "Profile" pointing to `/profile`, and render "Admin Settings" (`/admin/settings`) conditionally for admin role only, verifying with `npm --prefix frontend run test`
- [x] 5.2 Fix mobile bottom nav in `frontend/components/dashboard/navbar.tsx` to change "Profile" href from `/admin/settings` to `/profile` and fix active state highlighting, verifying with visual inspection and test
- [x] 5.3 Fix admin sub-page sidebar NavItems in `frontend/app/admin/groups/page.tsx` and `frontend/app/admin/content/page.tsx` to point "Profile" to `/profile`
- [x] 5.4 Consolidate username, bio, avatar URL, and profile visibility editing from `/admin/settings` Profile tab into `frontend/app/profile/page.tsx`, verifying with `frontend/__tests__/app/profile/page.test.tsx`
- [x] 5.5 Gate `/admin/settings` behind admin role: remove "Profile" tab, add redirect for non-admin users to `/profile`, verifying with `frontend/__tests__/app/admin/settings/page.test.tsx`
- [x] 5.6 Add/update tests for navigation role-based visibility and route access control, verifying with `IQOQO_AI_MODE=1 make test-js`

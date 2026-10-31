## 1. Multi-Agent Review Sweep & Remediation

- [x] Execute security, SRE, and architecture review checklists.
- [x] Resolve all identified findings.
- [x] Run `make lint` and `make test` locally.

## 2. Core Domain & Operational Test Coverage Sweep

- [x] Author `tests/test_ontology_validation.py` covering runtime expansion guards in `app/core/ontology_validation.py`.
- [x] Author `tests/test_federation_guard.py` verifying `@federation_required` and `is_federation_enabled` in `app/api/federation_guard.py`.
- [x] Author `tests/test_search_types.py` verifying dialect-aware `SearchVector` compilation in `app/db/search_types.py`.
- [x] Author `frontend/__tests__/app/admin/lending.test.tsx` verifying custodian loan actions in `frontend/app/admin/lending/page.tsx`.
- [x] Author component tests for `frontend/components/item/item-timeline.tsx`, `frontend/components/item/star-rating.tsx`, and `frontend/components/admin/relation-management-dialog.tsx`.
- [x] Author operational tests for `scripts/archive_orphans.py`, `scripts/generate_ai_covers.py`, and `scripts/init_geonames_db.py`.

## 3. Mobile Readiness & Documentation Completion

- [x] Verify mobile discovery and auth endpoints.
- [x] Finalize `docs/FEDERATION.md`, `docs/API.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`, and `docs/CHANGELOG.md`.


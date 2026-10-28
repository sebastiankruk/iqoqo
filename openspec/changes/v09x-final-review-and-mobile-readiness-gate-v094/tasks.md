## 1. Multi-Agent Review Sweep & Remediation

- [ ] Execute security, SRE, and architecture review checklists.
- [ ] Resolve all identified findings.
- [ ] Run `make lint` and `make test` locally.

## 2. Core Domain & Operational Test Coverage Sweep

- [ ] Author `tests/test_ontology_validation.py` covering runtime expansion guards in `app/core/ontology_validation.py`.
- [ ] Author `tests/test_federation_guard.py` verifying `@federation_required` and `is_federation_enabled` in `app/api/federation_guard.py`.
- [ ] Author `tests/test_search_types.py` verifying dialect-aware `SearchVector` compilation in `app/db/search_types.py`.
- [ ] Author `frontend/__tests__/app/admin/lending.test.tsx` verifying custodian loan actions in `frontend/app/admin/lending/page.tsx`.
- [ ] Author component tests for `frontend/components/item/item-timeline.tsx`, `frontend/components/item/star-rating.tsx`, and `frontend/components/admin/relation-management-dialog.tsx`.
- [ ] Author operational tests for `scripts/archive_orphans.py`, `scripts/generate_ai_covers.py`, and `scripts/init_geonames_db.py`.

## 3. Mobile Readiness & Documentation Completion

- [ ] Verify mobile discovery and auth endpoints.
- [ ] Finalize `docs/FEDERATION.md`, `docs/API.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`, and `docs/CHANGELOG.md`.


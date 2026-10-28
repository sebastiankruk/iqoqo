## Why
Final release gate for the entire v0.9.x stream: ensures zero critical/high/moderate debt remains, documentation is 100% complete, and the server contract is ready for v1.0.0 native mobile apps.
## What Changes

- Execute full multi-agent review sweep (Security, SRE, QA, Ontologist, Architecture) across all v0.9.0–v0.9.4 code.
- Close remaining core test coverage gaps across backend guards, custodian frontend views, and administrative scripts:
  - Backend: Author `tests/test_ontology_validation.py` (runtime SHACL expansion guards in `app/core/ontology_validation.py`), `tests/test_federation_guard.py` (`@federation_required` and `is_federation_enabled` in `app/api/federation_guard.py`), and `tests/test_search_types.py` (`SearchVector` compilation in `app/db/search_types.py`).
  - Frontend: Author `frontend/__tests__/app/admin/lending.test.tsx` (custodian lending dashboard in `frontend/app/admin/lending/page.tsx`), and component tests for `item-timeline.tsx`, `star-rating.tsx`, and `relation-management-dialog.tsx`.
  - Scripts: Author operational tests for `scripts/archive_orphans.py`, `scripts/generate_ai_covers.py`, and `scripts/init_geonames_db.py`.
- Verify mobile client discovery contract (`GET /.well-known/nodeinfo`, `/api/auth/providers`, CORS, PAT/JWT refresh) required for upcoming v1.0.0 Capacitor apps.
- Finalize `docs/FEDERATION.md`, `docs/API.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`, and `docs/CHANGELOG.md`.

## Capabilities

### New Capabilities
- `v09x-review-mobile-readiness`: Multi-agent review sweep across 0.9.x, documentation completion, and verification of mobile app discovery/auth contract

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Final quality gate before v1.0.0 mobile milestone.

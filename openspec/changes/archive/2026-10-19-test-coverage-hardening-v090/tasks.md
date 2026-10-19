## 1. Backend Testing Layer (pytest)

- [x] 1.1 Add test verifying 100KB payload cap rejection (HTTP 413) on `POST /api/federation/inbox` in `tests/test_federation_e2e.py` and verify with `pytest tests/test_federation_e2e.py -k payload_cap`
- [x] 1.2 Add test verifying unauthenticated `GET /api/federation/lookup` rejection (HTTP 401) in `tests/test_federation_discovery.py` and verify with `pytest tests/test_federation_discovery.py -k lookup_unauthenticated`
- [x] 1.3 Add Alembic migration upgrade/downgrade schema verification tests in `tests/test_migration.py` for `v0_9_0_federation_schema` and `v0_9_0_user_default_visibility` and verify with `pytest tests/test_migration.py -k v0_9_0`

## 2. Frontend Component Testing Layer (Vitest)

- [x] 2.1 Add condition dropdown interaction test in `frontend/__tests__/components/item/edit-item-dialog.test.tsx` verifying condition changes are passed to `useUpdateItem` and verify with `npm --prefix frontend test edit-item-dialog`
- [x] 2.2 Add unit tests in `frontend/__tests__/app/profile/page.test.tsx` for `default_item_visibility` radio toggle and `FederationConsentSettings` rendering and verify with `npm --prefix frontend test profile/page`

## 3. Operational Script & Mount Security Layer (pytest + bats)

- [x] 3.1 Create `tests/test_pre_deploy_mounts.py` testing `scripts/pre_deploy_mounts.py` key modes (`0700` dir, `0600` pem files), secret file modes, and mount paths, and verify with `pytest tests/test_pre_deploy_mounts.py`
- [x] 3.2 Add test in `tests/bash/docker_entrypoint.bats` asserting `app/static/uploads/raw_covers` is checked for writability and verify with `bats tests/bash/docker_entrypoint.bats`

## 4. End-to-End Workflow Layer (Playwright)

- [x] 4.1 Add E2E scenario in `frontend/__tests__/e2e/manual_verification_integration.spec.ts` for editing item `local_barcode` and `condition` via `EditItemDialog` and verifying sidebar display
- [x] 4.2 Add E2E scenario in `frontend/__tests__/e2e/manual_verification_integration.spec.ts` for toggling federation privacy consent on `/profile` and verifying saved toast notification

## 5. Verification & Release Gate

- [x] 5.1 Run full CI test suites (`make lint`, `make test-backend`, `make test-frontend`, `make secret-scan`) and verify zero failures
- [x] 5.2 Run `make knowledge-sync` to update CodeGraph and Graphify indexes

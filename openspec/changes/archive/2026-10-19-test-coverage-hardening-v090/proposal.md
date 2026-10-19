## Why

Release 0.9.0 introduces decentralization, federation (ActivityPub/WebFinger), exemplar-level physical item barcodes, dual-source cover uploads, and container mount hardening. While core happy paths are tested, a pre-release test audit revealed targeted gaps across the four testing tiers: missing payload cap and authentication tests on federation endpoints, missing condition selection and profile defaults tests in UI components, missing permission tests for the pre-deploy operational script, and missing E2E flows for barcode editing and federation privacy toggles. Hardening these test suites guarantees release stability and prevents regressions.

## What Changes

- **Backend (`pytest`)**: Add test verifying 100KB payload cap (413) on `POST /api/federation/inbox`, test verifying unauthenticated rejection (401) on `GET /api/federation/lookup`, and Alembic migration upgrade/downgrade schema verification for `v0_9_0_federation_schema` and `v0_9_0_user_default_visibility`.
- **Frontend (`Vitest`)**: Add test for condition dropdown interaction in `EditItemDialog`, and add tests for `default_item_visibility` radio toggle and `FederationConsentSettings` inclusion on `ProfilePage`.
- **Scripts & Operations (`pytest` + `bats`)**: Create `tests/test_pre_deploy_mounts.py` verifying `data/keys` directory permissions (`0700`), `*.pem` file permissions (`0600`), and `.env` / `.allegro_token.json` (`0600`), and add `app/static/uploads/raw_covers` probe verification to `docker_entrypoint.bats`.
- **E2E Workflow (`Playwright`)**: Add scenarios in `manual_verification_integration.spec.ts` for item local barcode and condition editing via `EditItemDialog`, and for federation privacy consent toggle verification on `/profile`.

## Capabilities

### New Capabilities
- `release-090-test-coverage`: Comprehensive test coverage hardening across Backend, Frontend, Scripts, and E2E tiers for 0.9.0 federation, item barcode, and permission features.

### Modified Capabilities

## Impact

- Affected test suites: `tests/test_federation_e2e.py`, `tests/test_federation_discovery.py`, `tests/test_migration.py`, `tests/test_pre_deploy_mounts.py`, `tests/bash/docker_entrypoint.bats`, `frontend/__tests__/components/item/edit-item-dialog.test.tsx`, `frontend/__tests__/app/profile/page.test.tsx`, `frontend/__tests__/e2e/manual_verification_integration.spec.ts`.
- No production runtime API or schema breaking changes.

## 1. Multi-Instance Dual-Origin Playwright Suite

- [x] 1.1 Create `frontend/__tests__/e2e/federation_pair_live.spec.ts` with dual isolated browser contexts (`contextA` for Instance Alpha at `http://localhost:3000` and `contextB` for Instance Beta at `http://localhost:3001`), configure cookie consent bypass, and verify dual-origin connectivity without route mocks
- [x] 1.2 Implement live UI click-through for admin Trust Graph pairing on `/admin/federation` (Instance Alpha registers Instance Beta) and verify user federation consent toggle on `/profile` (Instance Beta user enables federated profile and collections)
- [x] 1.3 Implement live UI click-through for cross-instance user follow: User Alpha searches for and follows `@peeradmin@localhost:5005`, verifying signed `as:Follow` delivery in `/admin/federation` and Notification Center reception + acceptance (`as:Accept`) on Instance Beta
- [x] 1.4 Implement live UI click-through for federated lending: User Alpha navigates to `/federation/directory`, explores Instance Beta's public shelf, submits a loan request (`as:Offer`), and User Beta approves in `/admin/lending`, verifying collection status updates to `lent` and `ItemCustodyEvent` (`crm:E10_Transfer_of_Custody`) is written
- [x] 1.5 Implement live UI click-through for item return: User Beta marks the item returned in `/admin/lending`, verifying status resets to `available` and return custody event is logged
- [x] 1.6 Author `frontend/__tests__/e2e/help_hub_workflow.spec.ts` testing `/help` and `/help/[slug]` guide navigation, article breadcrumbs, and bilingual language switching

## 2. Makefile & Automation Harness

- [x] 2.1 Add `test-e2e-federation` target to `Makefile` that orchestrates `FEDERATION_PAIR=1` compose startup, runs `scripts/verify_federation_preview.sh` preflight, executes `playwright test frontend/__tests__/e2e/federation_pair_live.spec.ts`, and executes clean teardown
- [x] 2.2 Update `scripts/verify_federation_preview.sh` to ensure seed items and test accounts exist on both instances with required lending fixtures
- [x] 2.3 Author `tests/bash/verify_federation_preview.bats` testing `scripts/verify_federation_preview.sh` CLI arguments, preflight health verification, seeding modes, and exit codes

## 3. CI Pipeline Integration & Quality Gates

- [x] 3.1 Add `test-federation-pair-e2e` job to `.github/workflows/quality.yml` running `make test-e2e-federation` on Ubuntu runners and archiving Playwright traces on failure
- [x] 3.2 Verify all linters (`make lint`), secret scanners (`make secret-scan`), and OpenSpec validation (`openspec validate federation-pair-e2e-suite-v094`) pass cleanly

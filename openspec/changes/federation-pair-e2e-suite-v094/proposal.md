## Why

Currently, multi-instance federation between two live iQoQo stacks (primary and peer) is verified in CI either through single-process backend simulation mocks (`tests/test_federation_e2e.py`) or via isolated single-instance Playwright tests that fall back to mock routes when the peer container is offline (`federation_multi_instance.spec.ts`). Full multi-instance end-to-end user journeys (admin trust registration, user privacy consent, mutual follow handshakes, cross-instance library directory navigation, ActivityPub `as:Offer` loan requests, and CRM E10 custody transfer approvals) require manual execution against live preview stacks. Adding an automated dual-origin browser test suite executed against live paired containers in CI will prevent regression, guarantee cross-instance UI parity, and provide an automated safety net before v1.0.0.

## What Changes

- Add a live dual-origin Playwright E2E suite (`frontend/__tests__/e2e/federation_pair_live.spec.ts`) operating across two independent browser contexts connected to two live running instances without route mocks.
- Cover complete UI click-through workflows:
  - Admin Trust Graph pairing (`/admin/federation`) on both instances.
  - User federation consent opt-in on `/profile`.
  - Social search and follow request leading to live `as:Follow` delivery.
  - In-app notification center reception and approval on the remote instance.
  - Connected libraries directory exploration (`/federation/directory`).
  - Cross-instance item loan request (`as:Offer`) on remote friend's item.
  - Remote custodian approval in `/admin/lending`, asserting item status change to `lent` and `ItemCustodyEvent` (`crm:E10_Transfer_of_Custody`) logging.
  - Item return flow and custody timeline event logging.
- Add `make test-e2e-federation` Makefile target to orchestrate pairing setup, database seeding, health preflight, Playwright execution, and teardown.
- Integrate `test-federation-pair-e2e` job into GitHub Actions CI (`.github/workflows/quality.yml`).

## Capabilities

### Modified Capabilities

- `federation-multi-instance-e2e`: Add requirements for automated CI execution of live dual-origin browser click-throughs (without mock route fallbacks) and standardized Makefile/CI orchestration targets.

## Impact

- **Test Infrastructure**: New Playwright spec `frontend/__tests__/e2e/federation_pair_live.spec.ts`.
- **Build & CI**: New Makefile target `test-e2e-federation` and new CI job in `.github/workflows/quality.yml`.
- **Docker Compose**: Uses existing `docker-compose.federation-preview.yml` and prebuilt stack overlay.
- **Runtime Code**: Zero production runtime regressions; purely additive testing and CI verification hardening.

## Context

The repository has two levels of federation testing:
1. Backend simulation tests (`tests/test_federation_e2e.py`) executing cryptographic ActivityPub exchanges within a single pytest process using in-memory mocks.
2. Single-stack Playwright tests (`frontend/__tests__/e2e/federation_multi_instance.spec.ts`) that test WebFinger and cookie boundaries, but fall back to route mocking if a live secondary peer instance is not active.

Additionally, `scripts/verify_federation_preview.sh` and `docker-compose.federation-preview.yml` provide a working dual-stack preview environment (Instance Alpha on ports 8000/5001, Instance Beta on ports 3001/5005). What is missing is an end-to-end automated browser test suite that exercises both live instances simultaneously through real user clicks in Playwright and integrates directly into CI.

## Goals / Non-Goals

**Goals:**
- Author `frontend/__tests__/e2e/federation_pair_live.spec.ts` using dual isolated browser contexts (`contextA` for Instance Alpha, `contextB` for Instance Beta).
- Execute complete UI journeys with zero route mocking:
  - Admin Trust Graph pairing on `/admin/federation`.
  - User federation consent opt-in on `/profile`.
  - User search, profile inspection, and outbound follow.
  - Inbound follow notification in the Notification Center and follow acceptance.
  - Connected library directory exploration (`/federation/directory`).
  - Cross-instance item loan request (`as:Offer`).
  - Loan approval in lending admin, asserting item status transition to `lent` and immutable `ItemCustodyEvent` (`crm:E10_Transfer_of_Custody`) logging.
  - Item return flow and custody reconciliation.
- Add `test-e2e-federation` target in `Makefile` to automate lifecycle management (boot pair stack, preflight health verification, test run, teardown).
- Add CI job in `.github/workflows/quality.yml` to run the suite on release and federation PRs.

**Non-Goals:**
- Modifying backend ActivityPub protocol implementations or database models.
- Replacing existing unit tests or mock-capable single-instance Playwright tests.
- Testing third-party Fediverse software (e.g. Mastodon/Lemmy) in this test harness; focus is strictly iQoQo-to-iQoQo S2S federation.

## Decisions

### 1. Dual Browser Contexts vs. Sequential Single-Browser Runs
- **Decision**: Instantiate two concurrent browser contexts in Playwright (`contextA` targeting `ALPHA_URL`, `contextB` targeting `BETA_URL`).
- **Rationale**: Real-time federation involves asynchronous message exchange. A dual-context test allows User A to submit an action, and User B to immediately observe and respond to the resulting notification without session contamination or repeated logins.
- **Alternatives Considered**: Sequential login/logout in a single browser context was rejected because it introduces cookie pollution, significantly increases execution time, and cannot test concurrent interactions.

### 2. Reuse Existing Federation Pair Compose Infrastructure
- **Decision**: Reuse `docker-compose.prebuilt.yml` + `docker-compose.federation-preview.yml` rather than authoring a separate compose stack.
- **Rationale**: The preview federation pair stack already encapsulates multi-database PostgreSQL configuration, migration execution, and internal service discovery. Reusing it ensures that what is tested in CI matches the exact staging preview deployment.
- **Alternatives Considered**: Mocking HTTP calls with wiremock/mirage was rejected because it defeats the goal of validating live network-level ActivityPub signatures and real background Celery task dispatch.

### 3. Health Preflight via `verify_federation_preview.sh`
- **Decision**: Execute `bash scripts/verify_federation_preview.sh` before running Playwright.
- **Rationale**: Prevents flaky test runs by ensuring that PostgreSQL schemas are upgraded, test users are seeded with initial credentials, and WebFinger and HTTP endpoints are healthy before browser automation begins.
- **Alternatives Considered**: Letting Playwright wait on selector timeouts was rejected because container startup times vary on CI runners and could cause intermittent false-positive timeouts.

## Risks / Trade-offs

- **[Risk] Docker Container Startup Latency on CI Runners**
  → *Mitigation*: Use pre-built Docker image caching in GitHub Actions and implement a polling readiness loop with a 60s timeout before executing tests.
- **[Risk] Port Clashes on Developer Machines**
  → *Mitigation*: Allow overriding ports via environment variables (`PRIMARY_WEB_PORT`, `PEER_WEB_PORT`, `PRIMARY_API_PORT`, `PEER_API_PORT`) in both the Makefile and Playwright config.
- **[Risk] Asynchronous ActivityPub Delivery Delays**
  → *Mitigation*: Use Playwright's auto-retrying assertions (`await expect(locator).toBeVisible({ timeout: 10000 })`) when waiting for incoming notifications or activity log rows delivered via Celery.

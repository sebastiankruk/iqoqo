## Context

See `proposal.md` for motivation. Release 0.9.0 introduces significant architectural additions across Python/Flask backend and Next.js frontend, including S2S ActivityPub federation, key storage, physical item local barcodes, and container mount permissions. The testing strategy must align with the Four Invariant Testing Tiers defined in `iqoqo` standards:
1. Backend (`pytest` with database transaction isolation)
2. Frontend Component (`Vitest` + React Testing Library)
3. Script & Operations Layer (`pytest` + `bats`)
4. End-to-End Workflow Layer (`Playwright`)

## Goals / Non-Goals

**Goals:**
- Provide complete automated regression guards for all security and feature boundaries introduced in 0.9.0.
- Verify payload size limits (413) and route authentication guards (401) on federation endpoints.
- Ensure linear migration DAG consistency with automated schema round-trip tests for 0.9.0 migrations.
- Cover interactive UI controls in `EditItemDialog` (condition selection) and `ProfilePage` (privacy defaults and federation consent).
- Ensure operational script verification for container mount permissions and key protection modes (`0700` and `0600`).
- Validate end-to-end user flows for barcode editing and federation privacy consent in Playwright.

**Non-Goals:**
- Modifying production endpoint logic or UI markup (pure test coverage hardening).
- Full live S2S internet federated communication in CI (exercised via simulated two-instance in-memory test harnesses and Docker staging script).

## Decisions

### 1. Backend Inbound Payload and Auth Tests in Existing Suites
- **Decision**: Add 413 payload limit tests to `tests/test_federation_e2e.py` and unauthenticated 401 lookup tests to `tests/test_federation_discovery.py`.
- **Rationale**: Keeps federation tests co-located with their existing functional suites rather than introducing fragmented single-test files.
- **Alternatives Considered**: Creating a new `test_federation_security_gates.py` file. Rejected to avoid proliferation of small test modules when logical suites already exist.

### 2. Alembic Migration Upgrade/Downgrade Tests in `test_migration.py`
- **Decision**: Add isolated test functions for `v0_9_0_federation_schema` and `v0_9_0_user_default_visibility` in `tests/test_migration.py` matching the pattern used for `v0_8_4_item_local_barcode`.
- **Rationale**: Uses SQLite in-memory engine and Alembic `Operations` context to simulate upgrade and downgrade DDL execution, verifying table presence, index creation, and clean teardown.
- **Alternatives Considered**: Full PostgreSQL container migration run on every test execution. Rejected because Alembic schema assertions in `test_migration.py` run in sub-second time.

### 3. Operational Script Testing via Isolated Temporary Directories
- **Decision**: Test `scripts/pre_deploy_mounts.py` using `pytest` and `tmp_path` fixture in `tests/test_pre_deploy_mounts.py`.
- **Rationale**: Allows testing file permission modes (`0700`, `0600`, `0775`) deterministically on standard Linux filesystems without mutating host directories or requiring root privileges.
- **Alternatives Considered**: Running in a dedicated bats test file. Python `pytest` allows direct introspection of `os.stat().st_mode` and file metadata without shell parsing quirks.

### 4. Component Testing with `@testing-library/user-event`
- **Decision**: Update `edit-item-dialog.test.tsx` and `page.test.tsx` using `userEvent` for select and radio interactions.
- **Rationale**: Strictly complies with the `test-craftsman` guideline requiring `@testing-library/user-event` over raw synthetic `.click()` triggers to simulate real focus and input events.

### 5. Mocked Playwright E2E Integration Scenarios
- **Decision**: Add barcode editing and profile federation consent flows to `manual_verification_integration.spec.ts` using `page.route` intercepts.
- **Rationale**: Keeps E2E runs fast, deterministic, hermetic, and independent of external database state while exercising full browser UI rendering and event routing.

## Risks / Trade-offs

- **[Risk] Test session bleeding across Flask app contexts** → *Mitigation*: Ensure all new backend test fixtures explicitly execute `db.session.remove()` before and after yielding, adhering to the session isolation fix discovered in `test_iri_immutability.py`.
- **[Risk] Linux umask variations affecting permission mode tests** → *Mitigation*: In `test_pre_deploy_mounts.py`, explicitly mask `st_mode & 0o777` to assert exact octal permission bits.
- **[Risk] Playwright UI race conditions when toggling switches** → *Mitigation*: Use `expect(locator).toBeChecked()` and wait for network responses before asserting toast notifications.

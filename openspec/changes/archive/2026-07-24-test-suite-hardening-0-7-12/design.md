## Context

iqoqo 0.7.12 shipped with 114 changed files and ~6,992 new lines across escalation, scanner, permissions, dashboard insights, scripts, and UX. A systematic audit compared every 0.7.12 changelog entry against the existing 233 test files and identified 23 coverage gaps ranging from critical (components with zero tests) to low (missing edge cases in otherwise-tested components). The existing test infrastructure includes pytest (backend), Vitest (frontend unit), Playwright (E2E), and BATS (shell scripts). This change adds ~130-150 new tests across all layers without modifying any production code.

## Goals / Non-Goals

**Goals:**

- Eliminate critical test coverage gaps in scanner `bottom-sheet.tsx` (419 lines, 0% coverage) and `top-bar.tsx` (136 lines, 0% coverage)
- Close backend gaps: escalation `?status=` query filter, `write:metadata`/`read:metadata` API enforcement, resolver display name serialization
- Close frontend gaps: `ProcessedRequestsSection`, navbar help-requests link, `escalation-utils.tsx` utilities, deletion request UI, accordion/multi-escalation features
- Add E2E coverage for the full escalation submit-to-resolve workflow and scanner barcode-to-library workflow
- Add structural i18n test for `HelpRequests` key parity and completeness
- Add Pixel-inspection test for 0.7.12 fallback cover redesign
- Test untested scripts: `validate_yaml.py`, `sync_version.py` CLI modes, `json_extract()` dialect helper

**Non-Goals:**

- Performance/load testing (locust, k6, artillery)
- WCAG accessibility compliance testing (axe-core, pa11y)
- Firefox/WebKit E2E in CI (currently only Chromium)
- Systematic visual regression testing at scale
- Docker Compose integration tests beyond existing build validation
- Security penetration testing (OWASP-style)
- Production code changes or refactors
- Increasing test coverage in areas not touched by 0.7.12

## Decisions

### Decision 1: Unit tests over E2E for scanner components

**Choice**: Prioritize unit tests for `bottom-sheet.tsx` and `top-bar.tsx` rather than a single large E2E test.
**Rationale**: These components have complex internal state machines (ZXing barcode loop, tab switching, format selector optgroups). Unit tests with mocked dependencies provide better edge-case coverage and faster feedback than a single E2E flow. One E2E scanner test will still be added for the integration layer.
**Alternative**: One comprehensive E2E test. Rejected because it would be brittle against browser camera API differences and provide less coverage of error states.

### Decision 2: Reuse existing conftest.py fixtures, add targeted new ones

**Choice**: Use existing `admin_headers`, `normal_user_headers`, `restricted_user_headers` fixtures. Add a new `custodian_headers` fixture for permission enforcement tests.
**Rationale**: Existing fixtures cover admin and plain-user scenarios. The gaps are specifically around users with partial permission sets (e.g., `write:metadata` but not admin, `read:metadata` but not `write:metadata`). A `custodian_headers` fixture bridges this gap without modifying existing tests.
**Alternative**: Create per-test inline headers. Rejected because it duplicates boilerplate across 15+ new test functions.

### Decision 3: Escalation E2E uses seeded test data, not live user-creation

**Choice**: Extend `seed_e2e.py` to create a test escalation submitted by a regular user and seed it as pending. The E2E test logs in as custodian and resolves it.
**Rationale**: Avoids testing the submission form in E2E (already covered by backend and frontend unit tests). Focuses E2E on the integration: admin sees pending request → resolves it → user sees resolution.
**Alternative**: Full submit-then-resolve E2E. Would be 2x longer and test already-covered unit functionality.

### Decision 4: BATS tests for validate_yaml.py, pytest for sync_version.py

**Choice**: `validate_yaml.py` gets a BATS test (fits the scripts/bash pattern). `sync_version.py` CLI modes get pytest unit tests (fits `test_script_utilities.py` pattern). `json_extract()` gets a pytest test with parametrized SQLite/PostgreSQL modes.
**Rationale**: Aligns with existing test infrastructure patterns. BATS already covers script invocation. Pytest already covers script utility functions.

### Decision 5: Snapshot assertions enabled but with `maxDiffPixels` tolerance

**Choice**: Uncomment existing Playwright `toHaveScreenshot()` assertions with `maxDiffPixels: 200` tolerance and generate baseline snapshots during first CI run.
**Rationale**: The assertions already exist but are commented out. Enabling them with pixel tolerance accommodates minor rendering differences across CI runners while catching meaningful regressions.
**Alternative**: Pillow-level pixel comparison in backend tests. More precise but adds test complexity. Used as a supplement, not replacement.

### Decision 6: i18n test validates structural parity, not translation quality

**Choice**: Test that `HelpRequests` namespace keys are identical between en.json and pl.json, and that no values are empty strings. Do NOT test translation accuracy.
**Rationale**: Translation accuracy requires human review. Key parity and non-empty values catch the most common regression (adding a key to one language but not the other).
**Alternative**: Snapshot-based translation comparison. Rejected because snapshots would change with every intentional translation update.

## Risks / Trade-offs

- **Risk**: New scanner component tests may be flaky due to browser API mocks (MediaDevices, ZXing)
  - **Mitigation**: Mock all browser APIs at the Vitest level. Bottom-sheet tests will NOT attempt real camera access.

- **Risk**: E2E escalation test depends on seed data that must remain consistent
  - **Mitigation**: Document the seed data dependency in the spec file header. The seed script already has a stable, deterministic data set.

- **Risk**: Playwright visual snapshots may differ between local macOS and CI Linux
  - **Mitigation**: Use `maxDiffPixels: 200` tolerance. Generate baselines in CI on first run. If still flaky, disable and rely on Pillow-level backend test only.

- **Risk**: ~150 new tests increase CI runtime
  - **Mitigation**: All new tests are lightweight (no new Docker containers, no additional DB resets beyond existing E2E seed). Estimated CI impact: +2-3 minutes. Acceptable.

- **Trade-off**: Tests mock heavily in some areas (bottom-sheet mocks ZXing entirely)
  - **Rationale**: ZXing is an external library. Testing the integration is an E2E concern. Unit tests validate our orchestration logic around ZXing, not ZXing itself.

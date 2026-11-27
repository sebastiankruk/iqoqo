## Context

The `/test-craftsman` audit verified Alembic DAG linearity (`v1_2_0_item_physical_location` single head) and core happy paths for `v1.2.0`, but found three functional regressions (`SearchService` expanding bindparam, `DataManager` facet subqueries, `collection-url.ts` `location` sync), OpenAPI envelope mismatch on `/manifestations/{id}/stats`, two disallowed lint suppressions, and E2E/unit test coverage gaps across `C154`–`C158`, `C163`–`C164`.

## Goals / Non-Goals

- **Goals:**
  - Repair PostgreSQL FTS + `location` parameter binding and DTO projection in `SearchService` and `/api/items`.
  - Repair `locations` filtering across all facet counters in `DataManager`.
  - Repair `?location=...` URL hydration/serialization in `/collection`.
  - Align `app/api/docs.py` OpenAPI schemas and enforce `v1.2.0` endpoints in `test_openapi_contract_completeness.py`.
  - Bring `pytest`, `Vitest`, `BATS`, and `Playwright` E2E coverage to full `v1.2.0` parity with zero vacuous assertions and zero disallowed lint suppressions.
- **Non-Goals:**
  - Changing FRBR database schema or introducing new user-facing features beyond bugfixes and tests.

## Decisions

1. **Bug-First Regression Tests:** Every fix (`SearchService` bindparam, `DataManager` facet `locations`, `collection-url.ts` round-trip, OpenAPI `/stats` envelope) gets a failing regression test first before applying the fix.
2. **Test Hygiene & Accessible Selectors:** Replace `getByTestId` / `fireEvent` / dynamic `await import(...)` in new `v1.2.0` UI tests with accessible `getByRole` / `getByLabelText`, `userEvent`, and top-level imports, and remove `// eslint-disable-next-line` + `# pylint: disable=protected-access` suppressions cleanly.
3. **Full E2E Coverage:** Cover `C157` (`/item/[id]` location + `/collection?location=` + bulk location toolbar), `C158` (`/manifestation/[id]` covers gallery + stats card), `C156` (mobile `Footer` -> `ServerSelectorModal` switching), and `C164` (`/graph` Person canonical LOD dedup) in Playwright specs under `frontend/__tests__/e2e/`.

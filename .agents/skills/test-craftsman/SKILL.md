---
name: test-craftsman
description: "Skill for authoring and refining resilient backend (pytest), frontend (Vitest), and E2E (Playwright) test suites under FRBR ontologies."
license: AGPL
compatibility:
  - opencode
  - antigravity
metadata:
  audience: testers
---
# Test Crafting & Ingestion Skill

## Context

The iqoqo platform requires near 100% test coverage across a heterogeneous multi-layered architecture. To write valid tests, you must understand the exact responsibilities of each testing layer, respect data privacy boundaries, and validate complex FRBR ontology linkages without breaking or duplicating code.

### The Four Invariant Testing Tiers

1. **Backend Layer (`pytest` via `.venv/bin/pytest` or `make test-backend`)**
   - Validates FRBR mapping integrity, JSONB full-text search operators (`tsvector`), PostgreSQL schema isolation, and RDF/JSON-LD content negotiation endpoints.
2. **Frontend Component Layer (`Vitest` + `React Testing Library` via `make test-frontend`)**
   - Focuses on user-event interactions, state management hooks, mobile layouts, and proper error boundaries.
3. **End-to-End Workflow Layer (`Playwright` via `npx playwright test` under `frontend/`)**
   - Executes cross-layer scenarios (e.g., direct URL hydration tracking, user taxonomy role boundaries, multi-step acquisition or lending timelines).
4. **Script & Operations Layer (`bats` for shell scripts + `pytest` for operational Python scripts)**
   - Ensures administrative, deployment, database, and cloud backup utility scripts run correctly, validate arguments, fail gracefully, and preserve expected exit codes. Use stubs/mocks to avoid mutating real hosts or container states.

---

## Technical Guidelines for Code Generation

### A. Backend Testing (`pytest`)
- **Seeding & Fixtures:** Always use isolated database transactions per test. Use explicit factories or seed models that preserve relational integrity between Works, Expressions, Manifestations, and Items.
- **Strict Validation:** Assert response status codes, specific payload structures, and headers (e.g., provenance or taxonomy headers). Do not use broad exception handling.

### B. Frontend UI Testing (`Vitest` + RTL)
- **Accessible Queries:** Prioritize accessible locator strategies exactly as a user experiences the screen. Use `screen.getByRole`, `screen.getByLabelText`, and `screen.getByText`. Avoid querying raw CSS classes or test IDs unless an element has no semantic role.
- **User Actions:** Always employ `@testing-library/user-event` instead of raw `.click()` triggers to simulate genuine keystrokes and focus switches.

### C. End-to-End Workflow Testing (`Playwright`)
- **Accessible Selectors:** Use accessible role definitions (e.g., `page.getByRole('tab', { name: 'Expressions' })`).
- **URL Hydration & State Checks:** Explicitly assert navigation updates, query parameters preservation (e.g., checking if `?genres=Fiction&view=works` hydrates correctly), and prevent premature loop conditions.
- **Boundary Verification:** Securely verify personal workspace bounds vs. global graph tracking. Assert that global catalog layers (Manifestations, Expressions, Works) expose matching assets symmetrically, while local inventory layers (`view=items` or personal collections) strictly return an empty state if the user does not personally own a matching physical/digital copy.

---

## Operational Instructions for Agents

1. **Pre-emptive Formatting:** Before executing tests or evaluating linters, format your generated files using `.venv/bin/python -m black` for Python or Prettier for frontend files to eliminate layout friction.
2. **Zero-Silencing Policy:** Never introduce type/lint suppression tags (`# type: ignore`, `# noqa`, `/* eslint-disable */`, or `disable=too-many-statements`) to cover up complex test code. Refactor code block components or factor out dense fixtures into support modules.
3. **Targeted Verification Loop:** If an optimization command fails, invoke only the direct sub-task path (e.g., `.venv/bin/pytest tests/test_api.py -k test_target`) to isolate errors efficiently before triggering full suites.

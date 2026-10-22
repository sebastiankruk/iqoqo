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

## Role and Persona

You are a principal-level Quality Assurance Engineer and SDET (Software Developer in Test) working on **iqoqo**, an open-source, local-first digital library and cataloging system built on the FRBR/FRBRoo ontology.

Your primary objective is to act as the "Red Team" and "Safety Net" for the engineering team. You possess a deep understanding of the complex, event-based data model, the Flask backend, the Next.js frontend, and the Docker Compose orchestration. You are pragmatic, detail-oriented, and focused on long-term system stability over short-term feature velocity.

## Project Context

* **The Stack:** Python/Flask (API), React/Next.js (Web UI), PostgreSQL (Database), Redis/Celery (Background Tasks).
* **The Model:** Strict adherence to FRBR/FRBRoo.
* **The Risk:** The project has previously suffered from "AI-generated spaghetti code" and "technical debt accumulation." Your role is to prevent this from happening again.

## Current State

We are in the **v0.9.x stream (Federation, Social Library & Pre-1.0 Hardening)**; `main` is at **v0.9.2**, feature-complete and awaiting release, after **v0.9.0** and **v0.9.1** shipped (OpenSpec changes C71–C83b done). **v0.9.0** laid the foundation: `Item.local_barcode` (FRBR F5 physical tags), immutable canonical Actor/Object IRIs with `owl:sameAs` / ActivityStreams `Move` merge tombstones, the `federation` DB schema, Fernet-encrypted RSA-2048 actor keys, WebFinger/NodeInfo/Actor discovery, `draft-cavage-http-signatures-12` signing, an SSRF-safe `FederationClient` (IP-pinned via `http_client.py`), per-user `default_item_visibility` and `FederationConsent`, fail-fast container mount-permission checks, and multi-instance preview/E2E (`make preview-up FEDERATION_PAIR=1`). **v0.9.1** activated server-to-server ActivityPub (S2S only, no C2S): per-actor/shared Inbox and read-only Outbox, a dedicated `federation` Celery queue with 100KB caps and `bleach` sanitization, the Trust Graph (`untrusted | pending | trusted | blocked`) with provenance-aware metadata sync (`meta["_provenance"]`, `ProviderMergeDialog`), the `/admin/federation` dashboard, and a two-instance S2S security audit gate. **v0.9.2** adds the social layer: ActivityStreams 2.0 + CIDOC CRM (`crm:E10_Transfer_of_Custody`) social ontology and SHACL shapes, federated friends (`@user@domain`), friend collection/wishlist browsing, federated check-if-I-have-it, cross-instance `as:Offer`/`as:Accept` loans with immutable `ItemCustodyEvent` logging, the In-App Notification Center (`social.notifications`), SPARQL access-rights scoping (private items and non-consented collections excluded; isolated `sparql-runner` retained over Apache Fuseki per ADR), and a public connected-libraries directory (`/federation/directory`) plus in-app `/help` documentation hub. Developer knowledge tooling is the trio CodeGraph, Graphify and MemPalace.

## Upcoming (v0.9.3 & Beyond)

With v0.9.2 feature-complete, our focus is **v0.9.3: Async Transitions, Auth Hardening (PATs & OTP), OpenAPI 3.1 & BGG2** (C84–C87): asynchronous transition ingestion and background PostgreSQL `tsvector` FTS re-indexing via Celery + Redis with Server-Sent Events (`/api/v1/events/stream`); Personal Access Tokens (`iqo_*`, scoped Bearer auth, one-time secret display, revocation) and TOTP 2FA with recovery codes; migration to `boardgamegeek2` plus a 4-state Twitch/IGDB healthcheck in `make status`; and 100% OpenAPI 3.1 coverage (`/api/docs/openapi.json`) with new `federation-interop-tester` and `openapi-contract-auditor` skills and a collector Gemini Gem template (`docs/gems/iqoqo-librarian-gem.md`). Then **v0.9.4: Pre-1.0.0 Infrastructure, Native S3 & Mobile Readiness Gate** (C88–C90): retire residual `rclone` for native S3 backups (including the `federation` schema and encrypted actor keys), migrate local deployment to `iqoqo.kruk.cc`, codify Cloudflare WAF/Bot rules for Semantic Web and ActivityPub agents (`/.well-known/*`, `/api/federation/*`, `/api/public/rdf/*`), and run the full `0.9.x` multi-agent security/architecture review and mobile discovery/auth contract check (`NodeInfo`, `/api/auth/providers`, PAT/JWT refresh). This paves the way toward **v1.0.0: Native Mobile Ecosystem** (Capacitor iOS/Android, HASS-style server selector, bottom-action navigation) and **v1++** (Magic Shelf Scan AI, MCP server, monetization).

## QA Tooling & Frameworks Constraints

You must strictly utilize the existing tooling configured in the project:

* **Backend Testing:** `pytest` -> `make test-backend`
* **Backend Linting/Formatting:** `ruff`, `mypy`, `pylint`, `black`, and `isort` -> `make lint-backend`
* **Frontend Testing:** `Vitest` alongside `React Testing Library` -> `make frontend`
* **Frontend Linting/Formatting:** `eslint`, `prettier`, TypeScript compiler (`tsc`), and `stylelint` -> `make lint-frontend`
* **Documentation Linting:** `markdownlint-cli2`
* **E2E Testing:** Playwright

The iqoqo platform requires near 100% test coverage across a heterogeneous multi-layered architecture. To write valid tests, you must understand the exact responsibilities of each testing layer, respect data privacy boundaries, and validate complex FRBR ontology linkages without breaking or duplicating code.

### The Four Invariant Testing Tiers

1. **Backend Layer (`pytest` via `.venv/bin/pytest` or `make test-backend`)**
   * Validates FRBR mapping integrity, JSONB full-text search operators (`tsvector`), PostgreSQL schema isolation, and RDF/JSON-LD content negotiation endpoints.
2. **Frontend Component Layer (`Vitest` + `React Testing Library` via `make test-frontend`)**
   * Focuses on user-event interactions, state management hooks, mobile layouts, and proper error boundaries.
3. **End-to-End Workflow Layer (`Playwright` via `npx playwright test` under `frontend/`)**
   * Executes cross-layer scenarios (e.g., direct URL hydration tracking, user taxonomy role boundaries, multi-step acquisition or lending timelines).
4. **Script & Operations Layer (`bats` for shell scripts + `pytest` for operational Python scripts)**
   * Ensures administrative, deployment, database, and cloud backup utility scripts run correctly, validate arguments, fail gracefully, and preserve expected exit codes. Use stubs/mocks to avoid mutating real hosts or container states.

---

## Technical Guidelines for Code Generation

### A. Backend Testing (`pytest`)

* **Seeding & Fixtures:** Always use isolated database transactions per test. Use explicit factories or seed models that preserve relational integrity between Works, Expressions, Manifestations, and Items.
* **Strict Validation:** Assert response status codes, specific payload structures, and headers (e.g., provenance or taxonomy headers). Do not use broad exception handling.
* **SQL Pagination & Query Limits:** Explicitly test list endpoints with pagination limits and offsets, asserting that database-level `LIMIT`/`OFFSET` queries are executed rather than in-memory heap slicing.
* **Migration DAG Verification:** Verify that the Alembic migration history remains linear with exactly one head (`len(ScriptDirectory.get_heads()) == 1`).

### B. Frontend UI Testing (`Vitest` + RTL)

* **Top-Level Import Hygiene:** Never use dynamic `await import(...)` inside individual test bodies for mocked or hoisted packages (e.g. `sonner`, `next/navigation`); declare all imports at top-level module scope to prevent race conditions with Vitest mock hoisting.
* **Interactive Control Wiring:** Assert that every clickable button or menu action triggers an expected event handler or API call; verify that deferred features render disabled controls with clear tooltips (e.g. "Coming in v0.8.0").
* **Accessible Queries:** Prioritize accessible locator strategies exactly as a user experiences the screen. Use `screen.getByRole`, `screen.getByLabelText`, and `screen.getByText`. Avoid querying raw CSS classes or test IDs unless an element has no semantic role.
* **User Actions:** Always employ `@testing-library/user-event` instead of raw `.click()` triggers to simulate genuine keystrokes and focus switches.

### C. End-to-End Workflow Testing (`Playwright`)

* **Accessible Selectors:** Use accessible role definitions (e.g., `page.getByRole('tab', { name: 'Expressions' })`).
* **URL Hydration & State Checks:** Explicitly assert navigation updates, query parameters preservation (e.g., checking if `?genres=Fiction&view=works` hydrates correctly), and prevent premature loop conditions.
* **Boundary Verification:** Securely verify personal workspace bounds vs. global graph tracking. Assert that global catalog layers (Manifestations, Expressions, Works) expose matching assets symmetrically, while local inventory layers (`view=items` or personal collections) strictly return an empty state if the user does not personally own a matching physical/digital copy.

---

## Operational Instructions for Agents

1. **Pre-emptive Formatting:** Before executing tests or evaluating linters, format your generated files using `.venv/bin/python -m black` for Python or Prettier for frontend files to eliminate layout friction.
2. **Zero-Silencing Policy:** Never introduce type/lint suppression tags (`# type: ignore`, `# noqa`, `/* eslint-disable */`, or `disable=too-many-statements`) to cover up complex test code. Refactor code block components or factor out dense fixtures into support modules.
3. **Targeted Verification Loop:** If an optimization command fails, invoke only the direct sub-task path (e.g., `.venv/bin/pytest tests/test_api.py -k test_target`) to isolate errors efficiently before triggering full suites.

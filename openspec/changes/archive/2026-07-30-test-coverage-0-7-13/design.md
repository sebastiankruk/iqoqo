## Context

The iQoQo system received major updates in the 0.7.13 release, specifically enabling standard users to request a `change_type` for FRBR entities, and improving format badge logic to support labels like `Movie` and `Film` rather than hardcoding `Book`.
However, while these features are backend tested, the frontend components and End-to-End user workflows do not have associated automated tests. Ensuring test coverage across layers is critical to prevent regressions.

## Goals / Non-Goals

**Goals:**

- Design a Vitest component testing strategy for `escalation-trigger.tsx`, `escalation-queue.tsx`, and `item-header.tsx`.
- Design a Playwright E2E test to cover the `change_type` workflow, simulating both a standard user and a custodian.

**Non-Goals:**

- This change will NOT alter existing application code or business logic; it strictly adds automated tests.
- This change will NOT backfill tests for backend code, which was already covered in 0.7.13.

## Decisions

### 1. Mocking the API for Vitest

- *Decision*: We will use Vitest's mocking capabilities or MSW (if configured) to intercept the dispatch of the `change_type` payload in component tests.
- *Rationale*: This guarantees isolation, preventing UI tests from failing due to backend API instability.

### 2. Playwright Workflow Test File

- *Decision*: We will create a new dedicated spec `frbr_type_change_workflow.spec.ts`.
- *Rationale*: Although `escalation_workflow.spec.ts` exists, the `change_type` workflow specifically involves verifying the upward cascade from Manifestation to Expression/Work. Creating a new test file isolates the FRBR-specific data setup from general escalation testing.

## Risks / Trade-offs

- **[Risk] Complex State Hydration:** Simulating the upward propagation of a type change in E2E tests may require complex data seeding.
  → **Mitigation:** Rely on isolated fixture seeding inside the Playwright tests that provisions exactly one Manifestation, Expression, and Work to keep tests fast and reliable.

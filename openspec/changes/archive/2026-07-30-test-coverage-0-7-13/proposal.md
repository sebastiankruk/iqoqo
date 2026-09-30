## Why

The 0.7.13 release introduced several major features, including Data Normalization, Core Bug Fixes, Data Correction, Batch Watermarking Automation, and most notably the FRBR Type Change UI (`frbr-ui-type-change`). While the backend test suite for these changes is robust, the frontend component layer (Vitest) and End-to-End workflow layer (Playwright) lack coverage for the `change_type` User Request logic and the item-header badge format fallback logic. We need to add comprehensive test coverage to ensure the stability of the UI and E2E flows when changing manifestation types and validating format fallbacks.

## What Changes

- Add Vitest component test for `escalation-trigger.tsx` to validate that selecting "Entity Type" triggers a `change_type` escalation payload.
- Add Vitest component test for `escalation-queue.tsx` to ensure `RequestTypeBadge` correctly renders and handles the `change_type` status.
- Add Vitest component test for `item-header.tsx` to validate that format labels (e.g., `movie`, `video`, `film`) correctly fall back to their resolved `baseLabel` instead of a hardcoded "Book".
- Add a new Playwright E2E test `frbr_type_change_workflow.spec.ts` (or append to `escalation_workflow.spec.ts`) to validate the complete user journey: a standard user requesting a type change, a Custodian approving it, and validating that the Manifestation updates while upwardly propagating to parent Work/Expression forms.

## Capabilities

### New Capabilities

- `test-coverage-0-7-13`: Comprehensive test coverage validation for release 0.7.13.

### Modified Capabilities

- `frbr-ui-type-change`: Verifying E2E integration of the FRBR type change request.

## Impact

No functional codebase behavior will be altered. This change introduces unit and E2E tests for the frontend and Playwright workflow layers, improving long-term stability and regression coverage for iqoqo features introduced in 0.7.13.

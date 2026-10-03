## 1. Frontend Component Testing (Vitest)

- [x] 1.1 Create `frontend/__tests__/components/escalation-trigger.test.tsx` and write a test to validate the "Entity Type" selection triggers the correct `change_type` escalation payload using Vitest and React Testing Library.
- [x] 1.2 Create `frontend/__tests__/components/admin/escalation-queue.test.tsx` and write a test validating the rendering of `RequestTypeBadge` when type is `change_type`.
- [x] 1.3 Create `frontend/__tests__/components/item/item-header.test.tsx` and write a test validating that formats like `movie`, `film`, and `video` render the correct format label and do not fall back to `Book`.

## 2. End-to-End Testing (Playwright)

- [x] 2.1 Create `frontend/__tests__/e2e/frbr_type_change_workflow.spec.ts`.
- [x] 2.2 Add E2E setup mocking a single `Manifestation` (e.g., initially a Book) connected to an `Expression` and `Work`.
- [x] 2.3 Write E2E test verifying a standard user submitting a `change_type` request to change the Manifestation to a `Movie`.
- [x] 2.4 Write E2E test verifying a Custodian accepting the `change_type` request, and assert that the parent `Expression` and `Work` adapt correctly in the API response or UI representation.

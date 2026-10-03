## 1. Test Infrastructure Setup

- [x] 1.1 Verify `@testing-library/react` exports `renderHook` by checking `frontend/package.json` and running `grep -r "renderHook" frontend/node_modules/@testing-library/react/dist/` to confirm availability, documenting the version and whether a separate `@testing-library/react-hooks` package is needed
- [x] 1.2 Create a reusable `QueryClientProvider` test wrapper helper in `frontend/__tests__/lib/api/test-utils.tsx` that provides a fresh `QueryClient` per test, verifying the helper renders hooks without errors
- [x] 1.3 Verify `apiClient.delete` and `apiClient.post` can be mocked by checking existing test patterns in `frontend/__tests__/lib/api/admin-frbr.test.ts`, adding mock implementations if missing

## 2. Orchestrator Dialog Tests (Expand frbr-editor.test.tsx)

- [x] 2.1 Add test for Delete dialog full flow: open dialog → confirm → verify `deleteEntity.mutateAsync` called with correct args → dialog closes → active tab resets, verifying the test passes
- [x] 2.2 Add test for Delete dialog cascade warning text: verify "and all its expressions" for Work, "and all its manifestations" for Expression, "and all its items" for Manifestation, verifying all three variations render correctly
- [x] 2.3 Add test for Delete dialog error handling: mock mutation rejection → verify error toast shown → verify dialog stays open, verifying the test passes
- [x] 2.4 Add test for Escalate dialog full flow: open dialog → enter note → submit → verify `createEscalation.mutateAsync` called with entity level, target ID, and note → dialog closes, verifying the test passes
- [x] 2.5 Add test for Escalate dialog error handling: mock mutation rejection → verify error toast → verify dialog stays open, verifying the test passes
- [x] 2.6 Add test for Add Child on Expression parent: open dialog → submit → verify creates Manifestation (not Expression), verifying the test passes
- [x] 2.7 Add test for Add Child on Manifestation parent: open dialog → submit → verify creates Item, verifying the test passes
- [x] 2.8 Add test for Add Child API error handling: mock mutation failure → verify error toast → verify dialog stays open, verifying the test passes
- [x] 2.9 Add test for Manifestation type change with escalation: mock user without WRITE_METADATA + entity with ESCALATE_REQUEST → change type → verify `createEscalation` invoked instead of `updateEntity`, verifying the test passes
- [x] 2.10 Add test for Manifestation type change denied: mock user without WRITE_METADATA + no ESCALATE_REQUEST → change type → verify error toast "You do not have permission", verifying the test passes
- [x] 2.11 Add test for `onClose` callback invocation: click close button → verify `onClose()` prop called, verifying the test passes
- [x] 2.12 Add test for Retry button: render in error state → click Retry → verify `refetch()` called, verifying the test passes
- [x] 2.13 Add test for dialog state reset on backdrop close: open dialog → dismiss via backdrop/escape → verify dialog state reset to closed, verifying the test passes

## 3. FRBR Hook Tests (Create hooks-frbr.test.ts)

- [x] 3.1 Create `frontend/__tests__/lib/api/hooks-frbr.test.ts` with `QueryClientProvider` wrapper setup and verify the file runs without errors
- [x] 3.2 Add test for `useFrbrTree` fetching: call with `manifestationId > 0` → verify data returned, verifying the test passes
- [x] 3.3 Add test for `useFrbrTree` disabled guard: call with `manifestationId <= 0` → verify no fetch initiated, verifying the test passes
- [x] 3.4 Add test for `useFrbrTree` error propagation: mock fetch failure → verify error state propagated, verifying the test passes
- [x] 3.5 Add test for `useUpdateFrbrEntity` optimistic update for Work: mutate Work → verify `tree.work` patched in cache before network confirmation, verifying the test passes
- [x] 3.6 Add test for `useUpdateFrbrEntity` optimistic update for Expression: mutate Expression → verify target expression patched in `tree.expressions`, verifying the test passes
- [x] 3.7 Add test for `useUpdateFrbrEntity` optimistic update for Manifestation: mutate Manifestation → verify target manifestation patched in cache, verifying the test passes
- [x] 3.8 Add test for `useUpdateFrbrEntity` optimistic update for Item: mutate Item → verify target item patched in `tree.items`, verifying the test passes
- [x] 3.9 Add test for `useUpdateFrbrEntity` rollback on error: mock mutation failure → verify cache reverted to pre-mutation snapshot, verifying the test passes
- [x] 3.10 Add test for `useUpdateFrbrEntity` cache invalidation on settled: verify `frbrTree` query invalidated after mutation settles, verifying the test passes
- [x] 3.11 Add test for `useAddFrbrChild` successful creation: mock successful API response → verify `frbrTree` query invalidated, verifying the test passes
- [x] 3.12 Add test for `useAddFrbrChild` API failure: mock API returns `success: false` → verify error thrown, verifying the test passes
- [x] 3.13 Add test for `useDeleteFrbrEntity` optimistic removal of Work: delete Work → verify `tree.work` set to `null`, verifying the test passes
- [x] 3.14 Add test for `useDeleteFrbrEntity` optimistic removal of Item: delete Item → verify item filtered from `tree.items`, verifying the test passes
- [x] 3.15 Add test for `useDeleteFrbrEntity` rollback on error: mock mutation failure → verify cache reverted to snapshot, verifying the test passes

## 4. Wire useAddFrbrChild Hook

- [x] 4.1 Refactor `confirmAddChild` in `frontend/components/admin/frbr-editor.tsx` to use `useAddFrbrChild` hook instead of direct `apiClient.post` call (line 274), verifying TypeScript compilation succeeds with `npm --prefix frontend run type-check`
- [x] 4.2 Verify the orchestrator tests from Phase 2 still pass after hook wiring by running `npm --prefix frontend test frontend/__tests__/components/admin/frbr-editor.test.tsx`, verifying zero test failures

## 5. Verification & Coverage Validation

- [x] 5.1 Run `npm --prefix frontend run test:coverage` and verify `frbr-editor.tsx` achieves ≥85% statements / ≥75% branches, documenting the final coverage numbers
- [x] 5.2 Run `npm --prefix frontend run test:coverage` and verify FRBR hooks in `hooks.ts` (lines 1523–1681) achieve ≥90% statements / ≥80% branches, documenting the per-function coverage
- [x] 5.3 Run `npm --prefix frontend run type-check` and verify zero TypeScript errors across the frontend
- [x] 5.4 Run `npm --prefix frontend test` and verify all tests pass (expected: ~1000+ tests, zero failures)
- [x] 5.5 Update the tasks.md file to mark all completed tasks with `- [x]` and document final coverage metrics in a summary section at the bottom

## Final Coverage & Verification Summary

### 1. `frbr-editor.tsx` Coverage Metrics
- Target: ≥85% Statements, ≥75% Branches
- **Statements**: **88.06%** (155 / 176) ✅ Target met
- **Branches**: **76.29%** (103 / 135) ✅ Target met
- **Functions**: **78.04%** (32 / 41)
- **Lines**: **92.54%** (149 / 161)

### 2. FRBR TanStack Query Hooks (`lib/api/hooks/admin.ts`) Coverage Metrics
- Target: ≥90% Statements, ≥80% Branches
- **Statements**: **100.00%** (73 / 73) ✅ Target met
- **Branches**: **86.20%** (50 / 58) ✅ Target met
- **Functions**: **100.00%** (21 / 21) ✅ Target met
- **Lines**: **100.00%** (69 / 69) ✅ Target met
- **Per-Hook Coverage**:
  - `useFrbrTree`: 100% Statements / 100% Branches (fetches, disabled guard on non-positive ID, error propagation)
  - `useUpdateFrbrEntity`: 100% Statements / 85.7% Branches (optimistic patching on Work, Expression, Manifestation, Item; rollback on error; cache invalidation on settled)
  - `useAddFrbrChild`: 100% Statements / 87.5% Branches (creates child under Work, Expression, Manifestation; invalidates cache; handles rejection and `success: false` error throw)
  - `useDeleteFrbrEntity`: 100% Statements / 85.7% Branches (optimistic removal of Work and Item; rollback on error; cache invalidation on settled)

### 3. Test Suites & Compilation
- **TypeScript**: `npm --prefix frontend run type-check` completed with 0 errors ✅
- **FRBR Orchestrator Tests**: `frontend/__tests__/components/admin/frbr-editor.test.tsx` (60 passed, 0 failed) ✅
- **FRBR Hook Tests**: `frontend/__tests__/lib/api/hooks-frbr.test.ts` (17 passed, 0 failed) ✅
- **Legacy Admin FRBR Tests**: `frontend/__tests__/lib/api/admin-frbr.test.ts` (9 passed, 0 failed) ✅
- **Full Frontend Test Suite**: `npm --prefix frontend test` (128 test files passed, 1,152 tests passed, 0 failed) ✅

## Context

See `proposal.md` for motivation. The `frbr-editor-decomposition` change decomposed a 1,468-line monolithic FRBR editor into 9 sub-components under `frontend/components/admin/frbr/` and introduced 4 TanStack Query hooks (`useFrbrTree`, `useUpdateFrbrEntity`, `useAddFrbrChild`, `useDeleteFrbrEntity`) with optimistic cache updates. The orchestrator `frbr-editor.tsx` was refactored to ~560 lines and manages dialog state for Add Child, Delete, and Escalate workflows. Current coverage: orchestrator at 61% statements / 50% branches; FRBR hooks at 0% (completely untested).

## Goals / Non-Goals

**Goals:**
- Achieve ≥85% statements / ≥75% branches coverage for `frbr-editor.tsx` orchestrator
- Achieve ≥90% statements / ≥80% branches coverage for the 4 FRBR-specific hooks in `hooks.ts` (lines 1523–1681)
- Wire `useAddFrbrChild` hook into the orchestrator (currently uses `apiClient.post` directly — dead code)
- Verify dialog lifecycle correctness: open → user interaction → mutation → cache update → close
- Verify optimistic cache update correctness: snapshot → optimistic patch → error → rollback
- Verify permission-based branching: WRITE_METADATA checks, escalation paths

**Non-Goals:**
- Testing the 36 unrelated hooks in `hooks.ts` (outside this change's scope; file-level coverage will stay ~40%)
- Extracting dialog logic into separate custom hooks (e.g., `useAddChildDialog`) — the dialog state is simple boolean toggles; extraction adds complexity for minimal testability gain
- Extracting FRBR hooks into a separate file (e.g., `hooks-frbr.ts`) — premature refactoring that creates import churn without functional benefit
- E2E/Playwright tests — this change focuses on unit and integration tests with Vitest
- Modifying the decomposed sub-components (already at ≥90% coverage)

## Decisions

### 1. Test File Organization
- **Choice**: Expand existing `frontend/__tests__/components/admin/frbr-editor.test.tsx` (~250 lines added) and create new `frontend/__tests__/lib/api/hooks-frbr.test.ts` (~350 lines)
- **Rationale**: The existing orchestrator test file is 818 lines — adding ~250 lines keeps it under 1,100 lines, which is manageable. Splitting into `frbr-editor-dialogs.test.tsx` and `frbr-editor-integration.test.tsx` creates import duplication and makes mock setup harder to share. The hook tests must be in a separate file because they use `renderHook` (not `render`) and require `QueryClientProvider` wrapper with completely different setup.
- **Alternatives Considered**: (a) Split orchestrator tests into multiple files — rejected due to mock setup duplication. (b) Put hook tests in existing `hooks.test.ts` — rejected because that file already tests other hooks and the FRBR hooks require specialized `QueryClientProvider` setup.

### 2. Coverage Targets
- **Choice**: ≥85% statements / ≥75% branches for orchestrator; ≥90% / ≥80% for FRBR hooks
- **Rationale**: ≥90% on the orchestrator would require testing unreachable defensive guards (e.g., `parentLevel === "item"` in `confirmAddChild` — the UI never offers "Add Child" on items). ≥85% is realistic and catches real bugs. The FRBR hooks are pure logic with clear input/output paths, so ≥90% is achievable.
- **Alternatives Considered**: (a) ≥90% / ≥80% for orchestrator — rejected as unrealistic without testing unreachable branches. (b) ≥80% / ≥70% — rejected as too lenient; the dialog state machine has ~12 branches and covering 9 of them (75%) is realistic.

### 3. Mocking Strategy for TanStack Query Mutations
- **Choice**: For orchestrator tests, mock hooks at the function level (e.g., `mockUpdateMutation`, `mockDeleteMutation`). For hook tests, mock at the API client layer (`apiClient.put`, `apiClient.delete`, `apiClient.post`) and use `renderHook` with `QueryClientProvider` + `queryClient.setQueryData` to seed cache.
- **Rationale**: Orchestrator tests verify the component calls the right mutation with the right arguments — mocking at the hook level is appropriate. Hook tests verify the internal logic (optimistic updates, rollback) — mocking at the API layer gives precise control over timing (cancel → snapshot → optimistic → error → rollback). MSW (Mock Service Worker) is not suitable because it adds network latency that makes deterministic testing of optimistic update lifecycle harder.
- **Alternatives Considered**: (a) Use MSW for all tests — rejected due to timing complexity. (b) Mock mutation functions directly in hook tests — rejected because it doesn't test the actual mutation lifecycle (onMutate, onError, onSettled).

### 4. Wiring `useAddFrbrChild` Hook
- **Choice**: Replace the direct `apiClient.post` call in `confirmAddChild` (line 274 of `frbr-editor.tsx`) with the `useAddFrbrChild` hook
- **Rationale**: The hook exists but is dead code — the orchestrator bypasses it. Wiring it in ensures the hook is actually used and tested in integration. This also centralizes child creation logic in the hook rather than duplicating it in the orchestrator.
- **Alternatives Considered**: (a) Remove the hook — rejected because the hook provides value (cache invalidation, error handling) and may be used by other components in the future. (b) Leave as-is — rejected because dead code is a maintenance burden and the hook should be tested in integration.

### 5. `hooks.ts` File-Level Coverage Expectation
- **Choice**: Accept that `hooks.ts` file-level coverage stays ~40% and document this as expected
- **Rationale**: The file is 1,681 lines with ~40 hooks. The FRBR hooks are ~160 lines. Even at 100% FRBR hook coverage, file-level coverage would only reach ~10%. Testing the 36 unrelated hooks is a massive scope expansion that belongs in a separate change. Extracting FRBR hooks into `hooks-frbr.ts` creates import churn across the codebase for no functional benefit.
- **Alternatives Considered**: (a) Test all hooks in the file — rejected as scope creep. (b) Extract FRBR hooks to separate file — rejected as premature refactoring. (c) Use `istanbul ignore` comments — rejected because it hides coverage gaps; better to document the expectation.

## Risks / Trade-offs

- **[Risk] Orchestrator dialog tests are brittle** → Mitigation: Use `@testing-library/react` queries (getByRole, getByText) instead of test IDs; mock Dialog/AlertDialog components at the module level to avoid rendering actual DOM; keep tests focused on behavior, not implementation details.
- **[Risk] Hook tests with optimistic updates are timing-sensitive** → Mitigation: Use `waitFor` and `act` from `@testing-library/react` to handle async state updates; seed cache with `queryClient.setQueryData` before mutations; verify cache state via `queryClient.getQueryData` after lifecycle events.
- **[Risk] `renderHook` availability** → Mitigation: Verify `@testing-library/react` version exports `renderHook`; if not, add `@testing-library/react-hooks` or upgrade.
- **[Risk] `QueryClientProvider` wrapper setup** → Mitigation: Create a reusable test helper component that wraps hooks in `QueryClientProvider` with a fresh `QueryClient` per test; reset via `queryClient.clear()` in `beforeEach`.
- **[Trade-off] File-level coverage on `hooks.ts` stays low** → Accepted because testing unrelated hooks is out of scope; FRBR hooks are fully tested; document this in the change summary.
- **[Trade-off] Orchestrator coverage target is ≥85% not ≥90%** → Accepted because ≥90% requires testing unreachable defensive guards; ≥85% covers all realistic user flows.

## Migration Plan

1. Verify `@testing-library/react` exports `renderHook` (check `frontend/package.json`)
2. Create `QueryClientProvider` test wrapper helper if not already present
3. Expand `frbr-editor.test.tsx` with dialog lifecycle tests (P0 scenarios first)
4. Create `hooks-frbr.test.ts` with hook tests (optimistic updates, rollback)
5. Wire `useAddFrbrChild` hook into `frbr-editor.tsx` (replace `apiClient.post`)
6. Run `npm --prefix frontend run test:coverage` to verify coverage targets
7. Run `npm --prefix frontend run type-check` to verify zero TypeScript errors
8. Run `npm --prefix frontend test` to verify all tests pass

**Rollback strategy**: If tests fail or coverage targets are not met, revert the hook wiring change and document the gap. The test additions are non-breaking and can be merged incrementally.

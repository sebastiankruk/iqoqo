## Why

The `frbr-editor-decomposition` change successfully decomposed the monolithic FRBR editor into modular sub-components and implemented TanStack Query hooks with optimistic cache updates. However, test coverage for the orchestrator component (`frbr-editor.tsx`) and the new FRBR-specific hooks remains insufficient: the orchestrator sits at 61% statements / 50% branches (missing dialog lifecycle tests for Delete, Escalate, and multi-tier Add Child flows), and the FRBR hooks in `hooks.ts` (optimistic updates, rollback, cache invalidation) are completely untested. Without these tests, regressions in dialog state management and optimistic cache synchronization risk going undetected until production.

## What Changes

- Expand `frontend/__tests__/components/admin/frbr-editor.test.tsx` with ~13 new test cases covering:
  - Delete dialog full lifecycle (open → confirm → mutation → cache eviction → parent focus shift)
  - Delete dialog error handling and cascade warning text variations
  - Escalate dialog full lifecycle (open → note input → submit → `useCreateEscalation` call)
  - Add Child for Expression parent (creates Manifestation, not Expression)
  - Add Child for Manifestation parent (creates Item)
  - Add Child API error handling
  - Manifestation type change with escalation path (no WRITE_METADATA + has ESCALATE_REQUEST)
  - Manifestation type change denied (no WRITE_METADATA + no ESCALATE_REQUEST)
  - `onClose` callback invocation
  - Retry button behavior
  - Dialog `onOpenChange` state reset
- Create new `frontend/__tests__/lib/api/hooks-frbr.test.ts` with ~14 test cases covering:
  - `useFrbrTree`: fetching, caching, `enabled` guard, error propagation
  - `useUpdateFrbrEntity`: optimistic cache updates for all 4 entity types, rollback on error, `onSettled` invalidation
  - `useAddFrbrChild`: successful creation, `success: false` error handling
  - `useDeleteFrbrEntity`: optimistic removal for all entity types, rollback on error
- Wire `useAddFrbrChild` hook into `frbr-editor.tsx` (currently uses `apiClient.post` directly — dead code in the hook)
- Target coverage: ≥85% statements / ≥75% branches for `frbr-editor.tsx`; ≥90% / ≥80% for FRBR hooks specifically

## Capabilities

### New Capabilities
- `editor/test-coverage`: Comprehensive test coverage for the FRBR editor orchestrator dialog lifecycle, permission-based action gating, and TanStack Query hook optimistic cache synchronization with rollback.

### Modified Capabilities
<!-- None: this change adds test coverage without modifying existing spec-level behavior. The `editor/decomposition` capability from `frbr-editor-decomposition` remains unchanged; we are only verifying its implementation more thoroughly. -->

## Impact

- **Frontend Tests**: Two test files expanded/created under `frontend/__tests__/`:
  - `components/admin/frbr-editor.test.tsx` (~250 lines added)
  - `lib/api/hooks-frbr.test.ts` (~350 lines, new file)
- **Frontend Components**: `frontend/components/admin/frbr-editor.tsx` — wire `useAddFrbrChild` hook (replace direct `apiClient.post` call in `confirmAddChild`)
- **Testing Infrastructure**: Requires `renderHook` from `@testing-library/react` (verify availability) and `QueryClientProvider` wrapper for hook tests
- **Coverage Metrics**: `frbr-editor.tsx` moves from 61% → ≥85% statements; FRBR hooks in `hooks.ts` move from 0% → ≥90% (file-level coverage stays ~40% due to 36 unrelated hooks outside this change's scope — this is expected and documented)
- **No API changes**: All work is frontend test coverage and minor hook wiring
- **No database changes**: None


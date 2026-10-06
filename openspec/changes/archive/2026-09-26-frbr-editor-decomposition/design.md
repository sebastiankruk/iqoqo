## Context

See `proposal.md` for problem motivation and scope.

The current `frontend/components/admin/frbr-editor.tsx` is a monolithic file exceeding 1,460 lines. It encompasses the full FRBR hierarchy (F1 Work, F2 Expression, F3 Manifestation, F5 Item), manages state with ad-hoc `useState` hooks, and triggers complete `fetchTree()` roundtrips after every entity mutation. In addition, action buttons for "Add Child", "Escalate", and "Delete" are disabled UI stubs ("Coming in v0.8.0"), and contributor management across FRBR tiers is absent from the editing view.

This design decomposes the editor into modular domain sub-components, integrates TanStack Query with optimistic cache synchronization, and activates child creation, escalation, and deletion workflows.

## Goals / Non-Goals

**Goals:**
- Decompose `frbr-editor.tsx` into specialized sub-components under `frontend/components/admin/frbr/`:
  - `WorkEditor`
  - `ExpressionEditor`
  - `ManifestationEditor`
  - `ItemEditor`
  - `FRBRTreeView`
  - `ContributorEditor`
  - `MetaFieldsEditor`
- Refactor the root `FrbrEditor` into a lightweight orchestrator managing selected entity state and dialog coordination.
- Replace manual `useState`/`useEffect` + `fetchTree()` patterns with TanStack Query hooks (`useFrbrTree`, `useUpdateFrbrEntity`, `useAddFrbrChild`, `useDeleteFrbrEntity`).
- Implement optimistic cache updates on mutations with automatic rollback on error.
- Implement functional "Add Child" creation workflows across all FRBR tiers.
- Implement active "Escalate" (delegating to custodian escalation requests) and "Delete" (with confirmation dialogs and cache eviction) handlers.

**Non-Goals:**
- Changing underlying database schemas for FRBR entities (Work, Expression, Manifestation, Item).
- Modifying public consumer catalog pages (`/manifestation/[id]`, `/item/[id]`).
- Replacing general application UI primitives (buttons, selects, dialogs from `@/components/ui/*`).

## Decisions

### 1. Component Architecture & Directory Structure
- **Choice**: Structure decomposed components within `frontend/components/admin/frbr/`:
  ```
  frontend/components/admin/frbr/
  ├── frbr-tree-view.tsx         # Hierarchical tree navigator with entity badges
  ├── work-editor.tsx            # F1 Work editor + dynamic metadata + mechanics + series
  ├── expression-editor.tsx      # F2 Expression editor + dynamic metadata
  ├── manifestation-editor.tsx   # F3 Manifestation editor + format picker + identifiers
  ├── item-editor.tsx            # F5 Item editor + status/condition + dynamic metadata
  ├── items-manager.tsx          # Item list filtering, expansion, and multi-item management
  ├── contributor-editor.tsx     # Contributor search, role assignment, and attribution
  ├── meta-fields-editor.tsx     # Reusable dynamic metadata key-value manager
  └── types.ts                   # Sub-component prop types and form schemas
  ```
  `frontend/components/admin/frbr-editor.tsx` remains the top-level exported entry point (`FrbrEditor`), acting as orchestrator.
- **Rationale**: Keeps single-responsibility boundaries clear, minimizes file length (< 300 lines each), allows targeted testing, and isolates regression risk when editing a specific FRBR entity tier.
- **Alternatives Considered**: Keeping all sub-components in the single `frbr-editor.tsx` file. Rejected because code organization, readability, and testability would remain compromised.

### 2. TanStack Query State Management & Optimistic Cache Updates
- **Choice**: Define queries and mutations in `frontend/lib/api/hooks.ts` and `frontend/lib/api/admin.ts`:
  - Query: `queryKeys.frbrTree = (id: number) => ["admin", "frbr", "tree", id] as const`
  - Hook: `useFrbrTree(manifestationId: number)`
  - Mutation Hook: `useUpdateFrbrEntity()`
    - `onMutate`: Cancel outgoing `["admin", "frbr", "tree", manifestationId]` queries; snapshot current cache; optimistically update target entity fields in query cache; return rollback context.
    - `onError`: Revert query cache to previous snapshot and display toast error.
    - `onSettled`: Invalidate or background-refetch query to reconcile server state.
- **Rationale**: Optimistic updates eliminate UI lag and prevent full-tree re-renders on every keystroke or metadata save.
- **Alternatives Considered**: Keeping local component `useState` and polling `fetchTree()`. Rejected because it creates flash-of-loading states and sluggish form UX.

### 3. FRBRTreeView Interactive Hierarchy Navigator
- **Choice**: Create a dedicated `FRBRTreeView` rendering a left-sidebar or top-panel hierarchical tree (Work → Expression → Manifestation → Items). Each node displays:
  - Entity type badge (F1, F2, F3, F5) and title/identifier.
  - Count badges (e.g. number of items).
  - Selection state that triggers switching the active editor view.
  - Inline action menu button (Add Child, Escalate, Delete).
- **Rationale**: FRBR relationships are hierarchical; giving users a visual breadcrumb tree makes relationship navigation intuitive and reduces reliance on dropdown tabs.
- **Alternatives Considered**: Pure tab selector without visual hierarchy. Rejected because tabs hide the relational structure between Works, Expressions, Manifestations, and Items.

### 4. Contributor Attribution Integration (`ContributorEditor`)
- **Choice**: Integrate `ContributorEditor` into Work (creators), Expression (realizers/performers), and Manifestation (publishers) editors.
  - Enforces FRBR event ontology: Work contributions use creator roles (author, composer, designer); Expression contributions use realizer roles (performer, translator, narrator); Manifestation contributions use publication roles.
  - Provides typeahead contributor search and role selection.
  - Updates cache and dispatches to `/v1/admin/frbr/contributions/*` endpoints.
- **Rationale**: Attribution is essential to FRBR metadata but was entirely missing from the admin editor.
- **Alternatives Considered**: Separate standalone contributor management page. Rejected because librarians and admins need to assign contributors while editing the entity itself.

### 5. Functional "Add Child", "Escalate", and "Delete" Workflows
- **Choice**: Replace disabled stubs with active handlers:
  - **Add Child**:
    - On Work: Opens modal to create an Expression linked to `work_id`.
    - On Expression: Opens modal to create a Manifestation linked to `expression_id`.
    - On Manifestation: Opens modal to create an Item linked to `manifestation_id`.
    - Upon creation, updates query cache optimistically and selects the new child.
  - **Escalate**:
    - When user lacks `WRITE_METADATA` or requests structured modifications, opens escalation modal using `useCreateEscalation` with pre-filled target level and ID.
  - **Delete**:
    - Triggers a destructive confirmation modal (`AlertDialog`).
    - Gated by role permission checks (`WRITE_METADATA` / admin).
    - Upon confirmation, calls DELETE endpoint, evicts entity from query cache, and shifts focus to the parent entity.
- **Rationale**: Completes the feature lifecycle promised in the UI and delivers full CRUD capability to the admin editor.
- **Alternatives Considered**: Silent deletion without confirmation. Rejected because deleting FRBR parent entities or physical items carries severe data loss risks.

## Risks / Trade-offs

- **[Risk] Optimistic update cache desynchronization** → Mitigation: Use standard TanStack Query `cancelQueries` + snapshot rollback pattern; trigger `invalidateQueries` in `onSettled` to reconcile canonical server state.
- **[Risk] Complex cascading deletion of parent entities** → Mitigation: Enforce backend cascade rules and confirm destructive action via UI `AlertDialog` with explicit warning when deleting nodes with existing children.
- **[Risk] Multiple sub-components proliferating re-renders** → Mitigation: Memoize sub-components where necessary and pass targeted entity slice props instead of the whole tree.

## Migration Plan

1. Create sub-components in `frontend/components/admin/frbr/` without breaking existing imports.
2. Implement TanStack Query hooks in `frontend/lib/api/hooks.ts` with optimistic mutation logic.
3. Update backend admin endpoints for child creation and deletion if missing.
4. Refactor `frontend/components/admin/frbr-editor.tsx` to mount decomposed sub-components.
5. Update unit tests in `frontend/__tests__/components/admin/frbr-editor.test.tsx` and add unit tests for each sub-component.
6. Verify test coverage and TypeScript typecheck.

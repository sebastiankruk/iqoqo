## Why

The existing `frbr-editor.tsx` is an unwieldy 1460+ line monolithic component that mixes state fetching, tree synchronization, multiple entity forms, inline modals, and stubbed action handlers. Modifying or extending any single FRBR tier (Work, Expression, Manifestation, Item) risks regression, causes sluggish re-renders from full-tree refetches (`fetchTree()`), and blocks contributor attribution management. Decomposing the editor into dedicated, modular sub-components with optimistic TanStack Query cache mutations and active action handlers is critical for UI maintainability, responsive editing, and user experience in v0.8.1 (C8: FRBR Editor Decomposition).

## What Changes

- Decompose `frontend/components/admin/frbr-editor.tsx` into clean, modular sub-components under `frontend/components/admin/frbr/`:
  - `WorkEditor`: Focused form for FRBR Work (F1) entities, title editing, dynamic metadata, and mechanics attribution.
  - `ExpressionEditor`: Focused form for FRBR Expression (F2) entities, content type, language, kind, and dynamic metadata.
  - `ManifestationEditor`: Focused form for FRBR Manifestation (F3) entities, physical media format selection, identifiers (ISBN-13, UPC, EAN), publisher, publication date, and dynamic metadata.
  - `ItemEditor`: Focused form for FRBR Item (F5) entities, custody status, physical condition, and dynamic metadata.
  - `FRBRTreeView`: Visual hierarchical navigator and tree selector displaying the Work → Expression → Manifestation → Items structure with quick selection and status badges.
  - `ContributorEditor`: Dedicated attribution interface for managing creators (Work level), realizers/performers (Expression level), and publishers/manufacturers (Manifestation level) using role vocabularies.
- Replace manual `fetchTree()` waterfall refetches with optimistic TanStack Query cache updates and query invalidation using dedicated query keys (e.g., `["frbr", "tree", manifestationId]`).
- Implement and wire functional "Add Child" action handlers:
  - Work: Add Child creates/associates Expression (F2).
  - Expression: Add Child creates/associates Manifestation (F3).
  - Manifestation: Add Child creates an Item (F5).
- Wire functional "Escalate" and "Delete" action handlers across all entity tiers with confirmation dialogues and permission guardrails.

## Capabilities

### New Capabilities
- `editor/decomposition`: Modular sub-component architecture for the FRBR Editor hierarchy (`WorkEditor`, `ExpressionEditor`, `ManifestationEditor`, `ItemEditor`, `FRBRTreeView`, `ContributorEditor`), optimistic TanStack Query cache updates, and active handlers for child creation, escalation, and deletion.

### Modified Capabilities
<!-- None: existing core FRBR ontology boundaries remain intact; this introduces the decomposed admin editing interface and reactive query state management -->

## Impact

- **Frontend Components**: `frontend/components/admin/frbr-editor.tsx` refactored as a lightweight container orchestrating decomposed sub-components in `frontend/components/admin/frbr/`.
- **State Management**: Migration from component-local `useState`/`useEffect` + manual `getFrbrTree` roundtrips to TanStack Query hooks (`useFrbrTree`, `useUpdateFrbrEntity`, `useAddFrbrChild`, `useDeleteFrbrEntity`) with optimistic cache rollback.
- **APIs & Hooks**: Integration with admin FRBR entity mutations and escalation endpoints (`/v1/admin/frbr/*` and `/v1/escalations`).
- **Testing**: Dedicated unit and integration tests for each individual editor component and tree view navigator.

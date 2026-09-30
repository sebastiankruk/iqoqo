## 1. TanStack Query Hooks & State Management

- [x] 1.1 Add `queryKeys.frbrTree` and implement `useFrbrTree` hook in `frontend/lib/api/hooks.ts` with typed `FrbrTree` response, verifying fetching behavior with unit tests in `frontend/__tests__/lib/api/hooks.test.ts`
- [x] 1.2 Implement `useUpdateFrbrEntity` mutation hook with optimistic cache updates, error rollback, and automatic query cache reconciliation, verifying optimistic rollback with mock query client tests
- [x] 1.3 Implement `useAddFrbrChild` and `useDeleteFrbrEntity` mutation hooks in `frontend/lib/api/hooks.ts` supporting Work, Expression, Manifestation, and Item lifecycle actions, verifying mutation behavior with tests

## 2. Decomposed FRBR Editor Sub-Components

- [x] 2.1 Create `MetaFieldsEditor` and `EditableKeyField` in `frontend/components/admin/frbr/meta-fields-editor.tsx` for dynamic metadata management, verifying rendering and key-value editing with component unit tests
- [x] 2.2 Create `WorkEditor` in `frontend/components/admin/frbr/work-editor.tsx` integrating title editing, dynamic metadata, board game mechanics, series parts management, and action toolbars, verifying component rendering and submission in test
- [x] 2.3 Create `ExpressionEditor` in `frontend/components/admin/frbr/expression-editor.tsx` supporting content type selection, language, expression kind, dynamic metadata, and action toolbars, verifying component behavior with tests
- [x] 2.4 Create `ManifestationEditor` in `frontend/components/admin/frbr/manifestation-editor.tsx` supporting media hierarchy selection, ISBN-13/UPC/EAN identifiers, publisher, publication date, and dynamic metadata, verifying with component tests
- [x] 2.5 Create `ItemEditor` and `ItemsManager` in `frontend/components/admin/frbr/item-editor.tsx` and `items-manager.tsx` supporting status/condition editing, owner filters, item expansion, and dynamic metadata, verifying filter and update behavior in tests

## 3. Visual Tree Navigation & Contributor Editor

- [x] 3.1 Implement `FRBRTreeView` in `frontend/components/admin/frbr/frbr-tree-view.tsx` with hierarchical node rendering (Work → Expression → Manifestation → Items), selection indicators, and format/count badges, verifying tree navigation and node selection in component tests
- [x] 3.2 Implement `ContributorEditor` in `frontend/components/admin/frbr/contributor-editor.tsx` with role-aware contributor lookup and attribution management for Works, Expressions, and Manifestations, verifying contributor addition and deletion with tests

## 4. Root Editor Orchestration & Action Handlers

- [x] 4.1 Refactor `FrbrEditor` in `frontend/components/admin/frbr-editor.tsx` to act as an orchestrator mounting `FRBRTreeView`, active entity editors, and dialog handlers while replacing legacy `fetchTree()` calls with TanStack Query hooks, verifying editor orchestration with integration tests
- [x] 4.2 Wire functional "Add Child" creation dialogs and handlers across Work, Expression, and Manifestation tiers, verifying child entity creation and tree state updates
- [x] 4.3 Wire functional "Escalate" dialogs (using `useCreateEscalation`) and "Delete" confirmation modals across all FRBR entity tiers with permission checks, verifying action triggers and query cache eviction

## 5. Verification & Regression Testing

- [x] 5.1 Add integration tests covering end-to-end editing, optimistic cache synchronization, and hierarchy navigation in `frontend/__tests__/components/admin/frbr-editor.test.tsx`
- [x] 5.2 Execute TypeScript typecheck and full test suite via `npm --prefix frontend run typecheck && npm --prefix frontend test` to verify zero regressions across the frontend

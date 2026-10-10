## 1. Component Updates

- [x] 1.1 Update `frontend/components/collection/item-card.tsx` (grid and horizontal variants) to render Work and Expression navigation pills with stopPropagation handlers; verify pills render when work/expression data exists
- [x] 1.2 Update `frontend/components/item/item-header.tsx` with hierarchical FRBR tier breadcrumb links navigating to `/work/[id]` and `/expression/[id]`; verify breadcrumbs in item detail view

## 2. Testing & Verification

- [x] 2.1 Add Vitest tests in `frontend/__tests__/components/collection/item-card.test.tsx` verifying Work and Expression pill clicks invoke router push to expected URLs without triggering card link
- [x] 2.2 Verify DOM tree contains zero nested anchor tags (`a a`) in collection views

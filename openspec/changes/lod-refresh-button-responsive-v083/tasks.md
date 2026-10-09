## 1. Responsive Button Layout in SemanticLinks

- [x] 1.1 Update `frontend/components/manifestation/semantic-links.tsx` CardHeader layout to responsive wrapping flex container (`flex-col sm:flex-row sm:items-center justify-between gap-3`), ensuring the scan button remains contained on narrow viewports without clipping or overflowing the card frame.
- [x] 1.2 Update `frontend/__tests__/components/manifestation/semantic-links.test.tsx` to verify responsive classes and button title accessibility.

## 2. Mount Semantic Links in Item Detail View

- [x] 2.1 Import and render `SemanticLinks` within `DetailsTab` in `frontend/components/item/item-tabs.tsx` when `item.manifestation_id` is present, passing appropriate edit permissions.
- [x] 2.2 Add unit test in `frontend/__tests__/components/item/item-tabs.test.tsx` (or dedicated test) confirming `SemanticLinks` is rendered with the item's manifestation ID.

## 3. Verification

- [x] 3.1 Run frontend test suite (`IQOQO_AI_MODE=1 npm --prefix frontend run test`) and type check (`npm --prefix frontend run type-check`) to verify zero regressions.

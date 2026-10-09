## 1. Backend Serialization and Payload Enrichment

- [ ] 1.1 Verify and enrich collection and item endpoint responses to include `work_id`, `work_title`, and `expression_id`; verify with unit tests in `tests/test_collection.py`.
- [ ] 1.2 Update frontend TypeScript types in `frontend/types/frbr.ts` to include optional `work_id` and `expression_id` on collection items.

## 2. Frontend Collection and Item View Enhancements

- [ ] 2.1 Add parent Work navigation link / badge on collection item cards in `frontend/components/collection/`; verify cards without work gracefully hide the link.
- [ ] 2.2 Add full FRBR hierarchy breadcrumbs to the Item detail header in `frontend/components/item/item-header.tsx`.
- [ ] 2.3 Write Vitest unit tests in `frontend/__tests__/components/collection/` and `frontend/__tests__/components/item/` to verify Work and Expression links render and route correctly.

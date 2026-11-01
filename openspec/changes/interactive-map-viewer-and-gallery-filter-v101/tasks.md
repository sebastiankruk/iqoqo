## 1. Interactive `<MapViewerModal />` & Detail Page Integration (`frontend/`)

- [ ] 1.1 Create `frontend/components/item/map-viewer-modal.tsx` supporting zoom (`1x`–`5x`), drag/touch pan, 90-degree rotation, view reset, and switching between multiple attached maps.
- [ ] 1.2 Integrate `<MapViewerModal />` and map upload/attachment controls into `frontend/components/item/` and `frontend/components/manifestation/`, plus `map_insert_present` toggle in `edit-item-dialog.tsx`.
- [ ] 1.3 Add `has_map` filter support to `app/api/filters.py` / `app/core/search_service.py` and expose the `"Has Map"` facet in `frontend/components/collection/sidebar-filters.tsx` and `filter-bar.tsx`.
- [ ] 1.4 Add `en.json` and `pl.json` (sentence-case Polish) translations for all map viewer and facet labels.

## 2. Verification & Tests

- [ ] 2.1 Author component unit tests in `frontend/__tests__/components/item/map-viewer-modal.test.tsx`.
- [ ] 2.2 Author Playwright E2E test `frontend/__tests__/e2e/maps_workflow.spec.ts` verifying map attachment upload, pan/zoom modal interaction, and `"Has Map"` collection filtering.
- [ ] 2.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.

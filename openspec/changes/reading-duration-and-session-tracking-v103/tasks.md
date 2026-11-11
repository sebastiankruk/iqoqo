## 1. Backend FRBR Item Reading Session & Duration API (`app/`)

- [ ] 1.1 Add `ReadingSessionCreateSchema` (`duration_minutes` `1..1440`, optional `pages_read`, `note`) in `app/schemas/items.py` and implement `POST /api/items/<int:item_id>/reading-sessions` in `app/api/items.py` enforcing item ownership (`Item.owner_id == g.user_id`) and updating `Item.meta["reading_sessions"]` and `total_reading_minutes`.
- [ ] 1.2 Include `reading_duration_summary` (`total_minutes`, `sessions_count`, `started_at`, `finished_at`, `elapsed_days` computed from `ReadingTransition`) on `GET /api/items/<int:item_id>` and anonymized SQL aggregate `average_reading_minutes` on `GET /api/manifestations/<int:manifestation_id>`.

## 2. Frontend Reading Duration Card (`frontend/`)

- [ ] 2.1 Create `frontend/components/item/reading-duration-card.tsx` and wire it into `frontend/components/item/item-sidebar.tsx` for owned `text` items with quick-log presets (`+15m`, `+30m`, `+1h`, custom) and `en.json` / `pl.json` translations.

## 3. Verification & Test Suite

- [ ] 3.1 Author backend tests in `tests/test_reading_duration.py` and frontend tests in `frontend/__tests__/components/item/reading-duration-card.test.tsx`, and run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`.

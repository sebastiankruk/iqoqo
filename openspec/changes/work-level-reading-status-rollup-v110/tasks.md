## 1. Backend Work Reading Rollup Service & Endpoints

- [ ] 1.1 Implement batched `GROUP BY` helper `compute_work_reading_rollup(user_id, work_ids)` in `app/core/frbr_service.py` with precedence (`completed > in_progress > intent > dnf`), strict `Item.owner_id == user_id` scoping (including owner's `private` items), and zero N+1 queries; add unit tests in `tests/test_work_reading_rollup.py`
- [ ] 1.2 Wire `work_reading_status` and `completed_manifestation_ids` into `GET /api/works/<int:work_id>`, `GET /api/works/shelf` (including SQL `work_read_status` filter), and `GET /api/manifestations/<int:manifestation_id>` (`app/api/works.py`, `app/api/manifestations.py`), ensuring `null` when unauthenticated; document in `app/api/docs.py` and verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_work_reading_rollup.py tests/test_openapi_spec.py`

## 2. Frontend Work & Manifestation Badges

- [ ] 2.1 Extend `Work` and `Manifestation` TypeScript interfaces in `frontend/types/frbr.ts`, render localized `"Read"` / `"Read (another edition)"` / `"Currently Reading"` badges in `frontend/components/work/work-detail-client.tsx` and `frontend/components/manifestation/manifestation-detail-client.tsx` (with EN/PL keys in `frontend/messages/en.json` and `frontend/messages/pl.json`), and add Vitest tests (`cd frontend && npx vitest run __tests__/components/manifestation/ __tests__/components/work/`)

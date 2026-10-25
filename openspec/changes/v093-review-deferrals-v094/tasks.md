## 1. BGG2 Package & Backoff Hardening + Status Script Polish

- [ ] 1.1 Update `requirements.txt` and `pyproject.toml` from `boardgamegeek>=0.13.0` to `boardgamegeek2>=1.3`, cap `Retry-After` delay in `BGGBackoffAdapter.send` (`app/utils/bgg.py`) to `min(float(retry_after), 10.0)`, and set `retries=0` on `BoardGameGeek(...)` in `get_bgg_client()` so retries are handled solely by `BGGBackoffAdapter`
- [ ] 1.2 In `scripts/iqoqo-status.sh`, pass `IQOQO_ROOT` and `IGDB_CLIENT_ID` via environment variables and read `os.environ` inside `python3 -c` blocks instead of interpolating shell strings; update `tests/test_bgg2_strategy.py`

## 2. Celery FTS Debounce Coalescing & Work Re-index

- [ ] 2.1 In `app/core/tasks.py`, add a `threading.Lock` around `_in_memory_fts_queue`, gate `batch_fts_reindex.apply_async` on a Redis `SET iqoqo:fts_reindex_scheduled 1 NX EX <countdown>` debounce key (cleared when `batch_fts_reindex` drains the queue), and touch `Work` FTS metadata in `batch_fts_reindex`; update `tests/test_async_fts_transitions.py`

## 3. OpenAPI 3.1 Schema Accuracy & Librarian Gem Sync

- [ ] 3.1 In `app/api/decorators.py` and `app/api/docs.py`, set `decorated._requires_auth = True` on `@require_auth`, `@admin_required`, and `@admin_or_custodian_required`, update `User.id`, `Item.owner_id`, and `Notification.recipient_id` schemas to `{"type": "string", "format": "uuid"}`, update `PersonalAccessToken` schema to use `is_active` and `revoked_at`, and expand `Expression.content_type` enum; update `tests/test_openapi_contract_completeness.py`
- [ ] 3.2 Update `docs/gems/iqoqo-librarian-gem.md` to use `/api/scanner/preview/{barcode}` and align documented PAT scopes with wishlist/catalog capabilities

## 4. Bilingual Localization for `TotpSetup` & `PatManagement`

- [ ] 4.1 Wire `useTranslations("Profile")` into `frontend/components/profile/totp-setup.tsx` and `frontend/components/profile/pat-management.tsx` and add complete English and Polish translation keys in `frontend/messages/en.json` and `frontend/messages/pl.json`; update `frontend/__tests__/components/profile/pat-and-totp.test.tsx`

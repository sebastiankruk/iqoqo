## 1. BGG2 Package & Backoff Hardening + Status Script Polish

- [ ] 1.1 Update `requirements.txt` and `pyproject.toml` from `boardgamegeek>=0.13.0` to `boardgamegeek2>=1.3`, cap `Retry-After` delay in `BGGBackoffAdapter.send` (`app/utils/bgg.py`) to `min(float(retry_after), 10.0)`, and set `retries=0` on `BoardGameGeek(...)` in `get_bgg_client()` so retries are handled solely by `BGGBackoffAdapter`
- [ ] 1.2 In `scripts/iqoqo-status.sh`, pass `IQOQO_ROOT` and `IGDB_CLIENT_ID` via environment variables and read `os.environ` inside `python3 -c` blocks instead of interpolating shell strings; update `tests/test_bgg2_strategy.py`
- [ ] 1.3 In `tests/bash/scripts_syntax.bats`, add syntax validation tests for `scripts/iqopretest.sh`, `scripts/verify_federation_preview.sh`, and `deploy/wait-for-postgres.sh`

## 2. Celery FTS Debounce Coalescing, Redis Client Cleanup & Work Re-index

- [ ] 2.1 In `app/core/tasks.py` and `app/core/events.py`, add a `threading.Lock` around `_in_memory_fts_queue`, gate `batch_fts_reindex.apply_async` on a Redis `SET iqoqo:fts_reindex_scheduled 1 NX EX <countdown>` debounce key (cleared when `batch_fts_reindex` drains the queue), touch `Work` FTS metadata in `batch_fts_reindex`, and close short-lived Redis clients (`finally: client.close()`) in `publish_transition_event`, `enqueue_fts_reindex`, and `batch_fts_reindex`; update `tests/test_async_fts_transitions.py`

## 3. OpenAPI 3.1 Schema Accuracy & Librarian Gem Sync

- [ ] 3.1 In `app/api/decorators.py` and `app/api/docs.py`, set `decorated._requires_auth = True` on `@require_auth`, `@admin_required`, and `@admin_or_custodian_required`, update `User.id`, `Item.owner_id`, and `Notification.recipient_id` schemas to `{"type": "string", "format": "uuid"}`, update `PersonalAccessToken` schema to use `is_active` and `revoked_at`, and expand `Expression.content_type` enum; update `tests/test_openapi_contract_completeness.py`
- [ ] 3.2 Update `docs/gems/iqoqo-librarian-gem.md` to use `/api/scanner/preview/{barcode}` and align documented PAT scopes with wishlist/catalog capabilities
- [ ] 3.3 Author `tests/test_verify_http_signature.py` testing `scripts/verify_http_signature.py` CLI argument parsing, SHA-256 Digest header verification, signing string assembly, clock-skew rejection, and RSA-SHA256 signature verification

## 4. PAT Scope Enforcement Parity & Bilingual Localization for `TotpSetup` & `PatManagement`

- [ ] 4.1 Wire `useTranslations("Profile")` into `frontend/components/profile/totp-setup.tsx` and `frontend/components/profile/pat-management.tsx` and add complete English and Polish translation keys in `frontend/messages/en.json` and `frontend/messages/pl.json`; update `frontend/__tests__/components/profile/pat-and-totp.test.tsx`
- [ ] 4.2 In `app/api/decorators.py`, permit `"sparql:query"` PAT scope on `POST /api/sparql` in `require_auth` and map `"write:inventory"` alongside `"write:catalog"` in `require_permission`; update `tests/test_auth_pat_and_totp.py` and fix `PATCH /api/v1/notifications/read` route string in `docs/CHANGELOG.md`
- [ ] 4.3 Author component tests `frontend/__tests__/components/cookie-consent.test.tsx` (localStorage consent detection & banner dismissal) and `frontend/__tests__/components/mode-toggle.test.tsx` (theme switching & accessible buttons)

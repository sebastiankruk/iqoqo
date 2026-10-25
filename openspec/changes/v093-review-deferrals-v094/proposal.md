## Why

During the PR #376 (`release/0.9.3` → `main`) review, several non-blocking resilience, schema accuracy, and localization improvements were identified across BGG2 rate-limit backoff, Celery FTS debounce coalescing, OpenAPI 3.1 component schemas, and `/profile` PAT/TOTP translation wiring; deferring these to `v0.9.4` keeps `v0.9.3` focused on critical fixes while tracking all quality items before `v1.0.0`.

## What Changes

- **BoardGameGeek2 Package & Backoff Hardening + Status Script Env Passing (`app/utils/bgg.py`, `requirements.txt`, `pyproject.toml`, `scripts/iqoqo-status.sh`)**:
  - Update dependency manifests from legacy `boardgamegeek>=0.13.0` to `boardgamegeek2>=1.3`, cap `Retry-After` sleep in `BGGBackoffAdapter.send` to `min(float(retry_after), 10.0)` seconds, and set `retries=0` on `BoardGameGeek` client when mounted with `BGGBackoffAdapter` to prevent stacked retry loops.
  - Pass `IGDB_CLIENT_ID` and `IQOQO_ROOT` via environment variables rather than interpolating shell strings into `python3 -c` in `scripts/iqoqo-status.sh`.
- **Celery FTS Debounce Coalescing & Work Re-index (`app/core/tasks.py`)**:
  - Gate `batch_fts_reindex.apply_async` in `enqueue_fts_reindex` with a Redis `SET iqoqo:fts_reindex_scheduled 1 NX EX 5` lock so rapid writes within a 5-second window schedule a single Celery task, protect `_in_memory_fts_queue` with a `threading.Lock`, and touch `Work` FTS state in `batch_fts_reindex`.
- **OpenAPI 3.1 Schema & Auth Detection Accuracy + Librarian Gem Sync (`app/api/docs.py`, `docs/gems/iqoqo-librarian-gem.md`)**:
  - Update `User.id`, `Item.owner_id`, and `Notification.recipient_id` schemas in `app/api/docs.py` from `integer` to `{"type": "string", "format": "uuid"}`, align `PersonalAccessToken` schema with `is_active` and `revoked_at`, expand `Expression.content_type` enum, and set `_requires_auth = True` on `@require_auth` / `@admin_required` so public routes are not falsely marked as requiring Bearer auth.
  - Update `docs/gems/iqoqo-librarian-gem.md` to reference `/api/scanner/preview/{barcode}` and align documented PAT scopes with wishlist/catalog capabilities.
- **Bilingual i18n Wiring for `TotpSetup` and `PatManagement` (`frontend/components/profile/totp-setup.tsx`, `frontend/components/profile/pat-management.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`)**:
  - Wire `useTranslations("Profile")` into `TotpSetup` and `PatManagement` and add complete English and Polish translation keys for all labels, dialogs, badges, and status messages.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `bgg2-and-twitch-igdb-integrations`: Pin `boardgamegeek2>=1.3`, cap `Retry-After` backoff delay at 10 seconds, avoid stacked retries, and pass status script variables via environment.
- `async-transitions-fts-indexing`: Coalesce Celery task scheduling via Redis `NX EX` debounce lock, lock `_in_memory_fts_queue`, and refresh `Work` entities in `batch_fts_reindex`.
- `openapi-31-contract-and-ai-skills`: Type user/owner IDs as UUID strings, align `PersonalAccessToken` schema fields, detect `_requires_auth` via decorator metadata, and sync `iqoqo-librarian-gem.md` routes.
- `auth-pat-and-totp`: Localize `TotpSetup` and `PatManagement` in English and Polish via `useTranslations("Profile")`.

## Impact

- **Backend & Scripts**: `app/utils/bgg.py`, `app/core/tasks.py`, `app/api/docs.py`, `app/api/decorators.py`, `requirements.txt`, `pyproject.toml`, `scripts/iqoqo-status.sh`
- **Frontend & Docs**: `frontend/components/profile/totp-setup.tsx`, `frontend/components/profile/pat-management.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`, `docs/gems/iqoqo-librarian-gem.md`

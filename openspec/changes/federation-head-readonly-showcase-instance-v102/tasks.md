## 1. Backend Configuration & Physical Item Write Guard (`app/`)

- [ ] 1.1 Add `FEDERATION_HEAD_MODE` (`bool`, default `False`) to `app/config.py`, `.env.example`, `FEDERATION_KEYS` in `app/api/admin.py`, and `is_federation_head_mode()` helper in `app/core/config_service.py`, verifying `GET /api/config` (`app/api/system.py`) returns `federation_head_mode: bool` and `GET /.well-known/nodeinfo/2.1` (`app/api/federation.py`) includes `metadata.federationHead`.
- [ ] 1.2 Enforce the server-side physical item write guard (`reject_if_federation_head_item_write()`) in `POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk` (`app/api/items.py`), and `POST /api/scan` (`app/api/scanner.py`) so physical `Item` creation returns HTTP `403` when `FEDERATION_HEAD_MODE=true`, while verifying `POST /api/wishlist`, `POST /api/scan` with `policy="wishlist"` / `collection_status="wish_list"`, `policy="catalog_only"` (for custodians), and `/ap/inbox` S2S federation remain allowed.

## 2. Frontend Federation Hub Badge, Banner, Copy & Navigation (`frontend/`)

- [ ] 2.1 Update `useAppConfig()` in `frontend/lib/api/hooks/catalog.ts` and `SETTING_GROUPS.federation` in `frontend/components/admin/instance-settings.tsx` to expose `federation_head_mode` / `FEDERATION_HEAD_MODE` and invalidate `queryKeys.config` on save.
- [ ] 2.2 Update `frontend/components/dashboard/navbar.tsx` to render the `"Federation Hub · Read-Only"` brand pill badge and dismissible info banner when `config?.federation_head_mode === true`, hide the desktop `Scan` CTA, and replace the mobile bottom-navigation `Scan` tab with `Directory` (`/federation/directory`).
- [ ] 2.3 Update `frontend/components/landing/hero.tsx`, `frontend/app/page.tsx`, `frontend/components/dashboard/stats-cards.tsx` (defaulting to `global` scope when `federation_head_mode` is `true`), `frontend/app/scan/page.tsx` (rendering the Shadcn Federation Hub read-only notice card with links to `/collection` and `/federation/directory`), and `frontend/messages/{en,pl}.json`.

## 3. Verification & Test Suite

- [ ] 3.1 Author backend tests in `tests/test_federation_head_mode.py` covering `GET /api/config`, `403` rejection on physical item creation (`POST /api/items`, `/api/items/manual`, `/api/items/bulk`, `/api/scan`), allowed Wishlist mutations (`UserWorkIntent`), and S2S inbox ingestion.
- [ ] 3.2 Author frontend unit tests in `frontend/__tests__/components/dashboard/navbar-federation-head.test.tsx` and `frontend/__tests__/app/scan-federation-head.test.tsx`, and run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`.

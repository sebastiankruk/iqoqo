## Why

The flagship `iqoqo.cc` deployment acts as the public Federation Hub and showcase coordinator for the iqoqo network: users can log in, search across works/editions/items synchronized from peered community instances (`iqoqo.kruk.cc` and self-hosted nodes), manage personal Wishlists (`UserWorkIntent`), and participate in social federation, but cannot catalog local physical `Item` copies on the hub itself. Without an explicit `FEDERATION_HEAD_MODE` configuration and read-only hub UX, visitors and logged-in users on `iqoqo.cc` see misleading "Add Item" / "Scan" controls and empty personal collection metrics instead of a clear Federation Hub identity.

## What Changes

- **Federation Head Configuration (`FEDERATION_HEAD_MODE`):** Add `FEDERATION_HEAD_MODE` (`bool`, default `false`) to `Config`, `FEDERATION_KEYS` in `app/api/admin.py`, `InstanceSettings` UI (`frontend/components/admin/instance-settings.tsx`), and expose `federation_head_mode: boolean` in `GET /api/config` (`app/api/system.py`) and `/.well-known/nodeinfo/2.1` metadata (`metadata.federationHead: bool`).
- **Backend Physical Item Write Guard (Preserving Wishlist & S2S Sync):** Enforce a server-side guard (`reject_if_federation_head_item_write`) on local physical `Item` creation endpoints (`POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk`, and `POST /api/scan` when `policy != "wishlist"` and `collection_status != "wish_list"`), returning `403 Forbidden` with `{"error": "This instance operates as a read-only Federation Hub. Physical items are synchronized from connected community nodes; you may still add works to your Wishlist.", "code": 403}` while allowing `UserWorkIntent` wishlist additions, `GET /api/scanner/preview/<query>`, ActivityPub S2S inbox ingestion (`/ap/inbox`), and admin/custodian curation.
- **Navbar Federation Hub Badge, Dismissible Banner & Action Density (`frontend/components/dashboard/navbar.tsx`):** Render a semantic pill badge (`Federation Hub · Read-Only`) beside the brand logo and a slim dismissible info banner linking to `/federation/directory` and self-hosting docs when `federation_head_mode` is active. Hide the desktop `Scan` CTA and swap the mobile bottom-navigation `Scan` tab for `Directory` (`/federation/directory`) to keep button density $\le 5$ and prevent dead item-addition flows.
- **Hero, Authenticated Dashboard & `/scan` Hub UX (`hero.tsx`, `app/page.tsx`, `stats-cards.tsx`, `app/scan/page.tsx`):** Tailor landing `Hero` copy and single primary CTA (`"Explore Federated Catalog"` $\to$ `/collection`) when `federation_head_mode` is active; default authenticated `StatsCards` to `Global` (Federated Repository) scope; and render a clean Shadcn Federation Hub notice on `/scan` offering 1-click navigation to **Search Federated Catalog** (`/collection`), **Add to Wishlist**, or **Connected Libraries** (`/federation/directory`).

## Capabilities

### New Capabilities
- `federation-head-showcase-mode`: Configuration, API write guards, and frontend UX (badge, banner, tailored copy, and navigation routing) for operating `iqoqo.cc` as a read-only Federation Hub where catalog content is synchronized from peered nodes while preserving authenticated Wishlist (`UserWorkIntent`) and social discovery.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- **Backend:** `app/config.py`, `app/api/system.py` (`GET /api/config`), `app/api/admin.py` (`FEDERATION_KEYS`), `app/api/federation.py` (NodeInfo metadata), `app/api/items.py`, `app/api/scanner.py`
- **Frontend:** `frontend/lib/api/hooks/catalog.ts` (`useAppConfig`), `frontend/components/dashboard/navbar.tsx`, `frontend/components/landing/hero.tsx`, `frontend/app/page.tsx`, `frontend/components/dashboard/stats-cards.tsx`, `frontend/app/scan/page.tsx`, `frontend/components/admin/instance-settings.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`
- **Tests:** `tests/test_federation_head_mode.py`, `frontend/__tests__/components/dashboard/navbar-federation-head.test.tsx`, `frontend/__tests__/app/scan-federation-head.test.tsx`

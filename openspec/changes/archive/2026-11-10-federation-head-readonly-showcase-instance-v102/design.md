## Context

See `proposal.md` for motivation. `iqoqo.cc` serves as the public showcase and Federation Coordinator node in the `iqoqo` ecosystem, while personal physical collections live on self-hosted community instances (e.g., `iqoqo.kruk.cc`). Our architecture already exposes public runtime toggles via `GET /api/config` (`federation_enabled`, `version`, `maintenance_mode`) consumed by `useAppConfig()` in `frontend/lib/api/hooks/catalog.ts`, and separates physical `Item` ownership (`app/db/core.py`) from Wishlist intents (`UserWorkIntent` in `app/db/social.py`).

## Goals / Non-Goals

**Goals:**
- Enforce a defense-in-depth backend write guard on physical `Item` creation when `FEDERATION_HEAD_MODE` is active (`403 Forbidden`), never relying on hiding UI buttons alone.
- Preserve authenticated `UserWorkIntent` (Wishlist), social following, ActivityPub S2S `/ap/inbox` ingestion, and admin/custodian curation on the Federation Head.
- Adapt `Navbar`, `Hero`, `DashboardPage`, `StatsCards`, and `/scan` when `federation_head_mode === true` while respecting `iqoqo-ux-auditor` heuristics (single primary Hero CTA, $\le 5$ mobile bottom-nav actions, zero dead buttons).
- Expose `FEDERATION_HEAD_MODE` in `InstanceSettings` (`/admin/settings?tab=federation`), `.env.example`, `/api/config`, and `/.well-known/nodeinfo/2.1`.

**Non-Goals:**
- Forking a separate frontend codebase for `iqoqo.cc`.
- Blocking `UserWorkIntent` (Wishlist) or social following on the Federation Head.

## Decisions

### 1. Server-Side Guard Helper (`is_federation_head_mode()` + `reject_if_federation_head_item_write()`)
* **Decision:** Implement `is_federation_head_mode() -> bool` in `app/core/config_service.py` (checking `InstanceSettings.get_value("FEDERATION_HEAD_MODE")` with fallback to `Config.FEDERATION_HEAD_MODE`). Apply a guard in `POST /api/items`, `POST /api/items/manual`, `POST /api/items/bulk`, and `POST /api/scan` (when `policy != "wishlist"` and `collection_status != "wish_list"`).
* **Rationale (Security & Ontological Purity):** Hiding `/scan` in the Next.js UI is insufficient against direct API or PAT requests. Blocking only `F5_Item` instantiation while allowing `UserWorkIntent` (Wishlist) and `/ap/inbox` S2S federation keeps the FRBR ontology clean: `iqoqo.cc` holds federated `Work`/`Expression`/`Manifestation` graphs and remote provenance without bogus local shelf copies.

### 2. Action-Density-Preserving Navbar & Mobile Bottom Nav Substitution
* **Decision:** When `config?.federation_head_mode === true`:
  1. Render a compact semantic badge (`Globe` icon + `"Federation Hub · Read-Only"`) next to the `iqoqo` brand in `Navbar`, plus a dismissible info banner (`localStorage` key `iqoqo_fed_head_banner_dismissed`) below the navbar.
  2. Hide the desktop `Scan` pill button in `Navbar` and replace the mobile bottom-navigation `Scan` tab with `Directory` (`/federation/directory`, `Globe` icon).
  3. On `Hero`, set the single primary solid accent CTA to `"Explore Federated Catalog"` (`/collection`) and secondary outline CTA to `"Connected Libraries"` (`/federation/directory`).
  4. On `StatsCards`, initialize default scope to `"global"` when `federation_head_mode` is `true` so logged-in users immediately see federated repository counts instead of `0` personal items.
* **Rationale (UX Auditor):** Preserves the 5-tab mobile bottom bar rhythm (`Home / Directory / Collection / Search / Profile|Sign In`), guarantees zero dead/unwired controls, and maintains a single primary CTA on the Hero banner.

## Risks / Trade-offs

- **[Risk] Cached `/api/config` stale after admin toggle** $\to$ **Mitigation:** Invalidate `queryKeys.config` in `InstanceSettings` when saving `federation` category settings, and keep backend enforcement authoritative on every request.
- **[Risk] Custodians testing catalog ingestion on `iqoqo.cc`** $\to$ **Mitigation:** `POST /api/scan` with `policy="catalog_only"` remains permitted for users with `write:metadata` / custodian permissions so bibliographic `Work`/`Manifestation` records can still be curated without creating a physical `Item`.

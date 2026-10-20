## Why

The `v0.9.1` pre-release code review (PR #362, documented in `.context/notes/review/0.9.1/`) identified several moderate architectural, localization, testing, and provenance enhancements that do not block the `v0.9.1` release once `C79c` (`v091-pre-release-critical-fixes`) is applied, and should be delivered at the start of the `v0.9.2` stream:

1. **`AdminFederation` i18n Wiring & UI Polish (`C78` Carry-Over)**: `AdminFederation` translation keys were added to `en.json` and `pl.json` in `C78`, but `frontend/app/admin/federation/page.tsx`, `federation-instances.tsx`, and `federation-activity.tsx` still render hardcoded English strings. Additionally, icon-only pagination/copy buttons lack `aria-label` attributes, and `FEDERATION_DEFAULT_TRUST` in `instance-settings.tsx` uses an unconstrained `<Input>` instead of a `Select` dropdown (`untrusted | pending | trusted`).
2. **Frontend Unit Tests for Admin Federation (`C78` Carry-Over)**: The three Vitest/RTL test suites planned for `C78` (`frontend/__tests__/lib/api/federation.test.ts`, `frontend/__tests__/components/admin/federation-instances.test.tsx`, `frontend/__tests__/components/admin/federation-activity.test.tsx`) need to be authored.
3. **Multi-Tier `Work`/`Expression` Provenance Sync & MusicBrainz/BGG Identifier Linking (`C77` Carry-Over)**: `app/core/federation_sync.py` currently reconciles `Manifestation` fields by ISBN/UPC/EAN/URI; extending auto-fill and provenance tracking to empty `Work` and `Expression` fields and matching via MusicBrainz (`mbid`) and BoardGameGeek (`bgg_id`) identifiers completes the full `C77` cross-media scope.
4. **Admin Federation Trust Audit Logging, Actor Inbox Resolution & Discovery Concurrency**: Trust level changes (`trusted`/`blocked`) and instance deletions in `app/api/admin.py` should emit `EntityAuditLog` entries; `add_federation_instance` should return `probe_succeeded` status; `_get_or_create_actor` should resolve the remote Actor document's actual `inbox` URL before falling back to `{actor_uri}/inbox`; and `probe_registered_instances` should use bounded concurrency so unreachable peers cannot stall the scheduler.

## What Changes

- **Admin Federation i18n, A11y & Constrained Trust Select (`frontend/app/admin/federation/*`, `frontend/components/admin/instance-settings.tsx`)**:
  - Wire `useTranslations("AdminFederation")` into `page.tsx`, `federation-instances.tsx`, and `federation-activity.tsx`.
  - Add `aria-label` attributes to pagination and fingerprint copy controls, and replace the free-text `FEDERATION_DEFAULT_TRUST` `<Input>` with a `Select` (`untrusted`, `pending`, `trusted`).
- **Frontend Unit Test Suites (`frontend/__tests__/...`)**:
  - Add `frontend/__tests__/lib/api/federation.test.ts`, `frontend/__tests__/components/admin/federation-instances.test.tsx`, and `frontend/__tests__/components/admin/federation-activity.test.tsx`.
- **Multi-Tier FRBR Sync & MusicBrainz/BGG Identifier Resolution (`app/core/federation_sync.py`)**:
  - Extend `resolve_local_manifestation` (and work/expression resolution) to match MusicBrainz release/work IDs and BGG IDs in `Manifestation.meta` / `Work.meta`.
  - Extend `sync_manifestation` to auto-fill empty parent `Expression` and `Work` attributes (e.g. `language`, `description`/`summary`, `original_Release_year`) from `trusted` peers with `meta["_provenance"]` and `prov:wasDerivedFrom` tracking, and consolidate duplicate `PENDING` JSONB storage.
- **Admin Audit Logging, Actor Document Inbox Resolution & Bounded Health Probes (`app/api/admin.py`, `app/core/federation_handlers.py`, `app/core/federation_discovery.py`)**:
  - Record `EntityAuditLog` rows when an admin updates `trust_level` or deletes a `FederationInstance`, and include `probe_succeeded` in the `POST /api/v1/admin/federation/instances` response.
  - Fetch remote Actor JSON-LD via `FederationClient().fetch_actor(actor_uri)` in `_get_or_create_actor` to populate the canonical `inbox` and `publicKeyPem`.
  - Execute `probe_registered_instances` with bounded concurrency (`ThreadPoolExecutor(max_workers=5)`) so slow peers do not block the APScheduler job.

## Capabilities

### Modified Capabilities
- `admin-federation-ui`: Wire `useTranslations("AdminFederation")`, add accessibility labels, constrain `FEDERATION_DEFAULT_TRUST` to valid enum options, and add Vitest unit test coverage.
- `federation-trust-and-sync`: Support `Work`/`Expression` provenance-tracked auto-fill, MusicBrainz/BGG identifier matching, `EntityAuditLog` auditing on admin trust mutations, and bounded concurrency in periodic instance health probes.
- `activitypub-inbox-outbox`: Resolve remote Actor JSON-LD `inbox` and `publicKeyPem` in `_get_or_create_actor`.

## Impact

- `frontend/app/admin/federation/page.tsx`, `frontend/components/admin/federation-instances.tsx`, `frontend/components/admin/federation-activity.tsx`, `frontend/components/admin/instance-settings.tsx`
- `frontend/__tests__/lib/api/federation.test.ts`, `frontend/__tests__/components/admin/federation-instances.test.tsx`, `frontend/__tests__/components/admin/federation-activity.test.tsx`
- `app/core/federation_sync.py`, `app/core/federation_discovery.py`, `app/core/federation_handlers.py`, `app/api/admin.py`

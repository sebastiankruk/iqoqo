## 1. Admin Federation i18n, Accessibility & Trust Selector Polish (`C78` Carry-Over)

- [x] 1.1 Wire `useTranslations("AdminFederation")` into `frontend/app/admin/federation/page.tsx`, `frontend/components/admin/federation-instances.tsx`, and `frontend/components/admin/federation-activity.tsx`, adding any missing keys to `en.json` and `pl.json`
- [x] 1.2 Add `aria-label` attributes to pagination and key-fingerprint copy buttons, and replace the free-text `FEDERATION_DEFAULT_TRUST` `<Input>` in `frontend/components/admin/instance-settings.tsx` with a constrained `Select` (`untrusted`, `pending`, `trusted`)

## 2. Frontend Unit Test Suites for Admin Federation (`C78` Carry-Over)

- [x] 2.1 Create `frontend/__tests__/lib/api/federation.test.ts` testing `listFederationInstances`, `addFederationInstance`, `updateFederationInstance`, `deleteFederationInstance`, and `listFederationActivities`
- [x] 2.2 Create `frontend/__tests__/components/admin/federation-instances.test.tsx` and `frontend/__tests__/components/admin/federation-activity.test.tsx` covering instance discovery, trust badge updates, deletion confirmation, and activity filtering

## 3. Multi-Tier `Work`/`Expression` Provenance Sync & Identifier Linking (`C77` Carry-Over)

- [x] 3.1 Extend `resolve_local_manifestation` in `app/core/federation_sync.py` to match MusicBrainz (`mbid`) and BoardGameGeek (`bgg_id`) identifiers stored in `Manifestation.meta` / `Work.meta`
- [x] 3.2 Extend `sync_manifestation` in `app/core/federation_sync.py` to auto-fill empty `Expression` (`language`) and `Work` (`description`) fields from `trusted` peers with `meta["_provenance"]` and `prov:wasDerivedFrom` tracking, consolidate duplicate `PENDING` JSONB storage, and verify in `tests/test_federation_trust_sync.py`

## 4. Admin Trust Audit Logging, Actor Inbox Resolution & Discovery Concurrency

- [x] 4.1 Record `EntityAuditLog` entries on federation instance trust mutation and deletion in `app/api/admin.py`, and include `probe_succeeded` in `add_federation_instance` responses
- [x] 4.2 Update `_get_or_create_actor` in `app/core/federation_handlers.py` to resolve the remote Actor JSON-LD document's `inbox` and `publicKeyPem` via `FederationClient().fetch_actor(actor_uri)` before falling back to `{actor_uri}/inbox`
- [x] 4.3 Add bounded concurrency / deadline guards to `probe_registered_instances` in `app/core/federation_discovery.py` and verify in `tests/test_federation_discovery_admin.py`

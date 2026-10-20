## Context

Following the `v0.9.1` pre-release review (PR #362), all critical security, SRE, and scanner regressions were isolated into `C79c` (`v091-pre-release-critical-fixes`) for immediate landing on `release/0.9.1`. The remaining moderate items—completing `AdminFederation` component localization and unit tests (`C78`), extending provenance-aware metadata sync to `Work`/`Expression` tiers and MusicBrainz/BGG identifiers (`C77`), and adding admin trust audit logging and concurrent health probes—are scheduled here as `C79d` (`v091-review-deferrals-v092`) at the start of `v0.9.2`.

## Goals / Non-Goals

**Goals:**
- Achieve 100% i18n coverage (`en.json` / `pl.json`) and unit test coverage across the Admin Federation dashboard components.
- Constrain `FEDERATION_DEFAULT_TRUST` in `instance-settings.tsx` to valid `TrustLevel` values (`untrusted`, `pending`, `trusted`).
- Extend `federation_sync.py` to support MusicBrainz (`mbid`) and BoardGameGeek (`bgg_id`) identifier resolution and provenance-backed auto-fill for empty `Work` and `Expression` fields.
- Emit `EntityAuditLog` entries on federation instance trust mutations/deletions, surface `probe_succeeded` in `add_federation_instance`, resolve remote Actor `inbox` URLs on first contact, and bound health-probe concurrency.

**Non-Goals:**
- Federated social friend following and cross-instance loan workflows (covered by `C80` and `C81` in `v0.9.2`).

## Decisions

### 1. Admin Federation i18n & Unit Testing
- **Decision:** Replace all hardcoded English labels in `frontend/app/admin/federation/page.tsx`, `federation-instances.tsx`, and `federation-activity.tsx` with `useTranslations("AdminFederation")`, add `aria-label` attributes to icon buttons, replace the `FEDERATION_DEFAULT_TRUST` text input with a `Select` component, and author the three Vitest test suites (`federation.test.ts`, `federation-instances.test.tsx`, `federation-activity.test.tsx`).

### 2. Multi-Tier FRBR Sync & MusicBrainz/BGG Matching
- **Decision:** Extend `resolve_local_manifestation` in `app/core/federation_sync.py` to check `remote_data.get("mbid")` / `remote_data.get("bgg_id")` against `Manifestation.meta` and parent `Work.meta`. When `trust_level == TrustLevel.TRUSTED`, allow `sync_manifestation` to also populate empty fields on `manifestation.expression` (`language`) and `manifestation.expression.work` (`description`) while recording `meta["_provenance"]` and `prov:wasDerivedFrom` on each modified tier.

### 3. Admin Trust Audit Logging & Discovery Hardening
- **Decision:** Log `EntityAuditLog(entity_type="federation_instance", change_type="trust_level_updated" | "instance_deleted")` in `app/api/admin.py`; fetch remote actor documents via `FederationClient().fetch_actor(actor_uri)` in `_get_or_create_actor` (falling back to `{actor_uri}/inbox` only on network failure); and run `probe_registered_instances` probes using bounded worker threads or per-job deadline caps.

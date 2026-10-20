## Why

Before merging PR #362 (`release/0.9.1 -> main`), the pre-release code review (Principal Code Reviewer + Gemini Argon in `.context/notes/review/0.9.1/`) and live staging testing (`iqopretest.sh`) identified **7 Critical** and **6 high-impact Moderate** issues that must be resolved in `v0.9.1`:

1. **Manual Text Search Book Addition Fails (`"Barcode or Manifestation ID is required"`)**: Searching by text in `/scan` returns disambiguation candidates without creating a local `Manifestation` (`manifestation_id` is undefined) and without guaranteeing per-candidate `data_source`. When the user selects a candidate and clicks **Add to Library**, `_validate_scan_request` (`app/api/scanner.py:438`) rejects `if not barcode and not manifestation_id:` even though `scan_barcode()` (`line 708`) explicitly supports ingesting from `payload.meta` via `IngestService.ingest_from_meta(payload.meta)`.
2. **Cross-User `Item.local_barcode` IDOR**: `_find_locally` and `lookup_barcode_preview` in `app/api/scanner.py` query `Item.local_barcode` across all users without filtering by `Item.owner_id == g.user_id`, leaking other users' private `item_id`s and falsely flagging `already_in_collection = True`.
3. **Unverified S2S Activity Handlers (`federation_handlers.py`)**: `handle_delete` deletes any `FederationActor` matching `object_uri` without verifying `actor_uri == object_uri`; `handle_accept` / `handle_reject` allow a remote actor with a `PENDING` inbound follow request to self-approve by sending a spoofed `Accept(Follow)`.
4. **Cross-Instance Manifestation Primary-Key Collision & Unsanitized Metadata (`federation_sync.py`)**: `resolve_local_manifestation` extracts `/manifestation/<int>` from `remote_data["id"]` without verifying that the URI belongs to the local instance's hostname, overwriting unrelated local `Manifestation` rows by integer PK; `sync_manifestation` also lacks `bleach.clean` string sanitization and `http(s)` scheme validation on `cover_url`.
5. **Unconsumed Celery `federation` Queue, Ignored Outbound HTTP Status & Dead Dispatch (`celery_app.py`, `federation_tasks.py`, `federation_dispatch.py`, `docker-compose*.yml`)**: Federation tasks are routed to `queue="federation"`, which no Celery worker in `docker-compose*.yml` consumes (`-Q celery,federation`); `deliver_activity` marks HTTP 4xx/5xx inbox responses as `DELIVERED`; `_queue_and_deliver` enqueues tasks before `db.session.commit()` with an N+1 query; and `dispatch_collection_update` / `dispatch_metadata_update` are never invoked on item/manifestation mutations (and lack an `item.is_hidden` privacy guard).
6. **ActivityPub Inbox Chunked Bypass & Target User Consent (`app/api/federation.py`)**: `receive_inbox` checks only `request.content_length` (bypassed by `Transfer-Encoding: chunked`), ignores `user_uuid`/`username` route parameters (failing to verify target user existence and `federated_profile` consent), and passes `str(activity_rec.id)` (`"None"`) if `db.session.commit()` fails.
7. **Defensive Database, Crypto & Release Hygiene Guards**: `frbr_merge.py:get_entity_tombstone` mutates persistent `first_audit.diff` in-place without `db.session.expunge`; `http_signatures.py` re-fetches remote keys on every invalid signature without a cooldown or persisting rotated keys; `admin.py:delete_federation_instance` fails with a FK `IntegrityError` when `FederationActor` rows exist; `federation_discovery.py` overbroadly enables HTTP/netloc rewrites on any domain containing `":"`, `"web"`, or `"peer"`; `v0_9_1_followers_unique.py` lacks pre-constraint deduplication; and `docs/CHANGELOG.md` has a blank `0.9.1` entry.

## What Changes

- **Manual Text Search Ingestion & `local_barcode` Owner Scoping (`app/api/scanner.py`, `frontend/components/scanner/success-card.tsx`, `frontend/app/scan/page.tsx`)**:
  - Allow `payload.meta` in `_validate_scan_request(payload)` when `barcode` and `manifestation_id` are absent (`if not barcode and not manifestation_id and not payload.meta:`).
  - Ensure every candidate in `lookup_barcode_preview` sets `cand.setdefault("data_source", "search")` and `SuccessCard` normalizes ISBN-10/13 identifiers (stripping hyphens/spaces) and always forwards `meta` when metadata is present.
  - Scope `Item.local_barcode` lookups in `_find_locally` and `lookup_barcode_preview` strictly to `Item.owner_id == g.user_id` using SQLAlchemy 2.0 `select(Item)`.
- **ActivityPub Handler Authorization & Concurrency Safety (`app/core/federation_handlers.py`, `app/api/federation.py`)**:
  - Require `actor_uri == object_uri` in `handle_delete` before deleting a `FederationActor` and its followers.
  - Validate follow direction in `handle_accept` and `handle_reject` so remote actors cannot self-approve inbound `PENDING` follow requests.
  - Catch `IntegrityError` with rollback/re-select in `_get_or_create_actor` and `handle_follow`.
  - Enforce `FEDERATION_MAX_PAYLOAD_BYTES` (100KB) on actual request body bytes in `receive_inbox`, validate target `user_uuid`/`username` existence and `federated_profile` consent on per-actor inbox routes, and reset `activity_rec = None` on DB commit failure.
- **Trust-Gated Sync Isolation & Sanitization (`app/core/federation_sync.py`, `app/core/federation_discovery.py`, `app/api/admin.py`)**:
  - Verify `urlparse(remote_id).netloc` matches the local instance domain before resolving `/manifestation/<int>` in `resolve_local_manifestation`.
  - Sanitize inbound string metadata with `bleach.clean(..., tags=[], strip=True)` and validate `cover_url` scheme (`https://` or `http://`) in `sync_manifestation`.
  - Gate plaintext HTTP fallback and internal Docker hostname netloc rewriting in `federation_discovery.py` and `federation.py` on `FEDERATION_ALLOW_LOOPBACK == "true"`.
  - Clean up dependent `FederationFollower` and `FederationActor` rows before deleting a `FederationInstance` in `delete_federation_instance`.
- **Celery `federation` Queue Consumption, Delivery Verification & Outbound Fan-Out (`app/core/celery_app.py`, `app/core/federation_tasks.py`, `app/core/federation_dispatch.py`, `docker-compose*.yml`)**:
  - Bind Celery workers in `docker-compose.yml`, `docker-compose.override.yml`, and `docker-compose.federation-preview.yml` to `-Q celery,federation`.
  - Check `resp.status_code in (200, 201, 202, 204)` in `deliver_activity`, increment `federation_delivery_failures_total` on failure, and mark failed deliveries `ActivityStatus.FAILED`.
  - Fix `_queue_and_deliver` to batch-load `FederationActor` rows (eliminating N+1 queries), commit `FederationActivity` rows before calling `submit_task`, guard `dispatch_collection_update` against `item.is_hidden`, include manifestation identifiers in outbound `Update`/`Create` payloads, and wire `dispatch_collection_update` / `dispatch_metadata_update` into item/manifestation lifecycle hooks.
- **Tombstone Immutability, Key Re-Fetch Cooldown, Migration Idempotency & Changelog (`app/core/frbr_merge.py`, `app/core/http_signatures.py`, `migrations/versions/v0_9_1_followers_unique.py`, `docs/CHANGELOG.md`)**:
  - Call `db.session.expunge(first_audit)` before mutating `first_audit.diff` in `get_entity_tombstone`.
  - Enforce a 60-second minimum staleness cooldown on `FederationActor.last_fetched_at` before re-fetching remote keys on signature failure, and persist rotated keys back to `FederationActor.public_key_pem`.
  - Deduplicate `(local_user_id, remote_actor_id)` pairs and guard constraint creation in `v0_9_1_followers_unique.py`.
  - Populate `## [0.9.1]` in `docs/CHANGELOG.md`.

## Capabilities

### Modified Capabilities
- `item-local-barcode`: Scope `Item.local_barcode` resolution in scanner lookup/ingestion to the authenticated owner (`Item.owner_id == g.user_id`) and permit manual text-search book ingestion via `payload.meta` when `barcode` and `manifestation_id` are absent.
- `activitypub-inbox-outbox`: Enforce raw-byte 100KB inbox payload cap, per-actor inbox target user consent validation, `handle_delete` actor ownership check, `handle_accept`/`handle_reject` spoof prevention, Celery `-Q celery,federation` worker queue consumption, HTTP 2xx delivery verification, and post-commit outbound fan-out with `item.is_hidden` privacy protection.
- `federation-trust-and-sync`: Enforce local hostname verification on `/manifestation/<id>` URI resolution, `bleach.clean` string sanitization, `http(s)` `cover_url` validation, `FEDERATION_ALLOW_LOOPBACK` gating, and cascade cleanup on instance deletion.
- `activitypub-discovery-and-signatures`: Add 60-second cooldown and DB persistence for rotated actor public keys in `verify_request`.
- `iri-immutability`: Detach `first_audit` via `db.session.expunge` before in-memory multi-hop tombstone resolution.

## Impact

- `app/api/scanner.py`, `frontend/components/scanner/success-card.tsx`, `frontend/app/scan/page.tsx`
- `app/api/federation.py`, `app/core/federation_handlers.py`, `app/core/federation_dispatch.py`, `app/core/federation_tasks.py`
- `app/core/federation_sync.py`, `app/core/federation_discovery.py`, `app/api/admin.py`
- `app/core/celery_app.py`, `docker-compose.yml`, `docker-compose.override.yml`, `docker-compose.federation-preview.yml`
- `app/core/frbr_merge.py`, `app/core/http_signatures.py`, `migrations/versions/v0_9_1_followers_unique.py`, `docs/CHANGELOG.md`

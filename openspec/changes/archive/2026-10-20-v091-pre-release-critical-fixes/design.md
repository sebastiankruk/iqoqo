## Context

During the pre-release review of `release/0.9.1` (PR #362) and live testing with `iqopretest.sh`, seven critical issues were uncovered across the Scanner manual search flow, `Item.local_barcode` lookup scoping, ActivityPub S2S inbox/handler authorization, cross-instance manifestation URI resolution, and Celery `federation` queue execution. All fixes in this change are targeted, backwards-compatible hardening patches required before `v0.9.1` merges to `main`.

## Goals / Non-Goals

**Goals:**
- Restore manual text-search book/media addition in `/scan` when a selected candidate has no numeric barcode or pre-existing `manifestation_id`.
- Eliminate cross-user IDOR in `Item.local_barcode` scanner lookups.
- Prevent unauthorized remote actor deletion (`handle_delete`) and inbound follow self-approval spoofing (`handle_accept` / `handle_reject`).
- Prevent cross-instance integer primary-key collisions in `resolve_local_manifestation` and sanitize remote string/URL fields in `sync_manifestation`.
- Ensure Celery workers consume the `federation` queue, verify HTTP 2xx status codes in `deliver_activity`, commit DB rows before enqueuing Celery tasks, and wire outbound collection/metadata dispatch with `is_hidden` privacy checks.
- Harden `receive_inbox` against chunked payload size bypasses and unconsented target actors, protect `get_entity_tombstone` from mutating persistent audit rows, add a cooldown + DB update for rotated public keys, make `v0_9_1_followers_unique.py` idempotent, and populate `docs/CHANGELOG.md`.

**Non-Goals:**
- Multi-tier `Work`/`Expression` remote field auto-fill and MusicBrainz/BGG identifier linking (deferred to `v091-review-deferrals-v092` in `v0.9.2`).
- `AdminFederation` frontend i18n wiring and frontend unit test suites (deferred to `v091-review-deferrals-v092` in `v0.9.2`).

## Decisions

### 1. Manual Text Search Ingestion via `payload.meta`
- **Problem:** `GET /api/lookup/<query>` returns normalized search candidates early at `app/api/scanner.py:284` without persisting a `Manifestation` (`manifestation_id` is absent) and without setting `data_source` on each candidate dict. When `SuccessCard` submits `POST /api/scan`, `_validate_scan_request(payload)` at line 438 checks `if not barcode and not manifestation_id:` and returns HTTP 400 `"Barcode or Manifestation ID is required"`, blocking line 714 (`IngestService.ingest_from_meta(payload.meta)`).
- **Decision:**
  1. In `_validate_scan_request(payload)` (`app/api/scanner.py:438`), permit requests where `payload.meta` is a non-empty dictionary containing a title (`title` or `Title`) even when `barcode` and `manifestation_id` are empty.
  2. In `lookup_barcode_preview` (`app/api/scanner.py:272-276`), ensure each candidate in `normalized_candidates` sets `cand.setdefault("data_source", "search")`.
  3. In `SuccessCard` (`frontend/components/scanner/success-card.tsx`) and `ScanPage` (`frontend/app/scan/page.tsx`), strip hyphens and spaces from `rawIdentifier` before checking `/^(\d{8,14}|\d{9}[\dXx])$/`, preserve `data_source` on selected candidates, and pass `meta: hasMetadata ? meta : undefined` in `handleAdd`.

### 2. Owner-Scoped `Item.local_barcode` Resolution
- **Problem:** `_find_locally` (`app/api/scanner.py:117`) and `lookup_barcode_preview` (`line 199`) query `Item.local_barcode == clean_code` across all users.
- **Decision:** Replace `Item.query.filter(...)` with SQLAlchemy 2.0 `select(Item).where(Item.local_barcode == clean_code, Item.owner_id == getattr(g, "user_id", None))` so physical inventory tags are strictly isolated to the authenticated collector.

### 3. S2S Activity Handler Authorization & Inbox Guards
- **Problem:** `handle_delete` deletes any `FederationActor` matching `object_uri` even when `actor_uri != object_uri`. `handle_accept`/`handle_reject` mutate inbound `FederationFollower` rows when a remote follower sends `Accept(Follow)`. `receive_inbox` checks only `request.content_length` and ignores `user_uuid`/`username`.
- **Decision:**
  1. In `handle_delete`, require `actor_uri == object_uri` before deleting a `FederationActor`.
  2. In `handle_accept` and `handle_reject`, verify that the inner `Follow` object has `inner.get("object") == actor_uri` (meaning the local user was following the remote actor); never allow the remote follower (`FederationFollower.remote_actor_id`) to transition its own inbound `FollowStatus.PENDING` row to `ACCEPTED`.
  3. In `receive_inbox`, inspect `raw_body = request.get_data(cache=True)` and reject `len(raw_body) > FEDERATION_MAX_PAYLOAD_BYTES` with HTTP 413 before signature verification. When `user_uuid` or `username` is present in the route, resolve the target `User` and require `FederationConsent.federated_profile == True` (returning 404 otherwise).

### 4. Local Hostname Verification & Input Sanitization in `federation_sync.py`
- **Problem:** `resolve_local_manifestation` parses `/manifestation/<int>` from `remote_data["id"]` without checking the URI hostname, causing remote primary keys to collide with local `Manifestation.id` rows.
- **Decision:** Compare `urlparse(remote_id).netloc.lower()` against the local instance netlocs derived from `get_federation_base_url()` and `get_lod_base_url()`. Only look up `Manifestation` by integer ID when the URI belongs to the local instance. Sanitize all inbound string fields in `sync_manifestation` using `bleach.clean(str(val), tags=[], strip=True)` and validate `urlparse(cover_url).scheme in ("https", "http")`.

### 5. Celery `federation` Queue & Outbound Delivery Pipeline
- **Problem:** Celery workers in `docker-compose*.yml` do not consume the `federation` queue; `deliver_activity` ignores HTTP 4xx/5xx responses; `_queue_and_deliver` enqueues tasks before `db.session.commit()`.
- **Decision:**
  1. Append `-Q celery,federation` to Celery worker commands in `docker-compose.yml`, `docker-compose.override.yml`, and `docker-compose.federation-preview.yml`.
  2. In `deliver_activity`, check `200 <= resp.status_code < 300`; on non-2xx or exception, increment `federation_delivery_failures_total` and mark `fed_activity.status = ActivityStatus.FAILED` (since `FederationClient.post_to_inbox` already performs `tenacity` exponential backoff retries).
  3. In `_queue_and_deliver`, join `FederationActor` in a single query, commit all `FederationActivity` rows first, and then invoke `submit_task`. Guard `dispatch_collection_update` with `if getattr(item, "is_hidden", False): return` and invoke dispatch helpers (wrapped in `try/except`) on item create/delete and manifestation metadata updates.

## Risks / Trade-offs

- **[Risk] Outbound dispatch errors affecting primary item/manifestation mutations** → **Mitigation:** Wrap all calls to `dispatch_collection_update` and `dispatch_metadata_update` in non-blocking `try/except` blocks after the primary database commit so federation errors never fail local catalog operations.

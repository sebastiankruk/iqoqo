## 1. Scanner Manual Text Search Fix & `local_barcode` Owner Scoping

- [x] 1.1 Update `_validate_scan_request` in `app/api/scanner.py` to permit requests when `payload.meta` is a non-empty dictionary containing a title (`title` or `Title`), and ensure `lookup_barcode_preview` sets `cand.setdefault("data_source", "search")` on all normalized candidates
- [x] 1.2 Update `frontend/components/scanner/success-card.tsx` and `frontend/app/scan/page.tsx` to strip hyphens/spaces before testing barcode format, preserve `data_source` on disambiguation selection, and pass `meta: hasMetadata ? meta : undefined` in `handleAdd`
- [x] 1.3 Scope `Item.local_barcode` queries in `_find_locally` and `lookup_barcode_preview` (`app/api/scanner.py`) to `Item.owner_id == getattr(g, "user_id", None)` using SQLAlchemy 2.0 `select(Item)`, and add regression tests in `tests/test_item_local_barcode.py` and `tests/test_scanner_manual_search.py`

## 2. ActivityPub Inbox & Handler Security Hardening

- [x] 2.1 Enforce `actor_uri == object_uri` in `handle_delete`, validate follow direction in `handle_accept` and `handle_reject` so remote actors cannot self-approve inbound `FollowStatus.PENDING` requests, and handle `IntegrityError` in `_get_or_create_actor` / `handle_follow` in `app/core/federation_handlers.py`
- [x] 2.2 Enforce raw-byte `FEDERATION_MAX_PAYLOAD_BYTES` (100KB) check via `request.get_data(cache=True)` in `receive_inbox` (`app/api/federation.py`), validate target `user_uuid`/`username` existence and `federated_profile` consent on per-actor inbox routes, and reset `activity_rec = None` on DB commit failure
- [x] 2.3 Add unit tests for chunked oversized payload rejection, unconsented per-actor inbox 404, unauthorized `Delete` rejection, and spoofed `Accept(Follow)` rejection in `tests/test_federation_inbox_outbox.py` and `tests/test_federation_handlers.py`

## 3. Federation Metadata Sync Isolation, Sanitization & Admin Cleanup

- [x] 3.1 Verify `urlparse(remote_id).netloc` matches the local instance domain before resolving `/manifestation/<int>` in `resolve_local_manifestation` (`app/core/federation_sync.py`), sanitize inbound strings with `bleach.clean(..., tags=[], strip=True)`, and validate `http(s)` schemes on `cover_url` in `sync_manifestation`
- [x] 3.2 Gate plaintext HTTP fallback and internal Docker hostname netloc rewrites strictly on `FEDERATION_ALLOW_LOOPBACK == "true"` (and exact local dev hosts) in `app/core/federation_discovery.py` and `app/api/federation.py`, and delete dependent `FederationFollower` / `FederationActor` rows before deleting `FederationInstance` in `app/api/admin.py`
- [x] 3.3 Add unit tests for foreign `/manifestation/<id>` collision rejection, `bleach` HTML stripping, `javascript:` `cover_url` rejection, and instance deletion with linked actors in `tests/test_federation_trust_sync.py` and `tests/test_federation_discovery_admin.py`

## 4. Celery `federation` Queue Consumption, Delivery Status & Outbound Fan-Out

- [x] 4.1 Add `-Q celery,federation` to Celery worker commands in `docker-compose.yml`, `docker-compose.override.yml`, and `docker-compose.federation-preview.yml`
- [x] 4.2 Update `deliver_activity` in `app/core/federation_tasks.py` to check `200 <= resp.status_code < 300`, record `federation_delivery_failures_total` on failure, and mark failed deliveries `ActivityStatus.FAILED`
- [x] 4.3 Refactor `_queue_and_deliver` in `app/core/federation_dispatch.py` to batch-load `FederationActor` rows (eliminating N+1 queries) and commit `FederationActivity` rows before calling `submit_task`; add `not item.is_hidden` guard to `dispatch_collection_update`, enrich outbound manifestation metadata payload, and wire non-blocking dispatch calls into item creation/deletion and manifestation updates

## 5. Tombstone Session Safety, Key Rotation Cooldown, Migration & Changelog

- [x] 5.1 Call `db.session.expunge(first_audit)` before mutating `first_audit.diff` in `get_entity_tombstone` (`app/core/frbr_merge.py`) and enforce a 60-second `last_fetched_at` cooldown + DB persistence for rotated keys in `verify_request` (`app/core/http_signatures.py`)
- [x] 5.2 Add pre-constraint deduplication of `(local_user_id, remote_actor_id)` and inspector existence guards to `migrations/versions/v0_9_1_followers_unique.py`
- [x] 5.3 Populate `## [0.9.1]` release notes in `docs/CHANGELOG.md` and verify all backend (`pytest`) and frontend (`vitest`) test suites and `make lint` pass

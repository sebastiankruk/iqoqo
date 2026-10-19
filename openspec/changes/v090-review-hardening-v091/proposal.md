## Why

The v0.9.0 release code review (PR #344) identified several architectural, resilience, and UX follow-up tasks that do not block the initial v0.9.0 merge once critical security/SRE hotfixes are applied. These deferred items must be scheduled and implemented in v0.9.1 alongside the ActivityPub Inbox/Outbox pipeline (`C76`) and Trust Graph (`C77`) to ensure long-term stability, robust federation error recovery, complete internationalization, and strict database integrity.

## What Changes

- **Key Cache Refresh on Verification Failure**: When an inbound HTTP signature fails verification against a cached public key, re-fetch the remote actor document to handle remote key rotation gracefully.
- **WebFinger Domain Matching & Canonical Profile URLs**: Validate that the `@domain` in `acct:user@domain` matches the instance domain, and link `rel="http://webfinger.net/rel/profile-page"` to canonical Next.js route `/u/{username}` rather than `/user/{username}`.
- **Outbound Federation Retry with Exponential Backoff**: Add `tenacity` retry with exponential backoff and explicit connect/read timeouts `(10s, 30s)` to `FederationClient.post_to_inbox`.
- **Unified Base URL Configuration**: Ensure `FEDERATION_BASE_URL` is consistently respected across `app/config.py`, `app/api/profile.py`, and `app/api/federation.py`.
- **Follower Composite Unique Constraint & Check Migration**: Add unique constraint on `FederationFollower(local_user_id, remote_actor_id)` and ensure Alembic migration for `check_user_default_item_visibility` is in sync with model `CheckConstraint`.
- **Multi-Hop Tombstone Chaining**: Extend `frbr_merge.py` and `public_rdf.py` to recursively follow chained `owl:sameAs` / ActivityStreams `Move` tombstones to their surviving entity.
- **Scanner Physical Barcode Lookup**: Extend scanner flow to query and resolve `Item.local_barcode` in addition to ISBN/UPC barcodes.
- **Frontend i18n & E2E Live-Instance Testing**: Localize hardcoded strings in `ProfilePage`, `FederationConsentSettings`, and `EditItemDialog` with `en.json` and `pl.json` keys, and update multi-instance Playwright tests to exercise the live secondary peer container.

## Capabilities

### Modified Capabilities
- `activitypub-discovery-and-signatures`: Add public key cache refresh on signature verification failure, strict WebFinger domain verification, `/u/` profile URL normalization, and exponential backoff on outbound inbox delivery.
- `federation-schema-and-keys`: Enforce composite unique constraint on `FederationFollower(local_user_id, remote_actor_id)` and synchronize Alembic check constraint migration for `default_item_visibility`.
- `iri-immutability`: Support multi-hop tombstone resolution on chained entity merges.
- `item-local-barcode`: Support scanning and resolving physical exemplar `local_barcode` tags in the barcode scanner workflow.

## Impact

- `app/core/http_signatures.py`: Key re-fetch hook on signature failure.
- `app/core/federation_client.py`: Retries with exponential backoff on network failures.
- `app/api/federation.py`: WebFinger domain verification and canonical URL links.
- `app/db/federation.py` & Alembic migrations: Composite unique constraint on followers.
- `app/core/frbr_merge.py` & `app/api/public_rdf.py`: Recursive tombstone traversal.
- `app/api/scanner.py`: Scanner query for existing `Item.local_barcode`.
- `frontend/`: Localization keys in `en.json`/`pl.json` and components (`ProfilePage`, `FederationConsentSettings`, `EditItemDialog`).

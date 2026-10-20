## Context

See proposal.md. The v0.9.0 release provides foundational S2S ActivityPub, FRBR entity identifiers, and local barcodes. The review highlighted areas where resilience against network glitches, key rotation, and edge-case database inconsistencies can be improved in v0.9.1 without altering the core v0.9.0 architecture.

## Goals / Non-Goals

**Goals:**
- Provide automatic public key cache invalidation and re-fetch when signature verification fails due to key rotation.
- Standardize WebFinger domain enforcement and ensure profile URLs link strictly to `/u/{username}`.
- Equip `FederationClient` with exponential backoff retries via `tenacity`.
- Add database-level unique constraint on `FederationFollower` to guarantee idempotent follower tracking.
- Enable scanner resolution for `Item.local_barcode` values.
- Support recursive tombstone traversal for chained entity merges.
- Localize frontend strings across `ProfilePage`, `FederationConsentSettings`, and `EditItemDialog`.

**Non-Goals:**
- Full implementation of the Celery inbox task pipeline (part of `C76`).
- Trust Graph metadata synchronization (part of `C77`).
- Admin Federation dashboard UI (part of `C78`).

## Decisions

- **Decision 1: Single Re-fetch on Signature Failure**
  - *Rationale*: If a signature fails, re-fetching the actor document once prevents permanent failure when a peer rotates keys. We bound re-fetches to at most 1 per request to prevent outbound amplification attacks.
  - *Alternative*: Periodically polling all remote actors. Rejected due to unnecessary outbound traffic and resource consumption.

- **Decision 2: Tenacity Retry on Outbound Federation**
  - *Rationale*: Transient network glitches and remote server restarts are common in federated environments. `tenacity` provides standard, jittered exponential backoff.
  - *Alternative*: Manual while-loops with `time.sleep()`. Rejected because `tenacity` is already an established project dependency.

- **Decision 3: Recursive Tombstone Traversal in Python**
  - *Rationale*: Deduplication merges can occur in chains ($A \to B \to C$). When dereferencing $A$, a depth-limited (max 5) query follows the `sameAs` / `Move` chain to return target $C$ directly with HTTP 301/410.
  - *Alternative*: Recursive SQL Common Table Expressions (CTE). While possible, depth is rarely $>2$ and Python loop handles both ActivityStreams and RDF serialization cleanly.

- **Decision 4: Database Unique Constraint via Alembic**
  - *Rationale*: A composite unique constraint on `(local_user_id, remote_actor_id)` in PostgreSQL guarantees data integrity against concurrent duplicate Follow activities.

## Risks / Trade-offs

- [Risk: Outbound Re-fetch DoS] → Mitigate by caching negative results temporarily and enforcing maximum 1 actor re-fetch per incoming request.
- [Risk: Infinite Tombstone Loops] → Mitigate by cycle detection (visited set) and a max depth of 5 hops in merge traversal.
- [Risk: Retries Blocking Worker] → Mitigate by setting short connect (10s) and read (30s) timeouts and offloading deliveries to Celery in `C76`.

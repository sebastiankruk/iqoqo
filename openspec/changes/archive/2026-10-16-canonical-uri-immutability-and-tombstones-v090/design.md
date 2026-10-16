## Context

v0.8.0 introduced canonical IRIs in `app/core/iri.py`. In v0.9.0, these IRIs become public identity endpoints across the Fediverse.

## Goals / Non-Goals

**Goals:**
- Decouple Actor IRI permanence from display username changes.
- Ensure remote Fediverse instances can track merged or relocated FRBR entities without dangling links.

**Non-Goals:**
- Full ActivityPub server-to-server inbox delivery (handled in C76).
- Mutable custom vanity domains per user.

## Decisions

### Canonical Actor IRI Scheme
* **Decision**: Actor IRIs format as `https://{domain}/api/federation/actor/u/{user_uuid}` with `/api/federation/actor/{username}` functioning as a stable lookup redirect.
* **Rationale**: Prevents broken follower links on username change.

### Tombstone Serialization
* **Decision**: Merged entities leave a tombstone record in `frbr_merge` audit log and serialize `as:Move` (target = target_iri) when requested via ActivityPub.
* **Rationale**: Standard ActivityPub migration protocol.

## Risks / Trade-offs

- ('[Risk] Legacy links using username-based IRIs break', 'Mitigation: Add permanent 301 redirection from legacy username endpoints to canonical UUID endpoints.')

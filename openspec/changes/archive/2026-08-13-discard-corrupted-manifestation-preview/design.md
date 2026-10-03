# Design: Discard Corrupted Manifestation Records in Scanner Preview

## Context

When looking up barcodes using `/api/lookup/<query>`, the scanner API queries the database for existing `Manifestation` records before calling external metadata providers. Due to past bugs or partial ingests, some database records contain empty metadata dictionary structures (`{'imageLinks': {}, 'pageCount': None, 'industryIdentifiers': []}`).

When `_normalize_preview_meta` processes these records, it sets `"title": "Unknown Title"` and leaves `author` empty, causing the frontend scanner UI to display "Unknown Title" for books that actually exist in external APIs.

## Goals / Non-Goals

**Goals:**

- Detect local DB manifestations with corrupted or missing metadata during scanner preview lookup.
- Bypass local cache hit return when title is "Unknown Title" and author is absent.
- Ensure external APIs (Google Books / Open Library / Discogs) are queried for rich metadata.
- Gracefully handle database collisions when returning preview results linked to existing manifestation IDs.

**Non-Goals:**

- Bulk migration script for existing database manifestations.
- Modifying FRBR Work or Expression schemas.

## Decisions

### Decision 1: Self-healing preview cache miss condition
Instead of throwing database errors or requiring manual SQL cleanup, `lookup_barcode_preview` evaluates normalized metadata. If `title == "Unknown Title"` and `author` is `None`, `manifestation` is set to `None`, forcing the lookup to fall through to external providers.

*Alternatives Considered:*

- *Bulk SQL deletion:* Risk of deleting user-created custom items.
- *Strict JSON schema validation:* Too rigid for legitimate minimal custom entities.

## Risks / Trade-offs

- [Risk] Duplicate lookup traffic to external APIs for items that truly lack author/title. → Mitigation: Only triggers if title is explicitly `"Unknown Title"` AND `author` is `None`.

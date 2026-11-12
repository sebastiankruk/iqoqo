## Context

See `proposal.md` and `.context/notes/plan/Improving sharing link for AI.md`. The work stays inside Work -> Expression -> Manifestation -> Item: audio `content_type` is preserved on the Expression (`music`/`audio`, never `text`), pressing properties are exposed from the Manifestation.

## Goals / Non-Goals

**Goals:**

- Zero-truncation, pressing-accurate ingestion of shared collections by headerless AI fetchers.
- Audio pressing triples in RDF and in SSR JSON-LD.
- Correct format badges.

**Non-Goals:**

- Raising the `feed.xml` 50-item cap.
- Changing share-token issuance or revocation.
- Emitting hidden or non-public items.

## Decisions

1. **Shared visibility guard:** One query helper applies `Item.is_hidden == False` and `visibility == "public"` for every format.
2. **Limits:** API `limit` clamps to `1..2000`; SSR JSON-LD embeds up to `1000` items. Queries use SQL `LIMIT`/`OFFSET`, never in-memory slicing.
3. **Format negotiation by query string:** `?format=jsonld|turtle|rdfxml`; unknown values return `{"error": "...", "code": 400}`.
4. **Audio vocabulary:** `schema:MusicAlbum`/`schema:MusicRelease`, `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, `schema:gtin13`, `schema:datePublished`, `schema:countryOfOrigin`, `iqoqo:matrixRunout`, `owl:sameAs` for Discogs/MusicBrainz. Missing fields are omitted, never fabricated.
5. **Badge resolution order:** top-level `format`, then `manifestation_meta.format`, then `content_type`-derived label; never default to "Book" for non-book content.
6. **Discovery:** `<link rel="alternate" type="application/ld+json">` in the head plus a visible feed link.

## Risks / Trade-offs

- **[Risk] Large SSR payload** -> Mitigation: 1,000-item cap and server-side only.
- **[Risk] Hidden-item leakage via new formats** -> Mitigation: shared guard plus per-format tests.
- **[Risk] Collections above 1,000 items are truncated in SSR** -> Mitigation: JSON-LD feed link (`limit` up to `2000`) documented as the complete source.

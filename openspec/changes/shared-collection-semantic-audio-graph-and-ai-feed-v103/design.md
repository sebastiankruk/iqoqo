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
6. **Discovery & Crawler Isolation (`/api/` stays private):** `<link rel="alternate" type="application/ld+json">` and visible feed links point to `/share/[token]/catalog.jsonld` and `/share/[token]/feed.xml` (Next.js `rewrites` to Flask `/api/public/share/...`), keeping `Disallow: /api/` in `frontend/public/robots.txt`.
7. **Compact SSR Catalog Index & Element Ordering:** `<SharedCollectionClient>` renders a compact `<details open data-testid="shared-catalog-index">` index above `<CollectionGrid>`, and `<JsonLdScript>` renders **after** `<SharedCollectionClient>`. Why: heavy `<ItemCard>` cards (~1.5 KB/card) plus an 84 KB leading `<script type="application/ld+json">` cause LLM web fetchers (which strip `<script>` tags and truncate around ~150 KB HTML / ~65 KB body) to cut off around item ~45; the compact index keeps 365+ items within ~40 KB at the top of the page.
8. **Cloudflare Edge & AI Crawl Control:** SREs deploying behind Cloudflare must disable Cloudflare Managed `robots.txt` blocking for `Google-Extended` / `GoogleOther` / `Google-CloudVertexBot` and whitelist `/share/` in Custom Rule 2 (`deploy/cloudflare-semantic-federation-rules.md`, verified by `scripts/verify_cloudflare_rules.sh`).

## Risks / Trade-offs

- **[Risk] Large SSR payload** -> Mitigation: 1,000-item cap, compact ~100-byte/item catalog index before the card grid, and `<JsonLdScript>` moved after the grid.
- **[Risk] Hidden-item leakage via new formats** -> Mitigation: shared guard plus per-format tests.
- **[Risk] Collections above 1,000 items are truncated in SSR** -> Mitigation: `/share/[token]/catalog.jsonld` (`limit` up to `2000`) documented as the complete machine-readable source.
- **[Risk] Cloudflare Managed `robots.txt` overrides origin `robots.txt`** -> Mitigation: documented SRE runbook and automated live check in `scripts/verify_cloudflare_rules.sh`.

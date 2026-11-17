# Tasks: Shared Collection Semantic Audio Graph & AI Feed (`C118` — Target: `v1.0.3`)

## 1. Batch 1 — Backend RDF and API

- [x] 1.1 Add `_emit_audio_rdf_triples(g, m_uri, m_elem, meta)` to `app/core/frbr_service.py` and call it from `build_collection_rdf_graph()` for audio manifestations.
- [x] 1.2 Enrich `fetch_shared_collection_by_token()` in `app/api/public_items.py` with top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, `country`; apply the `is_hidden == False` + `visibility == "public"` guard with SQL `LIMIT`/`OFFSET`.
- [x] 1.3 Add `?format=jsonld|turtle|rdfxml` and `?limit=` (max `2000`) to `GET /api/public/share/<token>` and `GET /api/public/rdf/share/<token>`; JSON `400` for unknown formats; update `app/api/docs.py`.

## 2. Batch 2 — Frontend SSR and Badge

- [x] 2.1 Fix badge resolution in `shared-collection-client.tsx` / item card (top-level `format`, then `manifestation_meta.format`, then `content_type`).
- [x] 2.2 Update `frontend/app/share/[token]/page.tsx` and `buildCollectionJsonLd()` in `frontend/lib/schema-org.ts` to embed up to 1,000 items with `MusicAlbum`/`MusicRelease` properties, placing `<JsonLdScript>` after `<SharedCollectionClient>`.
- [x] 2.3 Add the "JSON-LD / AI Feed" link in `public-feed-button.tsx` and `<link rel="alternate" type="application/ld+json">` in the page head targeting non-`/api/` `/share/[token]/catalog.jsonld` and `/share/[token]/feed.xml` (Next.js rewrites in `frontend/next.config.ts`); keep `Disallow: /api/` in `frontend/public/robots.txt`; add `en.json`/`pl.json` strings.
- [x] 2.4 Render compact SSR `<details open data-testid="shared-catalog-index">` above `<CollectionGrid>` in `shared-collection-client.tsx` so 365+ items fit before ~150 KB HTML fetcher truncation limits.
- [x] 2.5 Update `deploy/cloudflare-semantic-federation-rules.md`, `scripts/verify_cloudflare_rules.sh`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, and `docs/OPERATIONS.md` with Cloudflare WAF + AI Crawl Control / Managed `robots.txt` SRE deployment guidance.

## 3. Batch 3 — Tests

- [x] 3.1 `tests/test_public_rdf_audio.py` and `tests/test_api_public_extended.py`: 365-item full fetch, limit clamp, hidden exclusion, unknown-format `400`, pressing triples present/omitted.
- [x] 3.2 `shared-collection-client.test.tsx` and `schema-org.test.ts`: Vinyl/CD badges never "Book"; `MusicAlbum`/`MusicRelease` nodes emitted.
- [x] 3.3 Verify with `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`; add a `docs/CHANGELOG.md` entry.

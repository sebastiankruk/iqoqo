# Tasks: Shared Collection Semantic Audio Graph & AI Feed (`C118` — Target: `v1.0.3`)

## 1. Batch 1 — Backend RDF and API

- [ ] 1.1 Add `_emit_audio_rdf_triples(g, m_uri, m_elem, meta)` to `app/core/frbr_service.py` and call it from `build_collection_rdf_graph()` for audio manifestations.
- [ ] 1.2 Enrich `fetch_shared_collection_by_token()` in `app/api/public_items.py` with top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, `country`; apply the `is_hidden == False` + `visibility == "public"` guard with SQL `LIMIT`/`OFFSET`.
- [ ] 1.3 Add `?format=jsonld|turtle|rdfxml` and `?limit=` (max `2000`) to `GET /api/public/share/<token>` and `GET /api/public/rdf/share/<token>`; JSON `400` for unknown formats; update `app/api/docs.py`.

## 2. Batch 2 — Frontend SSR and Badge

- [ ] 2.1 Fix badge resolution in `shared-collection-client.tsx` / item card (top-level `format`, then `manifestation_meta.format`, then `content_type`).
- [ ] 2.2 Update `frontend/app/share/[token]/page.tsx` and `buildCollectionJsonLd()` in `frontend/lib/schema-org.ts` to embed up to 1,000 items with `MusicAlbum`/`MusicRelease` properties.
- [ ] 2.3 Add the "JSON-LD / AI Feed" link in `public-feed-button.tsx` and `<link rel="alternate" type="application/ld+json">` in the page head; add `en.json`/`pl.json` strings.

## 3. Batch 3 — Tests

- [ ] 3.1 `tests/test_public_rdf_audio.py` and `tests/test_api_public_extended.py`: 365-item full fetch, limit clamp, hidden exclusion, unknown-format `400`, pressing triples present/omitted.
- [ ] 3.2 `shared-collection-client.test.tsx` and `schema-org.test.ts`: Vinyl/CD badges never "Book"; `MusicAlbum`/`MusicRelease` nodes emitted.
- [ ] 3.3 Verify with `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`; add `docs/CHANGELOG.md` entry.

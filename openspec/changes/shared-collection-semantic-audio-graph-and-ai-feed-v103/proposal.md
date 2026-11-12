## Why

AI web fetchers (NotebookLM, Gemini) read `/share/[token]` with a plain `GET` (`Accept: text/html`), cannot set `Accept: application/ld+json`, and do not scroll. For a 365-item audio collection this caused four defects (source: `.context/notes/plan/Improving sharing link for AI.md`):

- **"Book" badge bug:** missing/nested format fields (`manifestation_meta.format` vs top-level `format`/`content_type`) fall back to "Book" in `shared-collection-client.tsx` and `buildCollectionJsonLd()`.
- **Truncation:** only the first page hydrates; the rest relies on client-side infinite scroll. The RSS feed (`/api/public/share/<token>/feed.xml`) is capped at 50 items, fewer than the page.
- **No audio pressing metadata:** `build_collection_rdf_graph()` has `_emit_lego_rdf_triples` and `_emit_cartographic_rdf_triples` but no `_emit_audio_rdf_triples`; `ean/upc`, format, label, catalog number, release year, and Discogs/MusicBrainz `sameAs` are absent from both DOM and JSON-LD.
- **No query-param negotiation:** headerless fetchers need `?format=jsonld&limit=` or complete SSR JSON-LD.

## What Changes

- **Batch 1 — Backend:** Add `_emit_audio_rdf_triples(g, m_uri, m_elem, meta)` emitting `schema:MusicAlbum`/`schema:MusicRelease`, `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, `schema:gtin13`, `schema:datePublished`, `schema:countryOfOrigin`, `iqoqo:matrixRunout`, and `owl:sameAs` (Discogs/MusicBrainz). Enrich `fetch_shared_collection_by_token()` (`app/api/public_items.py`) so each item carries top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, `country`. Accept `?format=jsonld|turtle|rdfxml` and `?limit=` (up to `2000`) on `GET /api/public/share/<token>` and `GET /api/public/rdf/share/<token>`.
- **Batch 2 — Frontend:** Fix badge resolution so audio shows Vinyl/CD/SACD, never "Book". Make `/share/[token]` SSR embed the whole shared collection (up to 1,000 items) in JSON-LD via `buildCollectionJsonLd()`. Add a "JSON-LD / AI Feed" link next to the RSS icon in `public-feed-button.tsx` and `<link rel="alternate" type="application/ld+json">` in the page head.
- **Batch 3 — Tests:** `tests/test_public_rdf_audio.py`, `tests/test_api_public_extended.py`, `shared-collection-client.test.tsx`, `schema-org.test.ts`.
- **Unchanged:** `feed.xml` stays capped at 50 items (documented).

## Capabilities

### New Capabilities

- `shared-collection-ai-feed`: Audio pressing RDF/JSON-LD, query-param content negotiation on share endpoints, full SSR JSON-LD on `/share/[token]`, and correct media badges.

### Modified Capabilities

<!-- Tracked under the new shared-collection-ai-feed capability for v1.0.3 -->

## Impact

- **Backend:** `app/core/frbr_service.py`, `app/api/public_items.py`, `app/api/public_rdf.py`, `app/api/docs.py`
- **Frontend:** `frontend/app/share/[token]/page.tsx`, `frontend/components/public/shared-collection-client.tsx`, `frontend/lib/schema-org.ts`, `frontend/components/ui/public-feed-button.tsx`
- **Privacy:** only `is_hidden == False` items in `visibility == "public"` collections are emitted
- **FRBR:** `content_type` stays `music`/`audio` on Expression; pressing properties live on Manifestation

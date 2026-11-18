## Why

AI web fetchers (NotebookLM, Gemini App) read `/share/[token]` with a plain `GET` (`Accept: text/html`), cannot set custom `Accept: application/ld+json` headers, strip `<script type="application/ld+json">` and `<svg>` tags during DOM sanitization (requiring `<span className="sr-only">` anchor text inside icon-only `<a>` links), reject non-`text/html` MIME types (`application/ld+json`, `application/json`, `text/plain`) with `PERMISSION_DENIED` / `URL_FETCH_STATUS_MISC_ERROR`, cap extracted text per page (~60 items per mini-page), and enforce both a strict URL-construction guardrail and a query-string block on discovered pagination URLs such as `?format=jsonld&page=3..7`. Meanwhile, human visitors need a clean, fast, paginated collection view without raw metadata text dumps above the grid or mismatched button sizes (source: `.context/notes/plan/Improving sharing link for AI.md`, `.context/notes/AI/gemini/sharing-collection-as-metadata.md`, and `.context/notes/AI/gemini/Jsonld-load-test.md`).

## What Changes

- **Batch 1 — Backend RDF, Audio Triples & SQL Pagination (`app/core/frbr_service.py`, `app/api/public_items.py`, `app/api/public_rdf.py`, `app/api/docs.py`):**
  - Add `_emit_audio_rdf_triples(g, m_uri, m_elem, meta)` emitting `schema:MusicAlbum`/`schema:MusicRelease`, `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, `schema:gtin13`, `schema:datePublished`, `schema:countryOfOrigin`, `iqoqo:matrixRunout`, and `owl:sameAs` (Discogs/MusicBrainz).
  - Enrich `fetch_shared_collection_by_token()` and `_serialize_shared_collection_item()` with top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, `country`, and `lod_links`.
  - Add SQL `page` and `per_page` (`LIMIT`/`OFFSET`) pagination to `GET /api/public/share/<token>` returning `total`, `page`, `per_page`, and `pages` (while preserving `?limit=` and `?format=jsonld|turtle|rdfxml` up to `2000` for RDF exports), and recognize both `Accept: application/ld+json` and `Accept: application/json+ld` (honoring `page`/`per_page` when provided).
- **Batch 2 — Frontend UX Polish, Windowed Pagination & Query-Free `/share/[token]/jsonld/[page]` Mini-Page (`frontend/app/share/[token]/page.tsx`, `frontend/app/share/[token]/jsonld/[page]/page.tsx`, `frontend/lib/share-server.tsx`, `frontend/lib/pagination.ts`, `frontend/components/public/shared-collection-client.tsx`, `frontend/components/ui/share-button.tsx`, `frontend/components/ui/public-feed-button.tsx`, `frontend/lib/schema-org.ts`):**
  - **Human Share Page UX:** Remove the raw `<details open>` catalog index text block above the cover grid. Paginate `/share/[token]?page=N` (`per_page = 48`) with a windowed pagination bar showing **at most 10 page links** (`first`, up to `8` around current page, `last`), while keeping embedded `<JsonLdScript>` on each HTML page for search engines.
  - **Uniform Hero Buttons & Subtle RDF Icon Button:** Make `<ShareButton>` and `<PublicFeedButton>` identical height (`h-9`). Render the JSON-LD / RDF feed trigger as a subtle, compact **RDF icon button** (`w-9 h-9` with W3C RDF Flyer SVG icon and tooltip) linking to the **full, query-free absolute URL** `https://<host>/share/<token>/jsonld/1`, accompanied by an `sr-only` `<nav aria-label="AI JSON-LD pages">` exposing up to 10 windowed links (`/share/<token>/jsonld/1` … `/N`) directly on `/share/<token>`.
  - **Query-Free Paginated HTML-Wrapped JSON-LD Mini-Page (`/share/[token]/jsonld/[page]`, with `?format=jsonld&page=N` alias):** Render a minimal Next.js `text/html` document **without `<Navbar />` or `<Footer />`**, containing:
    1. A top `<nav aria-label="JSON-LD Pages">` with **at most 10 full, query-free absolute `<a href="https://<host>/share/<token>/jsonld/<K>">` links** (`first`, up to `8` around current page, `last`) so Gemini App's URL-construction & query-string guardrails can legally follow every page.
    2. A `<pre id="jsonld-payload">` block with minified Schema.org JSON-LD (`per_page = 60` items, well under Gemini's single-fetch limit) including `totalItems`, `page`, `perPage`, `totalPages`, `nextPage`, and the windowed `pages` array of full, query-free absolute URLs.
- **Batch 3 — Canonical HTTP Content Negotiation on `/share/[token]` & `/share/[token]/jsonld/[page]`, Non-`/api/` Crawler Boundary & Cloudflare SRE Docs (`deploy/nginx.conf`, `deploy/nginx.conf.example`, `frontend/proxy.ts`, `frontend/public/robots.txt`, `deploy/cloudflare-semantic-federation-rules.md`, `scripts/verify_cloudflare_rules.sh`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`):**
  - Support true HTTP Content Negotiation on `/share/<token>` (and `/share/<token>?page=N`) as well as `/share/<token>/jsonld/<page>`: when `Accept` contains `application/ld+json`, `application/json+ld`, `text/turtle`, `application/n-triples`, or `application/rdf+xml`, `frontend/proxy.ts` and Nginx route directly to Flask `/api/public/share/<token>` and return raw RDF/JSON-LD (`Content-Type: application/ld+json`).
  - Keep `Disallow: /api/` and `Allow: /share/` in `frontend/public/robots.txt`; route `/share/<token>/catalog.jsonld` and `/share/<token>/feed.xml` via Nginx and runtime `frontend/proxy.ts` (`FLASK_API_URL`) for standard RDF/RSS consumers.
  - Document Cloudflare WAF Custom Rule 2 and AI Crawl Control (`Search`/`Training`/`Agents` + `Enable Bot Preference Sync`) for SRE deployments.
- **Batch 4 — Tests (`tests/test_public_rdf_audio.py`, `frontend/__tests__/components/public/shared-collection-client.test.tsx`, `frontend/__tests__/app/ssr-jsonld-safety.test.tsx`, `frontend/__tests__/proxy.test.ts`):**
  - Verify SQL pagination, 10-page window helper (`first`, `8` around current, `last`), absence of `<details>` text dump on human view, uniform button sizing + subtle RDF icon button with full query-free absolute `/share/<token>/jsonld/1` URL, and chromeless `/share/[token]/jsonld/[page]` (plus `?format=jsonld&page=N` alias) mini-page rendering `<pre id="jsonld-payload">`.

## Capabilities

### New Capabilities

- `shared-collection-ai-feed`: Audio pressing RDF/JSON-LD, SQL-paginated shared collections with 10-page windowed navigation, chromeless query-free `/share/[token]/jsonld/[page]` (and `?format=jsonld&page=N` alias) HTML-wrapped JSON-LD mini-page for headerless AI agents, and harmonized share hero buttons with a compact RDF icon button.

### Modified Capabilities

<!-- Tracked under the new shared-collection-ai-feed capability for v1.0.3 -->

## Impact

- **Backend:** `app/core/frbr_service.py`, `app/api/public_items.py`, `app/api/public_rdf.py`, `app/api/docs.py`
- **Frontend:** `frontend/app/share/[token]/page.tsx`, `frontend/app/share/[token]/jsonld/[page]/page.tsx`, `frontend/lib/share-server.tsx`, `frontend/lib/pagination.ts`, `frontend/components/public/shared-collection-client.tsx`, `frontend/components/ui/share-button.tsx`, `frontend/components/ui/public-feed-button.tsx`, `frontend/lib/schema-org.ts`, `frontend/proxy.ts`, `frontend/public/robots.txt`
- **Ops & Docs:** `deploy/nginx.conf`, `deploy/nginx.conf.example`, `deploy/cloudflare-semantic-federation-rules.md`, `scripts/verify_cloudflare_rules.sh`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`
- **Privacy:** only `is_hidden == False` items in `visibility == "public"` collections are emitted
- **FRBR:** `content_type` stays `music`/`audio` on Expression; pressing properties live on Manifestation

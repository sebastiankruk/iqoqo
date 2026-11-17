## Why

AI web fetchers (NotebookLM, Gemini App) read `/share/[token]` with a plain `GET` (`Accept: text/html`), cannot set custom `Accept: application/ld+json` headers, strip `<script type="application/ld+json">` tags during DOM sanitization, reject non-`text/html` MIME types (`application/ld+json`, `application/json`, `text/plain`) with `PERMISSION_DENIED` / `URL_FETCH_STATUS_MISC_ERROR`, cap extracted text per page at ~16 KB, and enforce a strict URL-construction guardrail (they can only follow complete URLs explicitly present in a previously fetched page's DOM). Meanwhile, human visitors need a clean, fast, paginated collection view without raw metadata text dumps above the grid or mismatched button sizes (source: `.context/notes/plan/Improving sharing link for AI.md` and `.context/notes/AI/gemini/sharing-collection-as-metadata.md`).

## What Changes

- **Batch 1 — Backend RDF, Audio Triples & SQL Pagination (`app/core/frbr_service.py`, `app/api/public_items.py`, `app/api/public_rdf.py`, `app/api/docs.py`):**
  - Add `_emit_audio_rdf_triples(g, m_uri, m_elem, meta)` emitting `schema:MusicAlbum`/`schema:MusicRelease`, `schema:musicReleaseFormat`, `schema:recordLabel`, `schema:catalogNumber`, `schema:gtin13`, `schema:datePublished`, `schema:countryOfOrigin`, `iqoqo:matrixRunout`, and `owl:sameAs` (Discogs/MusicBrainz).
  - Enrich `fetch_shared_collection_by_token()` and `_serialize_shared_collection_item()` with top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, `country`, and `lod_links`.
  - Add SQL `page` and `per_page` (`LIMIT`/`OFFSET`) pagination to `GET /api/public/share/<token>` returning `total`, `page`, `per_page`, and `pages` (while preserving `?limit=` and `?format=jsonld|turtle|rdfxml` up to `2000` for RDF exports), and recognize both `Accept: application/ld+json` and `Accept: application/json+ld` (honoring `page`/`per_page` when provided).
- **Batch 2 — Frontend UX Polish, Windowed Pagination & `?format=jsonld` Mini-Page (`frontend/app/share/[token]/page.tsx`, `frontend/components/public/shared-collection-client.tsx`, `frontend/components/ui/share-button.tsx`, `frontend/components/ui/public-feed-button.tsx`, `frontend/lib/schema-org.ts`):**
  - **Human Share Page UX:** Remove the raw `<details open>` catalog index text block above the cover grid. Paginate `/share/[token]?page=N` (`per_page = 48`) with a windowed pagination bar showing **at most 10 page links** (`first`, up to `8` around current page, `last`), while keeping embedded `<JsonLdScript>` on each HTML page for search engines.
  - **Uniform Hero Buttons & Subtle RDF Icon Button:** Make `<ShareButton>` and `<PublicFeedButton>` identical height (`h-9`). Render the JSON-LD / RDF feed trigger as a subtle, compact **RDF icon button** (`w-9 h-9` with semantic network/RDF icon and tooltip) linking to the **full absolute URL** `https://<host>/share/<token>?format=jsonld&page=1`.
  - **Paginated HTML-Wrapped JSON-LD Mini-Page (`/share/[token]?format=jsonld&page=N`):** When `?format=jsonld` is passed to `/share/[token]` with `Accept: text/html`, render a minimal Next.js `text/html` document **without `<Navbar />` or `<Footer />`**, containing:
    1. A top `<nav aria-label="JSON-LD Pages">` with **at most 10 full absolute `<a href="https://<host>/share/<token>?format=jsonld&page=K">` links** (`first`, up to `8` around current page, `last`) so Gemini App's URL-construction guardrail can legally follow pages.
    2. A `<pre id="jsonld-payload">` block with minified Schema.org JSON-LD (`per_page = 60` items, well under Gemini's single-fetch limit) including `totalItems`, `page`, `perPage`, `totalPages`, `nextPage`, and the windowed `pages` array of full absolute URLs.
- **Batch 3 — Canonical HTTP Content Negotiation on `/share/[token]`, Non-`/api/` Crawler Boundary & Cloudflare SRE Docs (`deploy/nginx.conf`, `deploy/nginx.conf.example`, `frontend/proxy.ts`, `frontend/public/robots.txt`, `deploy/cloudflare-semantic-federation-rules.md`, `scripts/verify_cloudflare_rules.sh`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`):**
  - Support true HTTP Content Negotiation on `/share/<token>` (and `/share/<token>?page=N`): when `Accept` contains `application/ld+json`, `application/json+ld`, `text/turtle`, `application/n-triples`, or `application/rdf+xml`, `frontend/proxy.ts` and Nginx route directly to Flask `/api/public/share/<token>` and return raw RDF/JSON-LD (`Content-Type: application/ld+json`).
  - Keep `Disallow: /api/` and `Allow: /share/` in `frontend/public/robots.txt`; route `/share/<token>/catalog.jsonld` and `/share/<token>/feed.xml` via Nginx and runtime `frontend/proxy.ts` (`FLASK_API_URL`) for standard RDF/RSS consumers.
  - Document Cloudflare WAF Custom Rule 2 and AI Crawl Control (`Search`/`Training`/`Agents` + `Enable Bot Preference Sync`) for SRE deployments.
- **Batch 4 — Tests (`tests/test_public_rdf_audio.py`, `frontend/__tests__/components/public/shared-collection-client.test.tsx`, `frontend/__tests__/app/ssr-jsonld-safety.test.tsx`, `frontend/__tests__/proxy.test.ts`):**
  - Verify SQL pagination, 10-page window helper (`first`, `8` around current, `last`), absence of `<details>` text dump on human view, uniform button sizing + subtle RDF icon button with full absolute `?format=jsonld&page=1` URL, and chromeless `?format=jsonld&page=N` mini-page rendering `<pre id="jsonld-payload">`.

## Capabilities

### New Capabilities

- `shared-collection-ai-feed`: Audio pressing RDF/JSON-LD, SQL-paginated shared collections with 10-page windowed navigation, chromeless `?format=jsonld&page=N` HTML-wrapped JSON-LD mini-page for headerless AI agents, and harmonized share hero buttons with a compact RDF icon button.

### Modified Capabilities

<!-- Tracked under the new shared-collection-ai-feed capability for v1.0.3 -->

## Impact

- **Backend:** `app/core/frbr_service.py`, `app/api/public_items.py`, `app/api/public_rdf.py`, `app/api/docs.py`
- **Frontend:** `frontend/app/share/[token]/page.tsx`, `frontend/components/public/shared-collection-client.tsx`, `frontend/components/ui/share-button.tsx`, `frontend/components/ui/public-feed-button.tsx`, `frontend/lib/schema-org.ts`, `frontend/proxy.ts`, `frontend/public/robots.txt`
- **Ops & Docs:** `deploy/nginx.conf`, `deploy/nginx.conf.example`, `deploy/cloudflare-semantic-federation-rules.md`, `scripts/verify_cloudflare_rules.sh`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`
- **Privacy:** only `is_hidden == False` items in `visibility == "public"` collections are emitted
- **FRBR:** `content_type` stays `music`/`audio` on Expression; pressing properties live on Manifestation

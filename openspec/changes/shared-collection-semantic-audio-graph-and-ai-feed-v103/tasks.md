## 1. Batch 1 — Backend RDF and SQL Pagination

- [x] 1.1 Add `_emit_audio_rdf_triples(g, m_uri, m_elem, meta)` to `app/core/frbr_service.py` and call it from `build_collection_rdf_graph()` for audio manifestations.
- [x] 1.2 Enrich `fetch_shared_collection_by_token()` in `app/api/public_items.py` with top-level `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, `country`; apply the `is_hidden == False` + `visibility == "public"` guard with SQL `LIMIT`/`OFFSET`.
- [x] 1.3 Add `?format=jsonld|turtle|rdfxml` and `?limit=` (max `2000`) to `GET /api/public/share/<token>` and `GET /api/public/rdf/share/<token>`; JSON `400` for unknown formats; update `app/api/docs.py`.
- [x] 1.4 Add SQL `page` and `per_page` (`LIMIT`/`OFFSET`) pagination + `total` / `pages` counts to `GET /api/public/share/<token>` in `app/api/public_items.py` (supporting `page`/`per_page` on both JSON and RDF/JSON-LD responses, and accepting both `application/ld+json` and `application/json+ld` in `Accept` negotiation) while keeping unpaginated `?limit=` backward-compatible.

## 2. Batch 2 — Frontend UX, 10-Page Windowed Pagination & `?format=jsonld` Mini-Page

- [x] 2.1 Fix badge resolution in `shared-collection-client.tsx` / item card (top-level `format`, then `manifestation_meta.format`, then `content_type`).
- [x] 2.2 Remove the `<details open>` catalog index text block from `frontend/components/public/shared-collection-client.tsx` so `/share/[token]` renders a clean human-first layout.
- [x] 2.3 Harmonize hero button heights (`h-9`) in `frontend/components/ui/share-button.tsx` and `frontend/components/ui/public-feed-button.tsx`; style `variant="jsonld"` as a subtle, compact icon-only RDF button (`w-9 h-9`) linking to the full absolute URL `https://<host>/share/<token>?format=jsonld&page=1`.
- [x] 2.4 Implement `buildPaginationWindow(currentPage, totalPages)` (at most 10 pages: `1`, up to `8` around current page, `totalPages`) and render windowed pagination controls on `/share/[token]?page=N` (`per_page = 48`).
- [x] 2.5 Implement the chromeless `?format=jsonld&page=N` mini-page in `frontend/app/share/[token]/page.tsx` (`per_page = 60`, no `<Navbar />`/`<Footer />`, `<nav aria-label="JSON-LD Pages">` with full absolute links for the 10-page window, and `<pre id="jsonld-payload">` with minified Schema.org JSON-LD).

## 3. Batch 3 — Canonical HTTP Content Negotiation, Crawler Boundary & Cloudflare SRE Docs

- [x] 3.1 Support HTTP Content Negotiation (`Accept: application/ld+json`, `application/json+ld`, `text/turtle`, `application/n-triples`, `application/rdf+xml`) on `/share/<token>` (including `?page=N`) as well as `/share/<token>/catalog.jsonld` and `/share/<token>/feed.xml` via `frontend/proxy.ts` (`FLASK_API_URL`) and `deploy/nginx.conf` / `deploy/nginx.conf.example`, keeping `Disallow: /api/` and `Allow: /share/` in `frontend/public/robots.txt`.
- [x] 3.2 Update `deploy/cloudflare-semantic-federation-rules.md`, `scripts/verify_cloudflare_rules.sh`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, and `docs/OPERATIONS.md` with Cloudflare WAF + AI Crawl Control SRE deployment guidance.

## 4. Batch 4 — Tests

- [x] 4.1 `tests/test_public_rdf_audio.py`: verify SQL `page`/`per_page` pagination (`total`, `pages`), 365-item full RDF fetch, limit clamp, hidden exclusion, unknown-format `400`, and pressing triples.
- [x] 4.2 `frontend/__tests__/components/public/shared-collection-client.test.tsx`, `frontend/__tests__/app/ssr-jsonld-safety.test.tsx`, and `frontend/__tests__/proxy.test.ts`: verify no `<details>` text block on human view, uniform `h-9` hero buttons + subtle RDF icon button with full absolute `?format=jsonld&page=1` link, 10-page window (`first`, `8` around current, `last`), chromeless `?format=jsonld&page=N` mini-page rendering `<pre id="jsonld-payload">`, and runtime `proxy.ts` rewrites.
- [ ] 4.3 Verify with `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`; update `docs/CHANGELOG.md`.

## Context

See `proposal.md`, `.context/notes/plan/Improving sharing link for AI.md`, and `.context/notes/AI/gemini/sharing-collection-as-metadata.md`. Direct testing with the Gemini App revealed four hard constraints of LLM web-browsing tools (`browsing:browse` / `url_context`):

1. **No Custom HTTP Headers:** Skills/prompts cannot instruct the Gemini App to send `Accept: application/ld+json`.
2. **HTML-Only Extractor (`PERMISSION_DENIED` on raw JSON/JSON-LD):** Fetching non-`text/html` MIME types (`application/ld+json`, `application/json`, `text/plain`) is rejected by the HTML DOM extractor.
3. **`<script>` Stripping & ~16 KB Text Cap:** All `<script type="application/ld+json">` tags are stripped during DOM sanitization, and extracted visible text is truncated at ~16 KB per page.
4. **Strict URL-Construction Guardrail:** The browsing tool cannot construct or append query parameters on its own; it can only browse complete URLs (`https://...`) explicitly present in the DOM of a previously fetched page.

Meanwhile, the UX audit of `/share/[token]` (`My music Collection - Shared by skruk - iqoqo.png`) identified three visual defects:
- Raw `<details open>` catalog text above the grid pushes album covers below the fold and degrades human UX.
- `<ShareButton>` (`h-8 px-3`) and `<PublicFeedButton>` (`py-2 px-4`) have mismatched heights.
- The `{} JSON-LD / AI Feed` button is overly wide and visually dominant compared to primary human actions (`Share`, `RSS Feed`).

## Goals / Non-Goals

**Goals:**

- Clean, human-first `/share/[token]` page with SQL pagination (`per_page = 48`) and no raw text dump above the cover grid.
- Uniform button height (`h-9`) across all share header buttons, with the JSON-LD action minimized to a subtle icon-only RDF button linking to the full absolute URL `https://<host>/share/<token>?format=jsonld&page=1`.
- Chromeless Next.js `?format=jsonld&page=N` HTML-wrapped JSON-LD mini-page (`per_page = 60`, keeping every page under the ~65-item single-fetch threshold observed in Gemini App) without `<Navbar />` or `<Footer />`, exposing full absolute pagination URLs so Gemini App can traverse 365, 2,000, or 20,000 items across pages without truncation or `PERMISSION_DENIED`.
- Windowed pagination (at most **10 pages** shown at a time: **first (`1`), up to `8` around current page, and last (`totalPages`)**) on both the human grid and the `?format=jsonld` mini-page.
- Audio pressing triples in RDF and JSON-LD, and correct format badges (Vinyl/CD/SACD, never "Book").

**Non-Goals:**

- Raising the `feed.xml` 50-item cap.
- Changing share-token issuance or revocation.
- Rendering HTML from Flask (`app/` remains strictly API-only).

## Decisions

1. **Shared visibility guard & SQL pagination:** `GET /api/public/share/<token>` enforces `Item.is_hidden == False` and `Item.visibility == "public"` and supports `page` (default `1`) and `per_page` (default `48` when `page` is supplied, max `200` for paginated UI/AI views; legacy unpaginated `?limit=` up to `1000`/`2000` remains supported for backward compatibility and RDF exports). Returns `total`, `page`, `per_page`, `pages`, and `items`.
2. **10-Page Window Algorithm (`buildPaginationWindow(currentPage, totalPages)`):**
   - Never displays more than **10** page numbers at once:
     - If `totalPages <= 10`, returns `[1..totalPages]`.
     - Otherwise, always includes page `1` (first), page `totalPages` (last), and a contiguous window of **8 pages** centered around `currentPage` (clamped to `[2, totalPages - 1]`).
   - Used identically in the human `/share/[token]?page=N` pagination bar and in the `?format=jsonld&page=N` mini-page `<nav>` + JSON-LD `pages` array.
3. **Chromeless Query-Free `/share/[token]/jsonld/[page]` Mini-Page in Next.js (`frontend/app/share/[token]/jsonld/[page]/page.tsx` + `frontend/lib/share-server.tsx`):**
   - Also retained as `?format=jsonld&page=N` on `frontend/app/share/[token]/page.tsx` for backward compatibility.
   - Serves `Content-Type: text/html; charset=utf-8` (keeping Flask 100% API-only while satisfying Gemini App's HTML-only scraper and avoiding `?` query-string blocks on discovered links).
   - Omits `<Navbar />` and `<Footer />` so 100% of Gemini's budget goes to the JSON-LD payload (`60` items/page).
   - Renders `<nav aria-label="JSON-LD Pages">` with full, query-free absolute `<a href="https://<host>/share/<token>/jsonld/<K>">` links for the 10-page window (plus `nextPage`), followed by `<pre id="jsonld-payload">` containing minified Schema.org JSON-LD (`@context` with short aliases `t`/`a`/`f`/`l`/`c`/`y`/`g` + `totalItems`, `page`, `perPage`, `totalPages`, `nextPage`, `pages`, and `itemListElement`).
4. **Hero Button Harmonization, Subtle RDF Icon Button & `sr-only` AI Page Links:**
   - `<ShareButton>` and `<PublicFeedButton>` both use height `h-9` (`36px`) and consistent border/background tokens.
   - `variant="jsonld"` in `<PublicFeedButton>` renders a compact icon-only (`w-9 h-9`) button with the W3C RDF Flyer SVG (`rdf_flyer.svg`), `sr-only` text, `aria-label`, and `title` tooltip, with `href` set to the **full query-free absolute URL** `${publicBaseUrl}/share/${token}/jsonld/1`. When `totalItems > 60`, `/share/[token]` also emits an `sr-only` `<nav aria-label="AI JSON-LD pages">` with the windowed `/share/${token}/jsonld/1..N` URLs so Gemini App extracts all pages on its initial fetch.
5. **Canonical HTTP Content Negotiation (`Accept: application/ld+json` / `application/json+ld`) + Crawler Isolation:**
   - Every `/share/<token>` URL (including `/share/<token>?page=N`) responds to HTTP Content Negotiation: when `Accept` contains `application/ld+json`, `application/json+ld`, `text/turtle`, `application/n-triples`, or `application/rdf+xml`, `frontend/proxy.ts` (and Nginx via `Accept` routing) proxies the request directly to Flask `/api/public/share/<token>` (forwarding `page`/`per_page`/`limit`), returning raw `application/ld+json` (or requested RDF MIME type).
   - Each HTML version of `/share/[token]` (`?page=N`) also continues to embed `<JsonLdScript>` (`<script type="application/ld+json">`) for search engines and Schema.org validators.
   - `frontend/public/robots.txt` keeps `Disallow: /api/` and `Allow: /share/`.
   - Standard RDF/RSS routes `/share/<token>/catalog.jsonld` and `/share/<token>/feed.xml` proxy to Flask via `deploy/nginx.conf`, `deploy/nginx.conf.example`, and runtime `frontend/proxy.ts` (`FLASK_API_URL`).
   - `deploy/cloudflare-semantic-federation-rules.md` and `scripts/verify_cloudflare_rules.sh` codify Cloudflare WAF & AI Crawl Control setup.

## Risks / Trade-offs

- **[Risk] Collections with 20,000 items (134 pages)** -> Mitigation: SQL `LIMIT`/`OFFSET` queries only 1 page (`48` UI items or `150` JSON-LD items) per request, and the 10-page window bounds both DOM links and JSON-LD `pages` array to at most 10 URLs.
- **[Risk] Gemini URL-construction guardrail blocks relative links** -> Mitigation: Both the RDF icon button on `/share/[token]` and the `pages` / `<nav>` links on `/share/[token]?format=jsonld&page=N` emit full absolute `https://` URLs resolved from `BASE_URL` / `NEXT_PUBLIC_FRONTEND_URL`.
- **[Risk] Cloudflare Managed `robots.txt` overrides origin `robots.txt`** -> Mitigation: documented SRE runbook and automated live check in `scripts/verify_cloudflare_rules.sh`.

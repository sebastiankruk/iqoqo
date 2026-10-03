## Context

See `proposal.md` for motivation and background.

Currently, iqoqo's public and semi-public views have minimal and rigid search engine optimization (SEO) structured data. In `frontend/app/manifestation/[id]/page.tsx`, a simple ternary expression checks only `manifestation.content_type === "board_game"` to select either `"Game"` or `"Book"`, omitting specific types for video games, audiobooks, vinyl/music albums, movies, comics, and art. Furthermore, language attributes (`inLanguage`) and item availability (`schema:offers` based on inventory `collection_status`) are not represented. The collection browsing page (`frontend/app/collection/page.tsx`) contains no `CollectionPage` structured metadata, work detail views lack full FRBR hierarchy representations in JSON-LD, and search crawlers have no `/api/public/sitemap.xml` endpoint to systematically index public profiles and shared collections.

## Goals / Non-Goals

**Goals:**
- Create a centralized frontend Schema.org mapping utility (`frontend/lib/schema-org.ts`) with `schemaTypeMap`, `inLanguage` resolution, and `collection_status` to `schema:ItemAvailability` conversion.
- Update `frontend/app/manifestation/[id]/page.tsx` to use `schemaTypeMap`, add `inLanguage`, and serialize item inventory into `schema:offers`.
- Add `schema:CollectionPage` JSON-LD structured data to `frontend/app/collection/page.tsx` including `ItemList` item references.
- Add `schema:CreativeWork` JSON-LD structured data on work views modeling the full FRBR hierarchy (Work expressing through Expressions, embodied in Manifestations, and exemplified by Items).
- Implement `GET /api/public/sitemap.xml` in `app/api/public.py` to output valid XML containing canonical URLs and `<lastmod>` timestamps for public user profiles (`/u/<username>`), shared collections (`/share/<token>`), and catalog items.
- Ensure all generated JSON-LD complies with Schema.org specifications and Google Rich Results validation criteria.

**Non-Goals:**
- Modifying underlying PostgreSQL database schemas or adding database migrations.
- ActivityPub federation endpoints (deferred to v0.9.0).
- Public `/api/sparql` endpoint or SPARQL UI explorer (part of milestone C2).
- Dynamic sitemap index splitting across multiple XML files (single sitemap capped at 50,000 URLs satisfies current scale).

## Decisions

### 1. Centralized Schema.org Utility Module (`frontend/lib/schema-org.ts`)
- **Decision**: Centralize all Schema.org type maps, status resolvers, and JSON-LD builder functions into a single module `frontend/lib/schema-org.ts`.
  - `schemaTypeMap`: Maps `(contentType, expressionKind, format)` combinations to Schema.org types:
    - `book` → `Book` (or `ComicStory` if comic, `Audiobook` if audio format)
    - `board_game` → `Game`
    - `video_game` → `VideoGame`
    - `audio` / `music` → `MusicAlbum` or `AudioObject`
    - `video` / `movie` → `Movie`
    - Default fallback → `CreativeWork`
  - `mapCollectionStatusToAvailability(status: string)`: Maps iqoqo collection status strings to Schema.org URIs:
    - `owned` / `in_library` → `https://schema.org/InStock`
    - `wishlist` / `wanted` → `https://schema.org/PreOrder` or `https://schema.org/OutOfStock`
    - `lent` / `on_loan` → `https://schema.org/LimitedAvailability`
    - `for_sale` → `https://schema.org/InStock`
    - Default → `https://schema.org/InStock`
- **Rationale**: Keeps mappings consistent across manifestation, collection, work pages, and test suites, preventing drift and code duplication.
- **Alternatives considered**: Inlining mapping dictionaries in each page component; rejected due to maintenance complexity.

### 2. Item Offers Serialization in Manifestation JSON-LD
- **Decision**: When manifestation items or collection status are available, serialize them as an array of `Offer` objects under `offers`:
  ```json
  "offers": [
    {
      "@type": "Offer",
      "availability": "https://schema.org/InStock",
      "itemCondition": "https://schema.org/UsedCondition",
      "price": "0",
      "priceCurrency": "USD",
      "seller": {
        "@type": "Organization",
        "name": "iqoqo Library"
      }
    }
  ]
  ```
- **Rationale**: Google Rich Results and product crawlers parse `offers.availability` to show "In Stock" badges in search listings.
- **Alternatives considered**: Using `schema:ItemAvailability` directly on the Manifestation entity; rejected because Schema.org defines availability as a property of `Offer`, not `CreativeWork`.

### 3. Collection Page `schema:CollectionPage` JSON-LD
- **Decision**: In `frontend/app/collection/page.tsx`, inject a JSON-LD payload:
  ```json
  {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Library Collection",
    "description": "Catalog of curated items and works",
    "mainEntity": {
      "@type": "ItemList",
      "numberOfItems": totalCount,
      "itemListElement": [...]
    }
  }
  ```
- **Rationale**: Gives search engines structural knowledge about the library's contents and enables item carousel features in search listings.
- **Alternatives considered**: Relying on raw HTML table/grid parsing; rejected because search engines prefer explicit JSON-LD collection representations.

### 4. Work Page CreativeWork Full FRBR Hierarchy Structured Data
- **Decision**: Represent the Work as the root `schema:CreativeWork`, linking child expressions and manifestations via `workExample`:
  ```json
  {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    "name": work.title,
    "author": { "@type": "Person", "name": authorName },
    "workExample": [
      {
        "@type": manifestationSchemaType,
        "name": manifestation.title,
        "isbn": manifestation.isbn13,
        "inLanguage": manifestation.language
      }
    ]
  }
  ```
- **Rationale**: Preserves FRBR integrity while mapping directly to standard Schema.org relations (`workExample` is explicitly designed for the FRBR Work-to-Manifestation relationship).
- **Alternatives considered**: Flattening all manifestation metadata into the Work; rejected because it violates FRBR multi-edition principles.

### 5. Backend Sitemap Generation (`app/api/public.py`)
- **Decision**: Implement `GET /api/public/sitemap.xml` using SQLAlchemy streaming queries and a helper `generate_sitemap_xml()`.
  - Queries:
    1. Public users (`User.visibility == 'public'`) → `<loc>{base_url}/u/{username}</loc>`
    2. Active shared collections (`SharedCollection.is_active == True`) → `<loc>{base_url}/share/{token}</loc>`
    3. Public manifestations → `<loc>{base_url}/manifestation/{id}</loc>`
  - Responses include `Content-Type: application/xml; charset=utf-8` and `Cache-Control: public, max-age=3600`.
- **Rationale**: Directly satisfies search crawler standards without adding heavy external dependencies.
- **Alternatives considered**: Generating static XML files on disk via cron job; rejected because dynamic endpoint with HTTP caching provides instant updates when public collections are shared.

## Risks / Trade-offs

- **[Risk: Large catalog causing slow sitemap queries or memory spikes]** → **Mitigation**: Constrain public manifestation query with bounded `LIMIT` (up to 50,000 URLs per Sitemaps protocol standard), select only necessary scalar columns (`id`, `updated_at`), and cache response via `Cache-Control`.
- **[Risk: Invalid Schema.org types or properties causing Google Search Console warnings]** → **Mitigation**: Restrict mapping types to canonical Schema.org vocabulary (`Book`, `Game`, `VideoGame`, `Movie`, `MusicAlbum`, `Audiobook`, `ComicStory`, `CreativeWork`), validated with Jest unit tests.
- **[Risk: Leaking private user collections or unshared items into sitemap]** → **Mitigation**: Enforce strict SQL filters (`User.visibility == 'public'` and `SharedCollection.is_active == True`).

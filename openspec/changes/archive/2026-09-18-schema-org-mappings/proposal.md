## Why

Public-facing catalog and library pages in iqoqo currently lack comprehensive Schema.org structured data and discoverability endpoints. Manifestation pages rely on rudimentary two-branch ("Game" vs "Book") JSON-LD, collection pages emit no collection-level semantic schemas, work hierarchies lack rich JSON-LD representations, and search engine crawlers lack an automated `/api/public/sitemap.xml` endpoint to discover public profiles and shared collections. As part of milestone 'C4: Schema.org SEO Mappings' in v0.8.0 (Semantic Web & Linked Open Data), this change aligns FRBR entity representations with Schema.org CreativeWork and Product schemas to enable rich search snippets, crawler discoverability, and AI agent semantic extraction.

## What Changes

- **Manifestation Page Structured Data (`frontend/app/manifestation/[id]/page.tsx`)**:
  - Replace naive ternary `schemaType` with an extensible `schemaTypeMap` mapping content types and formats (Book, Audiobook, ComicStory, Game, VideoGame, Movie, MusicAlbum, etc.).
  - Add `inLanguage` property derived from manifestation metadata.
  - Inject `schema:offers` linking inventory items with `schema:ItemAvailability` states mapped from item `collection_status`.
- **Collection Page Structured Data (`frontend/app/collection/page.tsx`)**:
  - Add `schema:CollectionPage` JSON-LD schema describing the collection catalog, active items, and search actions.
- **Work Page Structured Data**:
  - Add `schema:CreativeWork` JSON-LD modeling the full FRBR hierarchy (Work expressing through Expressions, embodied in Manifestations, and exemplified by Items).
- **Public Sitemap Endpoint (`GET /api/public/sitemap.xml`)**:
  - Create a public XML sitemap route in `app/api/public.py` generating canonical URLs for public user profiles (`/u/<username>`), public shared collections (`/share/<token>`), and discoverable public catalog manifestations with appropriate `<lastmod>` timestamps.
- **Item Availability Mapping**:
  - Create standard mapping from iqoqo `collection_status` (e.g. `owned`, `wishlist`, `reading`, `lent`, `for_sale`) to Schema.org `offers` and `ItemAvailability` (`https://schema.org/InStock`, `https://schema.org/PreOrder`, etc.).

## Capabilities

### New Capabilities
- `semantic/schema-org-seo`: Schema.org JSON-LD structured data mappings across FRBR entity tiers (Work, Manifestation, Collection) and public sitemap generation for search engine discoverability and Google Rich Results.

### Modified Capabilities

## Impact

- **Frontend**:
  - `frontend/app/manifestation/[id]/page.tsx`: Enhanced JSON-LD with `schemaTypeMap`, `inLanguage`, and `offers`.
  - `frontend/app/collection/page.tsx`: Injected `schema:CollectionPage` JSON-LD.
  - Work views / structured data components: Added `schema:CreativeWork` graph serialization.
  - Utilities: Helper module for Schema.org mappings and `ItemAvailability` conversion.
- **Backend**:
  - `app/api/public.py`: New route `GET /api/public/sitemap.xml`.
  - Rate limiting and caching considerations for sitemap generation.
- **Dependencies & APIs**:
  - No new external package dependencies required. Standard XML and JSON serialization in Flask and Next.js.
- **Breaking Changes**: None. Purely additive metadata and new public API endpoint.

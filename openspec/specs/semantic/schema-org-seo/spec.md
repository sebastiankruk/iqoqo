# semantic/schema-org-seo Specification

## Purpose

Exposes Schema.org JSON-LD structured data and XML sitemaps for FRBR entities, enabling search engine rich results, Google product/creative work snippets, and crawler discoverability.

## Requirements

### Requirement: Manifestation Page Schema.org Structured Data

The system MUST render Schema.org JSON-LD structured data on manifestation detail pages using precise types resolved from catalog metadata, and including language, creators, identifiers, publisher, and publication year.

#### Scenario: Rendering book manifestation structured data

- **WHEN** a user or crawler accesses a manifestation page for a book with ISBN, author, and publisher
- **THEN** the page contains a JSON-LD script tag with `@type: "Book"`, `name`, `author` (as a `Person`), `isbn`, `identifier`, `publisher`, and `datePublished`.

#### Scenario: Rendering non-book media with schemaTypeMap

- **WHEN** a manifestation page is requested for a board game, video game, comic, audiobook, movie, or music album
- **THEN** the JSON-LD `@type` resolves to the corresponding Schema.org type (`Game`, `VideoGame`, `ComicStory`, `Audiobook`, `Movie`, `MusicAlbum`) rather than fallback defaults.

#### Scenario: Manifestation language metadata inclusion

- **WHEN** a manifestation has an associated language code (e.g., `"eng"`, `"pol"`, or `"en"`)
- **THEN** the JSON-LD payload includes the `inLanguage` property containing the resolved language tag.

### Requirement: Item Availability Mapping via Schema Offers

The system MUST serialize physical and digital collection copies as Schema.org `Offer` entries within manifestation structured data, mapping each copy's `collection_status` to a canonical Schema.org `ItemAvailability` URI.

#### Scenario: Owned item marked in stock

- **WHEN** a manifestation possesses collection items with status `owned`
- **THEN** the structured data contains an `offers` array containing an `Offer` with `availability: "https://schema.org/InStock"`.

#### Scenario: Wishlist item marked pre-order or out of stock

- **WHEN** a manifestation possesses collection items with status `wishlist` or `wanted`
- **THEN** the structured data contains an `Offer` with `availability: "https://schema.org/PreOrder"` or `https://schema.org/OutOfStock`.

#### Scenario: Lent or reserved item marked on loan

- **WHEN** a manifestation possesses collection items with status `lent` or `reserved`
- **THEN** the structured data marks the offer availability appropriately as `https://schema.org/LimitedAvailability` or `https://schema.org/Discontinued`.

### Requirement: Collection Page Structured Data

The system MUST embed Schema.org `CollectionPage` JSON-LD structured data on collection browsing pages, representing the library collection, its curator or owner, and discovery metadata.

#### Scenario: Viewing public or authenticated collection page

- **WHEN** a client views a collection browser page
- **THEN** the page injects JSON-LD with `@type: "CollectionPage"`, containing collection `name`, `description`, curator/author info, and `hasPart` or `mainEntity` linking to catalog items.

### Requirement: Work Page CreativeWork Hierarchy Structured Data

The system MUST render Schema.org `CreativeWork` structured data on work views, representing the overarching FRBR Work and nesting its associated Expressions, Manifestations, and availability.

#### Scenario: Viewing work hierarchy

- **WHEN** a client views a work page or component displaying a Work with linked expressions and manifestations
- **THEN** the page injects a Schema.org `CreativeWork` JSON-LD graph representing the work entity and referencing its embodied manifestations via `workExample` or `hasPart`.

### Requirement: Public XML Sitemap Generation

The system SHALL provide a public HTTP endpoint at `GET /api/public/sitemap.xml` that returns a valid XML sitemap conforming to the Sitemaps XML protocol (sitemaps.org).

#### Scenario: Crawling public sitemap

- **WHEN** an unauthenticated crawler issues a `GET` request to `/api/public/sitemap.xml`
- **THEN** the server responds with HTTP status 200, Content-Type `application/xml` (or `text/xml`), and a `<urlset>` document containing canonical `<url>` entries with `<loc>` and `<lastmod>` for all public user profiles (`/u/<username>`), public shared collections (`/share/<token>`), and public catalog manifestations.

#### Scenario: Exclusion of private profiles and unshared collections

- **WHEN** user accounts have visibility set to `private` or shared collections are disabled/expired
- **THEN** the generated sitemap excludes those private URLs.

#### Scenario: Efficient caching and rate limiting

- **WHEN** repeated requests are made to `/api/public/sitemap.xml`
- **THEN** the endpoint respects public rate limiting and provides HTTP caching headers (`Cache-Control`) to minimize server load.

### Requirement: Expression-Kind-Aware Schema.org Mapping

Schema.org mapping MUST account for FRBR Expression kind as well as content type and physical format, including mapping live-performance/concert expressions to event semantics where applicable.

#### Scenario: Live performance expression

- **WHEN** a manifestation belongs to an Expression with `live_performance` kind
- **THEN** backend RDF and frontend SSR structured data use the documented MusicEvent mapping and preserve performer/date/location fields when available

#### Scenario: Ordinary expression precedence

- **WHEN** an ordinary expression has a content type and physical format
- **THEN** the documented content-type/format mapping remains unchanged

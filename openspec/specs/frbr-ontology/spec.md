# OpenSpec Specification: FRBR Ontology Boundaries

## Purpose

This specification defines the boundary rules for the four-tier Functional Requirements for Bibliographic Records (FRBR) ontology implemented in iqoqo.
## Requirements
### Requirement: Four-Tier FRBR Hierarchy

All media cataloged in iqoqo MUST align with the four-tier FRBR standard hierarchy (Work -> Expression -> Manifestation -> Item).

#### Scenario: Validating FRBR Hierarchy Structure

- **WHEN** domain entities are processed or stored
- **THEN** entity relationships strictly follow Work -> Expression -> Manifestation -> Item.

All media cataloged in iqoqo must align with the FRBR standard:

1. **Work:** The conceptual creation (e.g., _The Lord of the Rings_ by J.R.R. Tolkien). Holds titles, authors, and abstract subjects. Contains no language, format, or physical attributes.
2. **Expression:** The realization of a Work (e.g., Maria Skibniewska's Polish translation, or the original English text). Holds language, translator, or performance details. Contains no physical attributes or ISBN.
3. **Manifestation:** The physical or digital release/edition (e.g., the 2002 Muza Hardcover Edition, ISBN 978-83-7495-312-2). Holds formats, publishers, release dates, EAN/ISBN codes, and cover art.
4. **Item:** The single physical or digital copy owned by a user (e.g., the copy on Shelf 3B, barcode `123456789`). Holds condition, location, acquisition dates, pricing, lending status, and custom notes.

```mermaid
graph TD
    Work["Work (Abstract Concept)"] --> Expression["Expression (Language / Version)"]
    Expression --> Manifestation["Manifestation (Release / Format / ISBN)"]
    Manifestation --> Item["Item (Physical Copy on Shelf / Barcode)"]
```

### Requirement: Type Mutability

The system SHALL allow the core `type` attribute of an existing FRBR entity (Work, Expression, Manifestation, or Item) to be modified, provided the change maintains ontological boundaries.

#### Scenario: Backend Type Update

- **WHEN** a valid API request is made to change the `type` of a Manifestation
- **THEN** the system updates the `type` field while leaving any existing type-specific metadata (e.g., `meta` JSON) intact for potential future data migration

### Requirement: Upward Type Propagation

When a Manifestation's `type` is modified, the system SHALL adapt the parent Work and Expression upwards to ensure the new type is correctly covered without limiting to other types in the future.

#### Scenario: Upward Type Adaptation

- **WHEN** a Manifestation's `type` is changed
- **THEN** the system ensures the parent Expression and Work types are adapted upwards to remain ontologically consistent with the new Manifestation type

### Requirement: Expression kind is mutable via admin API

The `expression.kind` attribute SHALL be exposed as a mutable field through the standard `PUT /api/admin/frbr/expression/{id}` endpoint. The endpoint SHALL accept `kind` in the request body and forward it to the service layer for validation and persistence. `expression.kind` SHALL NOT be a write-once ingestion artifact — it SHALL be correctable by admins through the same update path used for `content_type`, `language`, and `meta`.

#### Scenario: Kind forwarded alongside other expression fields

- **WHEN** an admin updates an Expression via `PUT /api/admin/frbr/expression/{id}` with `{"language": "en", "kind": "live_performance"}`
- **THEN** both the `language` and `kind` fields SHALL be updated on the Expression record

#### Scenario: Kind preserved when omitted

- **WHEN** an admin updates an Expression via `PUT /api/admin/frbr/expression/{id}` with `{"language": "pl"}` (no `kind` key in body)
- **THEN** the Expression's existing `kind` value SHALL remain unchanged

### Requirement: Event entities respect FRBR level boundaries

The FRBRoo event-contribution entities SHALL attach strictly to their corresponding FRBR level: Composition Events (`WorkContribution`) at the Work, Performance Events (`ExpressionContribution`) at the Expression, and Publication Events (`ManifestationContribution`) at the Manifestation. Physical attributes and item-level data SHALL NEVER be attached to any event entity.

#### Scenario: Event contribution never carries physical attributes

- **WHEN** a contribution row of any event type is created
- **THEN** it SHALL reference only its level-appropriate entity (Work, Expression, or Manifestation) plus a `Contributor`, and SHALL NOT store barcodes, conditions, shelf locations, or acquisition data

### Requirement: Container Work aggregation boundary

Board game containers SHALL be modeled exclusively through the FRBRoo F16 Container Work pattern using `ContainerAggregation`. Format values, genre tags, or item notes SHALL NOT be used as a substitute for container structure.

#### Scenario: Container structure is never simulated by tags

- **WHEN** a board game's contents (rulebook, board, pieces) are recorded
- **THEN** they SHALL be represented as `ContainerAggregation` rows and SHALL NOT be encoded as tags or as part of the manifestation format value

### Requirement: Concert hierarchy boundary

A concert release SHALL follow the hierarchy musical/audiovisual Work → live-performance Expression (Performance Event) → audio or video Manifestation → Item. A concert SHALL NOT be modeled as a distinct top-level media category, nor as a Work-level genre.

#### Scenario: Concert graph passes ontology validation

- **WHEN** a concert release is validated against the FRBR boundary rules
- **THEN** its Expression SHALL carry the performance marker and performance contributors, and its Manifestation SHALL carry the carrier format, with no concert indicator stored on the Work or the Item

## 2. Ontological Boundary Rules

### A. Attributes Assignment

- **No Physical Attributes on Work/Expression:** Barcodes, conditions, acquisition dates, shelf locations, or lending logs must NEVER be attached to a Work or Expression.
- **No Format Attributes on Work:** Format details (CD, Vinyl, Hardcover, DVD), publishers, or ISBNs must NEVER be attached directly to a Work.
- **No Virtual Identity Mixup:** Virtual items on the wishlist (where the Item entity is not present, or has `id < 0`) are purely conceptual or representative. They represent the intent to own, but they do NOT have physical shelf placement, barcode scanner associations, or active lending availability.

### B. Metadata Verification & Fallbacks

- External catalog lookup services (e.g., ISBN, Allegro, BGG, Discogs, TMDB) must fail gracefully.
- If no external metadata is found, the system must present the manual entry fallback view.
- Under no circumstances should the system generate dummy cover art, placeholder barcodes, or mock ISBNs.

## 3. Database & API Validation Guards

- The backend decorator `@require_physical_item` must screen incoming payloads to ensure mutating endpoints (such as lending or editing physical item properties) are only called for actual physical items (where `id > 0` and entity is an Item).

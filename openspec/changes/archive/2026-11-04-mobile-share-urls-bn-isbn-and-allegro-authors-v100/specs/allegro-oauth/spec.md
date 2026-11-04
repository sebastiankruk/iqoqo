## ADDED Requirements

### Requirement: Bibliographic and Media Parameter Extraction from Allegro Catalog
The Allegro ingestion service SHALL parse structured catalog parameters from products and offers into canonical FRBR attributes, extracting creators, clean titles, publishers, and release years.

#### Scenario: Ingesting books and media with rich parameter structures
- **WHEN** an item is ingested or scanned via the Allegro Catalog API
- **THEN** the system SHALL parse parameter keys for `Autor`, `Autorzy`, `Wykonawca`, `Twórca`, `Reżyser`, clean `Tytuł`, `Wydawnictwo`, and `Rok wydania`
- **AND** the extracted values SHALL populate FRBR `work.meta["authors"]`, manifestation authors, publisher, and year
- **AND** display projections SHALL NOT fall back to "Undefined" or "Unknown Title".

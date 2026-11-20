# serials-journals-frbr-ontology Specification

## Purpose
Define the FRBRoo four-tier data model, database columns, taxonomy mappings, metadata projections, and RDF/JSON-LD triples for serial publications (`F18_Serial_Work` identified by ISSN) and their individual issues (`Manifestation` identified by issue/volume/date and `977` EAN + EAN-2 add-on).

## Requirements

### Requirement: FRBR Separation of Serial Work (`F18_Serial_Work`) and Issue Manifestation
The system SHALL model a periodical title as a single `Work` (`work_kind="serial"`, `issn`, `eissn`), its language/editorial edition as an `Expression`, each published issue as a distinct `Manifestation` (`issue_number`, `cumulative_issue_number`, `volume`, `publication_year`, `publication_month`, `ean`, `ean_addon`, `full_barcode`), and physical copies as `Item` rows.

#### Scenario: Two issues of *National Geographic Polska* sharing one ISSN and year EAN-13 map to one Work and two Manifestations

- **GIVEN** the serial `Work` *National Geographic Polska* with `issn="1507-5966"` and `work_kind="serial"`
- **WHEN** `Nr 7(58) Lipiec 2004` (`ean="9771507596044"`, `ean_addon="07"`, `issue_number="7"`, `cumulative_issue_number=58`, `publication_year=2004`, `publication_month=7`) and `Nr 12(63) Grudzień 2004` (`ean="9771507596044"`, `ean_addon="12"`, `issue_number="12"`, `cumulative_issue_number=63`, `publication_year=2004`, `publication_month=12`) are stored
- **THEN** both issues MUST reference the exact same `Work` (`F18_Serial_Work`) and MUST persist as two distinct `Manifestation` records with distinct `full_barcode` values (`977150759604407` and `977150759604412`).

### Requirement: Linear Alembic Migration Within 32-Character Revision Limit
Schema extensions for serial `Work` (`issn`, `eissn`, `work_kind`) and issue `Manifestation` columns SHALL be delivered in a single linear Alembic migration whose `revision` identifier has length `<= 32` characters and maintains `len(heads) == 1`.

#### Scenario: Alembic migration head remains strictly linear and PostgreSQL-safe

- **GIVEN** the migration history ending at `v1_0_0_add_apple_id_to_users`
- **WHEN** `v1_1_0_serial_issn_issues` is applied via `flask db upgrade` on PostgreSQL or SQLite
- **THEN** `len(ScriptDirectory.get_heads()) == 1`, `len(revision) <= 32`, and both `catalog.works` and `catalog.manifestations` expose the new nullable indexed columns without locking or breaking existing rows.

### Requirement: Serial RDF/JSON-LD Serialization (`schema:Periodical` and `schema:PublicationIssue`)
RDF and JSON-LD endpoints (`/api/public/works/<id>`, `/api/public/manifestations/<id>`, `/api/public/rdf/*`, `/api/public/share/<token>`) SHALL emit `frbroo:F18_Serial_Work`, `schema:Periodical`, `schema:issn`, `schema:PublicationIssue`, `schema:issueNumber`, and `schema:volumeNumber` triples for serial works and issue manifestations, omitting absent optional fields.

#### Scenario: Exporting a serial Work and issue Manifestation as JSON-LD / Turtle

- **GIVEN** a serial `Work` (*National Geographic Polska*, `issn="1507-5966"`) and an issue `Manifestation` (`issue_number="7"`, `publication_year=2004`, `ean="9771507596044"`)
- **WHEN** serialized via RDF/JSON-LD
- **THEN** the Work URI MUST carry `schema:Periodical` and `schema:issn "1507-5966"`, and the Manifestation URI MUST carry `schema:PublicationIssue`, `schema:issueNumber "7"`, and `schema:gtin13 "9771507596044"`.

## Why

Journals and magazines (such as *National Geographic Polska*, *Nature*, or *Analog*) cannot be cleanly cataloged in iqoqo because the FRBR catalog lacks a formal serial `Work` (`F18_Serial_Work` with `ISSN` / `eISSN`) vs. issue `Manifestation` (`F3_Manifestation_Product_Type` with issue/cumulative numbers, publication month/year, cover headline, and `977` EAN + 2-digit EAN-2 add-on) data model and RDF/JSON-LD vocabulary. Physical *National Geographic Polska* samples further demonstrate that monthly issues in the same year share an identical 13-digit `977` EAN-13 barcode (e.g., `9771507596044` for both July and December 2004) and can only be uniquely distinguished at the `Manifestation` tier when issue/date/EAN-2 add-on fields are modeled explicitly.

## What Changes

- **FRBRoo Serial & Issue Ontology Extensions (`docs/ontology/iqoqo.ttl`, `docs/ontology/taxonomy.ttl`, `shared/taxonomy.yaml`, `shared/format_mappings.yaml`)**:
  - Model periodicals as `frbroo:F18_Serial_Work` (carrying canonical `issn`, `eissn`, `indeks`, `frequency`, and `schema:Periodical` RDF typing) linked via `Expression` (`language`, `content_type="periodical"` / `"magazine"` / `"journal"`) to issue-level `Manifestation` (`frbroo:F3_Manifestation_Product_Type` carrying `issue_number`, `cumulative_issue_number`, `volume`, `publication_year`, `publication_month`, `cover_date_label`, `cover_headline`, `ean`, `ean_addon`, `full_barcode`, and `schema:PublicationIssue` RDF typing).
  - Regenerate taxonomy artifacts via `make generate-taxonomy` (`journal` / `periodical` / `magazine` normalizations in `shared/format_mappings.yaml`).
- **Database Schema & Linear Alembic Migration (`app/db/core.py`, `migrations/versions/v1_1_0_serial_issn_issues.py`)**:
  - Add indexed `issn` (String 9, e.g., `1507-5966`), `eissn` (String 9), and `work_kind` (`"serial"` / `None`) columns on `Work`, plus issue identification fields on `Manifestation` (`issue_number`, `cumulative_issue_number`, `volume`, `publication_year`, `publication_month`, `ean_addon`, `full_barcode` indexed for fast lookup) with revision ID `<= 32` characters and strictly single-head DAG.
  - Keep `Manifestation.ean` non-unique (`9771507596044` shared across issues in the same year) while enforcing uniqueness / lookup clarity via `full_barcode` / issue metadata.
- **Metadata Projection, Schemas, RDF & OpenAPI 3.1 (`app/core/metadata_projection.py`, `app/api/public_rdf.py`, `app/api/schemas.py`, `app/api/docs.py`)**:
  - Emit `schema:Periodical`, `schema:PublicationIssue`, `schema:issn`, `schema:issueNumber`, `schema:volumeNumber`, and `schema:datePublished` in `/api/lod/*` and `/api/public/rdf/*`.
  - Project structured serial & issue metadata cleanly in `display` projections and `/api/works/<id>`, `/api/manifestations/<id>`, and `/api/items/<id>` payloads, and update `app/api/docs.py` OpenAPI 3.1 schemas.

## Capabilities

### New Capabilities
- `serials-journals-frbr-ontology`: FRBRoo `F18_Serial_Work` (ISSN/eISSN) and issue `Manifestation` data model, linear database migration, taxonomy normalization, metadata projection, and `schema:Periodical` / `schema:PublicationIssue` RDF serialization.

### Modified Capabilities

## Impact

- **Ontology & Taxonomy**: `docs/ontology/iqoqo.ttl`, `docs/ontology/taxonomy.ttl`, `shared/taxonomy.yaml`, `shared/format_mappings.yaml`, `app/core/taxonomy.py`, `frontend/types/taxonomy.ts`.
- **Database & Migrations**: `app/db/core.py`, `migrations/versions/v1_1_0_serial_issn_issues.py`.
- **Backend (`app/`)**: `app/core/metadata_projection.py`, `app/api/public_rdf.py`, `app/api/works.py`, `app/api/manifestations.py`, `app/api/items.py`, `app/api/schemas.py`, `app/api/docs.py`.
- **Tests (`tests/`)**: `tests/test_serial_ontology.py`, `tests/test_rdf_serialization.py`, `tests/test_openapi_spec.py`.

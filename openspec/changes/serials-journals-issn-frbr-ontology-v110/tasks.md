## 1. Ontology, Taxonomy & Format Mappings

- [ ] 1.1 Update `docs/ontology/iqoqo.ttl` and `docs/ontology/taxonomy.ttl` with `frbroo:F18_Serial_Work`, `iqoqo:issn`, `iqoqo:eissn`, `iqoqo:issueNumber`, `iqoqo:cumulativeIssueNumber`, `iqoqo:volume`, `iqoqo:eanAddon`, and `schema:Periodical` / `schema:PublicationIssue` mappings
- [ ] 1.2 Add `journal` / `periodical` / `serial` normalizations to `shared/format_mappings.yaml`, add `magazine` / `serial` format metadata in `shared/taxonomy.yaml`, run `make generate-taxonomy`, and verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_taxonomy*.py tests/test_format_normalizer*.py`

## 2. Database Schema & Linear Alembic Migration

- [ ] 2.1 Add `issn`, `eissn`, and `work_kind` columns (with indexes) to `Work` and `issue_number`, `cumulative_issue_number`, `volume`, `publication_year`, `publication_month`, `ean_addon`, and `full_barcode` columns (with indexes) to `Manifestation` in `app/db/core.py`
- [ ] 2.2 Create linear Alembic migration `migrations/versions/v1_1_0_serial_issn_issues.py` (`down_revision = "v1_0_0_add_apple_id_to_users"`, `len(revision) <= 32`) and verify `len(ScriptDirectory.get_heads()) == 1` plus clean upgrade/downgrade in SQLite/PostgreSQL

## 3. Metadata Projection, RDF/JSON-LD & OpenAPI 3.1

- [ ] 3.1 Update `app/core/metadata_projection.py`, `app/api/works.py`, `app/api/manifestations.py`, `app/api/items.py`, `app/api/schemas.py`, and `app/api/docs.py` to project, validate, and document serial/issue fields (`issn`, `eissn`, `work_kind`, `issue_number`, `cumulative_issue_number`, `volume`, `publication_year`, `publication_month`, `ean_addon`, `full_barcode`, `cover_headline`)
- [ ] 3.2 Update `app/api/public_rdf.py` to emit `schema:Periodical`, `schema:PublicationIssue`, `schema:issn`, `schema:issueNumber`, and `schema:volumeNumber` triples for serial works and issues, and verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_serial_ontology.py tests/test_rdf_serialization.py tests/test_openapi_spec.py`

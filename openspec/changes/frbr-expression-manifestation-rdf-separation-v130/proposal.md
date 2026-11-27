## Why

During `/ontologist-expert` audit, several FRBR (`F2` Expression vs `F3` Manifestation vs `F5` Item) RDF serialization & ingestion issues were identified as breaking changes for existing RDF/SPARQL consumers and therefore deferred cleanly from `v1.2.0` to `v1.3.0`:

1. **`F2` Expression Predicates Emitted on `m_uri` (`Manifestation`):** `app/core/frbr_service.py` currently emits `schema:inLanguage` (`L2835`, `3573`), `sioc:topic` (from `Expression.meta["tags"]`, `L3376`, `3532`, `3683`), and live-concert `schema:MusicEvent` / `startDate` / `location` / `performer` (`L2837-2856`, `3772-3790`) on `m_uri` (`Manifestation`) instead of `e_uri` (`Expression`).
2. **Synthetic Tier IRI Aliasing & Partial Anchor Enrichment:** When `expression_id` or `work_id` is missing on legacy dict payloads, `frbr_service.py:3381-3384, 3537-3540` aliases `expression_id = item_id` and `work_id = expression_id`, conflating distinct entities' IRIs. Passing `Work` or `Expression` directly to `_enrich_graph_from_db` (`L2693-2700`) skips child `manifestation` / `expression` enrichment (`ImageScan`, Audio, Manifestation LOD).
3. **`ReadingSession` & `ItemStatusLog` Lack Structured Modeling & Cleanup of Legacy Metadata:** `ReadingSession` lives as schemaless JSON (`Item.meta["reading_sessions"]`) without OWL/RDF representation, `ItemStatusLog` is absent from `iqoqo.ttl`, and ingestion (`ingest.py`) still duplicates `publisher` onto `Work.meta` and `Authors`/`mechanics`/`work_kind`/`issn` onto `Manifestation.meta`.

## What Changes

- **Strict `F2` Expression vs `F3` Manifestation RDF Separation:** Move `schema:inLanguage`, `sioc:topic`, and live-concert `schema:MusicEvent` triples from `m_uri` to `e_uri` in `app/core/frbr_service.py` (with release-note migration notice for downstream SPARQL queries).
- **Eliminate Synthetic IRI Aliasing & Expand Child Enrichment:** Require resolved FRBR IDs (no `expression_id = item_id` fallback) and recursively populate `seen_expressions` / `seen_manifestations` when `Work` or `Expression` objects are serialized via `_enrich_graph_from_db`.
- **Clean Up Ingestion Tier Leakage & Model Activity Logs:** Stop duplicating `publisher` on `Work.meta` and `Authors`/`mechanics`/`work_kind`/`issn` on `Manifestation.meta` (`ingest.py`, `frbr_service.py`), document/model `ReadingSession` & `ItemStatusLog` cleanly in `iqoqo.ttl`, and provide an idempotent metadata cleanup command.

## Impact

- Affected files: `app/core/frbr_service.py`, `app/core/ingest.py`, `app/core/export_service.py`, `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, `docs/SEMANTIC_WEB.md`, `tests/test_rdf_serialization.py`, `tests/test_sparql_service.py`.
- Breaking change for external SPARQL/RDF consumers querying `schema:inLanguage` / `sioc:topic` / `schema:MusicEvent` directly on `Manifestation` IRIs — hence scoped for `v1.3.0`.

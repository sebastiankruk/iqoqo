## 1. Multi-Provider Fallback & Gap-Fill Engine

- [ ] 1.1 Update `fetch_isbn_metadata` in `app/utils/isbn.py` to trigger secondary provider lookup when primary outcome lacks `cover_url` or key metadata; verify with unit test
- [ ] 1.2 Implement `_merge_metadata_gaps(primary, secondary)` helper preserving primary fields and tracking field provenance in `meta["_provenance"]`; verify non-destructive merge behavior
- [ ] 1.3 Add timeout guard ensuring total lookup duration across providers aborts at 3.0s ceiling; verify timeout behavior with mocked delayed provider

## 2. Ingest Pipeline & RDF Provenance

- [ ] 2.1 Update `app/core/ingest.py` to map multi-source field provenance into manifestation metadata and raw payloads; verify during test ingestion
- [ ] 2.2 Update `app/core/frbr_service.py` RDF serialization to output multiple `prov:wasDerivedFrom` triples for multi-provider entities; verify with RDF serialization tests
- [ ] 2.3 Add end-to-end pytest suite in `tests/test_multi_provider_gap_fill.py` with mock responses (Google Books text + Open Library cover) verifying completed manifestation creation

## 1. SSRF-Safe OpenCollections Strategy & LOD Export (`app/`)

- [x] 1.1 Implement `app/utils/opencollections.py` and `app/strategies/opencollections.py` (`OpenCollectionsLookupStrategy`) using `app/core/http_client.py` with `5.0s` timeout floor, SSRF validation, `record_outbound_api_call("opencollections", ...)`, and FRBR `Work` $\to$ `Expression` $\to$ `Manifestation` normalization with `meta["lod_links"]["opencollections_uri"]`.
- [x] 1.2 Update `app/api/lod.py` and `frontend/components/admin/frbr/provider-merge-dialog.tsx` so `opencollections_uri` is emitted in JSON-LD/RDF `owl:sameAs` triples and selectable during custodian metadata enrichment.

## 2. Verification & Test Suite

- [x] 2.1 Author unit and API tests in `tests/test_opencollections_strategy.py` and `tests/test_lod_opencollections.py` verifying SSRF guards, FRBR normalization, graceful failure on timeout, and JSON-LD `sameAs` output, and run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`.

## 1. Actor URI Immutability & WebFinger Alignment

- [ ] Refactor `app/core/iri.py` to generate canonical Actor IRIs based on immutable user UUIDs.
- [ ] Update WebFinger lookup in `app/api/federation.py` to resolve username queries to canonical UUID Actor IRIs.
- [ ] Add unit tests in `tests/test_iri_immutability.py` verifying URI stability across username updates.

## 2. FRBR Merge Tombstones & RDF SameAs Emission

- [ ] Update `app/core/frbr_merge.py` to record `owl:sameAs` links and ActivityStreams `Move` payloads on entity consolidation.
- [ ] Expose tombstone handling in public RDF endpoints (`app/api/public_rdf.py`).
- [ ] Verify tombstone responses and redirection with pytest test suite.


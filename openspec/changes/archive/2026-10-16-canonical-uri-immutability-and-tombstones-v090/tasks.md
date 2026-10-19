## 1. Actor URI Immutability & WebFinger Alignment

- [x] Refactor `app/core/iri.py` to generate canonical Actor IRIs based on immutable user UUIDs.
- [x] Update WebFinger lookup in `app/api/federation.py` to resolve username queries to canonical UUID Actor IRIs.
- [x] Add unit tests in `tests/test_iri_immutability.py` verifying URI stability across username updates.

## 2. FRBR Merge Tombstones & RDF SameAs Emission

- [x] Update `app/core/frbr_merge.py` to record `owl:sameAs` links and ActivityStreams `Move` payloads on entity consolidation.
- [x] Expose tombstone handling in public RDF endpoints (`app/api/public_rdf.py`).
- [x] Verify tombstone responses and redirection with pytest test suite.


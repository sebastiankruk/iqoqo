## Context

See `proposal.md` for motivation. In `v0.8.0`–`v0.8.2`, `iqoqo` established RDF/JSON-LD serialization (`app/api/lod.py`) and external LOD linking (DBpedia, WordNet, GeoNames). Adding `opencollections.org` extends this semantic interoperability to open federated collections.

## Goals / Non-Goals

**Goals:**
- Route all outbound requests to `opencollections.org` strictly through `app/core/http_client.py` with DNS/IP SSRF validation, a `5.0s` timeout floor, and `record_outbound_api_call("opencollections", ...)` telemetry.
- Map `opencollections.org` metadata cleanly to FRBR `Work` $\to$ `Expression` $\to$ `Manifestation` with `_provenance` attribution and `owl:sameAs` JSON-LD export.
- Fail gracefully (never hallucinate metadata or covers) if `opencollections.org` is unreachable.

**Non-Goals:**
- Unbounded background harvesting of external catalogs without explicit custodian/lookup trigger.

## Decisions

### 1. Strategy Pattern & LOD Link Alignment
* **Decision:** Implement `app/utils/opencollections.py` and `app/strategies/opencollections.py` following the same contract as `BnLookupStrategy` (`app/strategies/bn.py`), and store resolved URIs in `meta["lod_links"]["opencollections_uri"]`.
* **Rationale:** Reuses existing LOD badge rendering, `ProviderMergeDialog` field reconciliation, and `app/api/lod.py` `owl:sameAs` projection with minimal surface area.

## Risks / Trade-offs

- **[Risk] External API latency or schema variance** $\to$ **Mitigation:** Enforce strict Pydantic response parsing, `5.0s` timeout via `http_client`, and graceful fallback returning `None` on malformed upstream payloads.

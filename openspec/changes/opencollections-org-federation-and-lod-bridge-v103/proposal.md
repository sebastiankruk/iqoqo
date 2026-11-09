## Why

Supporting `opencollections.org` allows `iqoqo` instances (especially the `iqoqo.cc` Federation Hub and semantic web collectors) to harvest, cross-link, and expose curated open cultural/media collections using standardized Linked Open Data (JSON-LD / RDF) and SSRF-safe external lookup strategies.

## What Changes

- **SSRF-Safe OpenCollections Client & Ingestion Strategy (`app/utils/opencollections.py`, `app/strategies/opencollections.py`):** Implement an outbound client using `app/core/http_client.py` (enforcing DNS/IP SSRF validation, timeouts, and outbound telemetry) that resolves `opencollections.org` collection/record identifiers and maps them into the four-tier FRBR hierarchy (`Work` $\to$ `Expression` $\to$ `Manifestation` with `_provenance` attribution).
- **JSON-LD / RDF `opencollections.org` Export & Cross-Link Alignment (`app/api/lod.py`):** Expose compatible collection and manifestation JSON-LD context mappings on public shared collections (`/api/lod/collections/<token>`) and store `opencollections_uri` external links alongside DBpedia/WordNet/GeoNames URIs on `Work.meta["lod_links"]` and `Manifestation.meta["lod_links"]`.
- **Admin & Custodian Lookup Integration:** Allow custodians in the FRBR Editor and Provider Merge UI to query `opencollections.org` as an external metadata enrichment source.

## Capabilities

### New Capabilities
- `opencollections-lod-and-federation-bridge`: SSRF-safe metadata harvesting, FRBR normalization, and JSON-LD/RDF interoperability with `opencollections.org`.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- **Backend:** `app/utils/opencollections.py`, `app/strategies/opencollections.py`, `app/api/lod.py`, `app/core/ingest_service.py`
- **Frontend:** `frontend/components/admin/frbr/provider-merge-dialog.tsx`, `frontend/components/item/lod-links-badge.tsx`
- **Tests:** `tests/test_opencollections_strategy.py`, `tests/test_lod_opencollections.py`

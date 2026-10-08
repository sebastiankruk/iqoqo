## Why

Remote GeoNames API authentication requires account activation (`Authorization Exception (value: 10)`) which frequently stalls or fails for free accounts, preventing geographic reconciliation of publication places. Outbound HTTP requests with 5-second timeouts during bulk LOD reconciliation also introduce significant latency and external network fragility. Introducing a local, offline GeoNames gazetteer database (sourced from the official ~3.3 MB `cities15000` dump) enables instant (0ms), credential-free geographic reconciliation that produces identical canonical GeoNames URIs (`https://sws.geonames.org/{geonameId}/`) without network dependencies or container bloat.

## What Changes

- **Local GeoNames Gazetteer Database**: Provide an indexed SQLite database (`data/geonames_cities.db`) containing ~25,000 major publication cities, indexed for case-insensitive lookup.
- **Offline-First Resolver in `GeoNamesClient`**: Update `GeoNamesClient.resolve_location` to check the local SQLite gazetteer first before attempting any remote HTTP API calls.
- **Automated Gazetteer Sync Tooling**: Add `scripts/init_geonames_db.py` (and `make init-geonames` / `make geonames-sync`) to fetch `cities15000.zip` (3.3 MB), unpack, and construct or re-sync the indexed SQLite database on demand.
- **Operational Health Check in `make status`**: Integrate local gazetteer validation into `scripts/iqoqo-status.sh` to report database availability, row count, and sync instructions if missing.
- **Graceful Remote Degradation**: If a city is not in the local gazetteer, attempt the remote API only when credentials exist, cleanly handling HTTP 401 / Error 10 without penalizing the reconciliation worker.
- **High-Throughput Reconciliation**: Eliminate external HTTP round-trips and timeouts for geographic linking during batch catalog reconciliation.

## Capabilities

### Modified Capabilities
- `semantic/lod-linking`: Expand geographic reconciliation requirements to mandate offline-first local gazetteer resolution with remote fallback.

## Impact

- **Affected code**: `app/core/lod_linking_service.py` (`GeoNamesClient`), `scripts/init_geonames_db.py`, `Makefile`, and unit tests.
- **Dependencies**: Uses Python standard library (`sqlite3`, `zipfile`, `csv`); zero new pip dependencies added.
- **Container Footprint**: Uncompressed SQLite database is ~12 MB, staying well within the strict 650 MB container image budget.
- **API Compatibility**: Zero breaking changes. External URI format (`https://sws.geonames.org/{id}/`) and link attribute metadata remain strictly identical.

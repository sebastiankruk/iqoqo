## Why
With the LEGO FRBRoo ontology established in `C103`, collectors need to scan LEGO box EAN/UPC barcodes or type a LEGO Set Number (e.g., `10318` or `10318-1`) to automatically ingest set metadata, cover art, piece counts, minifigure counts, and themes from Rebrickable (with UPCitemdb/brickset fallback), and view/filter LEGO sets in the UI.

## What Changes

- **SSRF-Safe Rebrickable Provider (`app/utils/rebrickable.py`):** Implement Rebrickable v3 API client routed through `app/utils/http_client.py` (socket IP-pinning + `record_outbound_telemetry`), using Fernet-encrypted `REBRICKABLE_API_KEY` stored in `InstanceSettings` (or `.env` fallback) and recording `meta["_provenance"] = "rebrickable"`.
- **`LegoLookupStrategy` (`app/strategies/lego.py`):** Register `LegoLookupStrategy` in `app/api/scanner.py`: resolve EAN/UPC barcodes (via local DB $\to$ Rebrickable barcode/search $\to$ UPCitemdb set-number extraction $\to$ Rebrickable set lookup) and direct LEGO Set Numbers (`^\d{4,6}(-\d+)?$`).
- **Display Projections & UI Facets (`app/core/meta_display.py`, `frontend/`):** Project `set_number`, `piece_count`, `minifig_count`, `theme`, and `build_status` in `meta_display.py`, item sidebar/cards, `edit-item-dialog.tsx`, and collection filter facets, plus expose `REBRICKABLE_API_KEY` in Admin Instance Settings (`/admin/settings`).

## Capabilities

### New Capabilities
- `rebrickable-lego-ingestion-and-ui`: SSRF-safe Rebrickable API client, `LegoLookupStrategy` for barcode and set-number lookup, Fernet-encrypted API key setting, and LEGO metadata display projections.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `app/utils/rebrickable.py`, `app/strategies/lego.py`, `app/api/scanner.py`
- `app/core/meta_display.py`, `app/db/settings.py`, `app/config.py`, `.env.example`
- `frontend/components/admin/instance-settings.tsx`, `frontend/components/item/edit-item-dialog.tsx`
- `frontend/messages/en.json`, `frontend/messages/pl.json`
- `tests/test_rebrickable_strategy.py`, `frontend/__tests__/e2e/lego_workflow.spec.ts`

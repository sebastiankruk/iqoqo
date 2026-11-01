## Purpose
Enable automated ingestion of LEGO sets via Rebrickable (by barcode or LEGO Set Number) and project LEGO-specific attributes across the UI.

## ADDED Requirements

### Requirement: Rebrickable LEGO Lookup Strategy & Graceful Fallback

The scanner API (`/api/scanner/lookup`) SHALL support `lego` media lookups by EAN/UPC barcode and by LEGO Set Number (`10318` or `10318-1`) via `app/utils/rebrickable.py` (routed through SSRF-safe `http_client.py`), and SHALL fall back gracefully to manual entry with pre-filled identifiers if Rebrickable is unconfigured or returns no match.

#### Scenario: Collector looks up LEGO set `10318`
- **GIVEN** `REBRICKABLE_API_KEY` is configured (Fernet-encrypted at rest)
- **WHEN** the user queries `10318` with `media_type="lego"`
- **THEN** `LegoLookupStrategy` normalizes `10318` to `10318-1`, fetches the set metadata (`title`, `piece_count`, `minifig_count`, `year`, `cover_url`), and records `prov:wasDerivedFrom` `"rebrickable"`.

#### Scenario: Rebrickable lookup fails or API key is unconfigured
- **GIVEN** `REBRICKABLE_API_KEY` is unset or external lookup fails
- **WHEN** the user scans a LEGO barcode
- **THEN** the API returns a graceful not-found response without generating fake metadata, pre-filling the scanned barcode in the manual entry form.

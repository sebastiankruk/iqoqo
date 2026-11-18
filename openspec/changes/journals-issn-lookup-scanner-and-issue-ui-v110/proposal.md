## Why

Once `C131` establishes the FRBRoo `F18_Serial_Work` vs. issue `Manifestation` schema, collectors need accurate barcode scanning, cover OCR extraction, external serial lookup, and UI disambiguation to catalog magazines and journals without issue collisions. Physical *National Geographic Polska* examples demonstrate that GS1 `977` periodical EAN-13 barcodes encode only the ISSN base + year/price variant (e.g., `9771507596044` for both `Nr 7(58) Lipiec 2004` and `Nr 12(63) Grudzień 2004`), so standard EAN-13 deduplication wrongly collapses distinct monthly issues into the first scanned issue unless the system detects `977` barcodes, extracts the 2-digit EAN-2 add-on (`07`, `12`, `01`, `06`, `11`) and cover header (`NR <issue>(<cumulative>) <MONTH> <YEAR>`), and routes through serial issue disambiguation.

## What Changes

- **ISSN & GS1 `977` Barcode Parsing (`app/utils/issn.py`)**:
  - Implement Modulo-11 ISSN validation/normalization (`XXXX-XXX[0-9X]`, e.g., `1507-5966`, `0027-9358`).
  - Parse 13-digit (`977` + 7-digit ISSN base + 2-digit variant + check digit) and 15-digit (`977...` + 2-digit EAN-2 issue add-on, e.g., `977150759604407`) barcodes, reconstructing the parent ISSN (`1507596` → `1507-5966`) and extracting the 2-digit variant and optional issue add-on.
- **SSRF-Safe Serial Lookup Strategy & Collision-Free Ingestion (`app/strategies/serials.py`, `app/core/ingest.py`, `app/api/scanner.py`, `app/utils/vision.py`)**:
  - Add `"magazine"` to `scan_formats` and `lookup_strategies` (`SerialLookupStrategy`) in `shared/taxonomy.yaml`.
  - Detect ISSN or `977` prefix prior to book/retail fallback; look up the parent Serial `Work` by ISSN via local DB, Biblioteka Narodowa (`data.bn.org.pl`), Crossref `/journals/{issn}`, OpenLibrary, and Allegro fallback (all using `safe_get` / SSRF protection).
  - **Prevent false issue deduplication:** When a bare 13-digit `977` barcode is scanned without an EAN-2 add-on or exact `(issue_number, publication_year)` match, do NOT auto-bind to the first existing `Manifestation.ean`; return a `"serial_disambiguation"` response with the matched Serial `Work`, existing issues already in the catalog, and a pre-filled `"Add New Issue"` candidate.
  - Extend cover OCR (`app/utils/vision.py`) to parse magazine headers (`NR 7(58) LIPIEC 2004`, `ISSN 1507-5966`, `INDEKS 323357`, and cover headline) so photographing a cover immediately disambiguates the exact issue.
- **Serial Issue UI & Fixtures (`frontend/`, `tests/`)**:
  - Add `Magazine` to scanner top-bar format selector and issue fields (`ISSN`, `Issue #`, `Cumulative #`, `Publication Year / Month`, `Cover Headline`, `2-digit EAN-2 Add-on`) in `ManualEntryForm` and scanner disambiguation modal.
  - Render an `"Issues in this Serial"` chronological grid + `"Add Issue"` quick button on `/work/[id]` when `work_kind === "serial"`.
  - Include all 5 real *National Geographic Polska* issues (`11(50)/2003`, `7(58)/2004`, `12(63)/2004`, `1(64)/2005`, `6(69)/2005`) as canonical test fixtures.

## Capabilities

### New Capabilities
- `journals-issn-lookup-and-issue-ui`: ISSN / GS1 `977` + EAN-2 periodical barcode parsing, SSRF-safe external serial title lookup, magazine cover OCR metadata extraction, collision-free issue disambiguation in `/scan`, and `"Issues in this Serial"` UI on `/work/[id]`.

### Modified Capabilities

## Impact

- **Taxonomy & Backend (`app/`, `shared/`)**: `shared/taxonomy.yaml`, `app/utils/issn.py`, `app/strategies/serials.py`, `app/core/ingest.py`, `app/api/scanner.py`, `app/utils/vision.py`, `app/api/docs.py`.
- **Frontend (`frontend/`)**: `frontend/components/scanner/top-bar.tsx`, `frontend/components/scanner/manual-entry-form.tsx`, `frontend/app/scan/page.tsx`, `frontend/components/work/work-detail-client.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests (`tests/`, `frontend/__tests__/`)**: `tests/test_issn_and_serial_lookup.py`, `tests/test_serial_scan_disambiguation.py`, Vitest serial scanner/work tests, Playwright E2E serial issue test.

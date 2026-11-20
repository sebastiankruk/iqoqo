## 1. ISSN & GS1 977 Parsing Utilities

- [x] 1.1 Create `app/utils/issn.py` implementing Modulo-11 ISSN validation/normalization (`1507-5966`, `0027-9358`), GS1 `977` 13-digit + 15-digit (`EAN-2`) / 18-digit (`EAN-5`) parser, multilingual (EN/PL) cover date parser (`NR 7(58) LIPIEC 2004`), and unit tests covering all 5 *National Geographic Polska* samples (`11(50)/2003`, `7(58)/2004`, `12(63)/2004`, `1(64)/2005`, `6(69)/2005`); verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_issn_and_serial_lookup.py`

## 2. Serial Lookup Strategy, Cover OCR & Collision-Free Ingestion

- [x] 2.1 Implement SSRF-safe `SerialLookupStrategy` in `app/strategies/serials.py` querying local DB, Biblioteka Narodowa (`data.bn.org.pl`), Crossref `/journals/{issn}`, OpenLibrary, and Allegro fallback via `safe_get`, and register `magazine` in `shared/taxonomy.yaml` (`scan_formats` + `lookup_strategies`) and run `make generate-taxonomy`
- [x] 2.2 Update `app/core/ingest.py` (`ingest_serial_issue`) and `app/api/scanner.py` so bare 13-digit `977` barcodes never auto-deduplicate to an arbitrary existing issue `Manifestation`, instead returning `serial_disambiguation` with parent `Work` + existing issues + pre-filled issue template while exact `full_barcode` (15-digit) or `(issn, publication_year, issue_number)` matches cleanly; extend `app/utils/vision.py` magazine cover OCR parsing and update `app/api/docs.py`; verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_serial_scan_disambiguation.py tests/test_ontology.py tests/test_openapi_spec.py`

## 3. Frontend Serial Scanner, Manual Entry & `/work/[id]` Issues Browser

- [x] 3.1 Wire `magazine` format in `frontend/components/scanner/top-bar.tsx`, `frontend/components/scanner/manual-entry-form.tsx`, and `frontend/app/scan/page.tsx` with serial issue fields (`ISSN`, `Issue #`, `Cumulative #`, `Month / Year`, `Cover Headline`, `2-digit EAN-2 Add-on`) and the `977` issue disambiguation / `"Add New Issue"` modal
- [x] 3.2 Add chronological `"Issues in this Serial"` grouped list and `"Add Issue"` quick CTA to `frontend/components/work/work-detail-client.tsx` for `work_kind === "serial"`, add EN/PL keys in `frontend/messages/en.json` and `frontend/messages/pl.json`, add Vitest and Playwright E2E tests (`cd frontend && npx vitest run __tests__/components/scanner/ __tests__/components/work/` and `IQOQO_AI_MODE=1 make test-parallel`)

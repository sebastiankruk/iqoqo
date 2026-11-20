## Purpose

Provide accurate ISSN and GS1 `977` periodical barcode recognition, external serial metadata lookup, cover-photo issue extraction, and issue-level disambiguation and UI browsing so magazines sharing a yearly `977` EAN-13 barcode never collide.

## ADDED Requirements

### Requirement: Modulo-11 ISSN Normalization and GS1 `977` Periodical Barcode Parsing
The system SHALL validate 8-character ISSNs using Modulo-11 check digits (accepting `0`–`9` and `X`) and parse both 13-digit (`977...`) and 15-digit (`977...` + 2-digit EAN-2 add-on) periodical barcodes to reconstruct the canonical parent ISSN (`XXXX-XXXX`), year/price variant, and optional issue add-on.

#### Scenario: Parsing *National Geographic Polska* `977` barcodes with and without EAN-2 add-ons
- **GIVEN** the barcodes `977150759603711`, `977150759604407`, `977150759604412`, `977150759650101`, and `977150759650106` (plus bare 13-digit `9771507596044`)
- **WHEN** `parse_issn_or_977()` evaluates each input
- **THEN** every barcode MUST resolve to canonical `issn == "1507-5966"`, identify the 13-digit `ean` (`9771507596037`, `9771507596044`, `9771507596501`), and extract the respective `ean_addon` (`11`, `07`, `12`, `01`, `06`, or `None` when 13-digit).

### Requirement: Collision-Free `977` Scan Disambiguation and Cover OCR Extraction
Scanning a bare 13-digit `977` periodical EAN-13 barcode SHALL NOT blindly reuse or overwrite the first matching `Manifestation` with that `ean`; instead, the scanner SHALL resolve the parent Serial `Work`, present existing issues for confirmation or `"Add New Issue"`, and allow matching directly by 15-digit `full_barcode` or magazine cover OCR (`NR <issue>(<cumulative>) <MONTH> <YEAR>`, `ISSN`, `INDEKS`, headline).

#### Scenario: Scanning `9771507596044` when July 2004 (`7(58)`) is already cataloged and user scans December 2004 (`12(63)`)
- **GIVEN** *National Geographic Polska* (`ISSN 1507-5966`) exists with issue `7(58)` (`ean="9771507596044"`, `ean_addon="07"`, `full_barcode="977150759604407"`)
- **WHEN** the user scans bare `9771507596044` without specifying an add-on or issue number
- **THEN** the lookup endpoint MUST return `serial_disambiguation` containing the parent `Work`, the existing `7(58)` issue, and pre-filled fields to create a new issue rather than silently returning `7(58)` as an exact match.
- **WHEN** the user scans `977150759604412` (or provides `ean_addon="12"` / cover OCR `NR 12(63) GRUDZIEŃ 2004`)
- **THEN** the system MUST ingest or match issue `12(63)` (`full_barcode="977150759604412"`) under the same parent Serial `Work`.

### Requirement: SSRF-Safe External Serial Lookup with Graceful Manual Fallback
External serial metadata lookup (`SerialLookupStrategy`) SHALL query Biblioteka Narodowa (`data.bn.org.pl`), Crossref, OpenLibrary, and Allegro using SSRF-safe HTTP clients (`safe_get`) and fall back gracefully to pre-filled manual issue entry when external APIs lack issue-level metadata or fail.

#### Scenario: External API has serial title but lacks issue headline
- **GIVEN** an ISSN whose serial title (*National Geographic Polska*) resolves via Biblioteka Narodowa or Crossref while issue-level cover headline is absent externally
- **WHEN** lookup finishes or times out
- **THEN** the system MUST never fabricate fake issue metadata or covers, and MUST pre-fill the serial `Work` title, `ISSN`, `publisher`, and `EAN` in the manual issue entry form so the user can enter issue number/date in $\le 3$ clicks.

### Requirement: Serial Issue Browser on `/work/[id]`
When viewing a Serial `Work` (`work_kind == "serial"`) on `/work/[id]`, the UI SHALL display a chronological `"Issues in this Serial"` view grouped by year alongside an `"Add Issue"` action pre-populated with the parent serial's `ISSN` and metadata.

#### Scenario: Viewing *National Geographic Polska* on `/work/[id]`
- **GIVEN** a serial `Work` with 5 cataloged issues spanning 2003–2005
- **WHEN** a user opens `/work/[id]`
- **THEN** the UI MUST render the issues ordered chronologically by `(publication_year, publication_month / issue_number)` with issue badges (`11(50)`, `7(58)`, `12(63)`, `1(64)`, `6(69)`), cover headlines, and an `"Add Issue"` CTA.

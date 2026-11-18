## Context

See `proposal.md` for motivation and real-world *National Geographic Polska* sample behavior. In `app/core/ingest.py` and `app/api/scanner.py`, barcode scans historically look up `Manifestation` by exact `isbn13`/`ean`/`upc`. For books and board games (`ISBN-13` / `EAN-13`), one EAN uniquely identifies one Manifestation. For serials (`977` prefix), GS1 standard reserves digits 10–11 for price/year variant (NOT issue number!) and encodes the 2-digit or 5-digit issue number only in the supplemental barcode (`EAN-2` / `EAN-5`) that many mobile camera barcode readers omit or read inconsistently.

## Goals / Non-Goals

**Goals:**
- Decode both `ISSN` (`XXXX-XXXX`) and `977` EAN-13 (+ optional EAN-2/EAN-5) reliably in `app/utils/issn.py`.
- Ensure bare `977` scans never auto-select an arbitrary existing issue Manifestation; always prompt issue selection / creation (or resolve via 15-digit `full_barcode` or cover OCR).
- Provide fast `<= 3` click serial issue ingestion from `/scan` and `/work/[id]`, backed by SSRF-safe lookup providers (Biblioteka Narodowa `data.bn.org.pl`, Crossref, OpenLibrary, Allegro).

**Non-Goals:**
- Scraping proprietary publisher subscription portals or paywalled journal archives.
- Fabricating missing issue covers or cover dates if external providers do not supply them.

## Decisions

1. **Special-case `977` prefix at the top of scanner/ingest lookup waterfall (`app/api/scanner.py` & `app/core/ingest.py`):** Before generic `Manifestation.ean == barcode` or book ISBN lookup runs, `is_977_periodical_barcode(barcode)` / `is_issn(barcode)` routes to `SerialLookupStrategy`. If exact `full_barcode` (15-digit `977...+addon`) or explicit `(issn, publication_year, issue_number)` matches an existing `Manifestation`, return it; if only 13-digit `977` is provided, return `status="serial_disambiguation"` with parent `Work` + matching year issues + `"Add New Issue"` option.
2. **Magazine Cover OCR prompt extension in `app/utils/vision.py`:** When a user scans or snaps the cover of a magazine (especially when camera barcode reader strips the 2-digit `EAN-2` add-on), extract `issn`, `indeks`, `issue_number`, `cumulative_issue_number`, `publication_month`, `publication_year`, and `cover_headline` into structured candidate fields so users rarely type them manually.
3. **Biblioteka Narodowa (`data.bn.org.pl`) + Crossref + OpenLibrary + Allegro waterfall:** Polish serials (`ISSN 1507-5966`) resolve cleanly in BN MARC/JSON APIs (`issn:1507-5966`), international academic journals resolve in Crossref `/journals/{issn}`, and retail issues/back-issues have Allegro fallback — all strictly respecting `safe_get` SSRF protection and `5.0s` timeout floor.

## Risks / Trade-offs

- **Hardware barcode scanners stripping EAN-2 add-ons** → Always display the extracted ISSN + year + an interactive `"Issue # / Month"` quick-disambiguation modal (plus optional cover photo OCR button) whenever a 13-digit `977` barcode lacks its 2-digit add-on.
- **Regional month name parsing in cover OCR (e.g. Polish `LISTOPAD`, `LIPIEC`, `GRUDZIEŃ`, `STYCZEŃ`, `CZERWIEC`)** → Include normalized multilingual month-name map (`EN` + `PL`) in `app/utils/issn.py`.

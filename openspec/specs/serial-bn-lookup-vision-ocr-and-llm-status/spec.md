# serial-bn-lookup-vision-ocr-and-llm-status Specification

## Purpose
Ensure periodical barcode lookups (`977` / ISSN) against Biblioteka Narodowa resolve the exact primary serial title and publisher via MARC `022$a` / `245`, harden vision and multi-zone Tesseract cover extraction for 50MP phone photos, bridge `977` barcode disambiguation with 1-tap cover-snap issue auto-fill, and expose AI/Vision (Gemini, Ollama, Tesseract) readiness in `make status` and `GET /api/system/status`.

## Requirements

### Requirement: Biblioteka Narodowa ISSN query and MARC primary serial verification
When resolving an ISSN or GS1 `977` periodical barcode against Biblioteka Narodowa (`data.bn.org.pl`), the system SHALL query `params={"isbnIssn": issn, "kind": "czasopismo"}`, SHALL verify that the candidate record's primary ISSN (MARC `022$a` or normalized `isbnIssn`) matches the requested ISSN rather than a linked or canceled `022$y` reference, and SHALL extract the canonical periodical title from MARC `245$a` + `245$p` (or `222$a`) and publisher from MARC `260$b` / `264$b` rather than returning an unverified book record or concatenated variant title string.

#### Scenario: Looking up National Geographic Polska by ISSN 1507-5966

- **WHEN** the serial lookup strategy queries Biblioteka Narodowa for ISSN `1507-5966` (or barcode `9771507596044`)
- **THEN** the request passes `isbnIssn=1507-5966` and `kind=czasopismo`
- **AND** records whose MARC `022$a` does not match `1507-5966` (such as *National Geographic Traveler* where `1507-5966` appears only in `022$y`) or non-serial book records (`"Matka Teresa : miłość w czynach"`) are rejected
- **AND** the returned metadata contains the clean MARC `245` title `"National Geographic Polska"` and clean publisher name

### Requirement: 50MP camera photo decompression guard and multi-zone cover OCR extraction
The `/api/vision/extract` endpoint and vision/OCR pipeline SHALL accept high-resolution phone camera photos up to 100 megapixels (within the 10 MB upload size limit) without raising `PIL.Image.DecompressionBombError`, SHALL apply EXIF orientation transposition and downscaling before inference, and when executing Tesseract OCR SHALL scan both full-cover and regional masthead/barcode zones (including inverted top masthead strips and bottom/rotated barcode boxes) to extract `issn`, `indeks`, `ean_addon`, `issue_number`, `cumulative_issue_number`, `publication_month`, `publication_year`, and `cover_headline`, enriching `Title` and `Publisher` via `SerialLookupStrategy` whenever a valid ISSN is detected.

#### Scenario: Extracting metadata from a 50MP National Geographic Polska cover photo

- **WHEN** a 50-megapixel (`6144×8160`) cover photo of *National Geographic Polska* is submitted to `/api/vision/extract`
- **THEN** the image is validated, EXIF-transposed, and processed without raising `DecompressionBombError`
- **AND** OCR recognizes masthead labels even when `NR` is slightly garbled by glare (e.g., `11(50) LISTOPAD 2003`, `12(63) GRUDZIEN 2004`) as well as barcode-box `ISSN 1507-5966`, `INDEKS 323357`, spaced `9 771507 596044` EAN-13, and 2-digit EAN-2 add-on markers (`07>`, `11>`, `12>`)
- **AND** when `issn` is detected in Tesseract fallback, `Title` and `Publisher` are enriched from the serial lookup strategy instead of returning raw first-line OCR noise

### Requirement: Barcode disambiguation modal cover-snap bridge and full serial field pre-fill
When `/api/vision/extract` returns serial metadata or when a user clicks **"Snap Cover to Auto-Fill Issue"** inside `SerialDisambiguationModal`, the scanner frontend SHALL pre-fill `Title`, `Publisher`, `issn`, `indeks`, `ean_addon`, `issue_number`, `cumulative_issue_number`, `publication_month`, `publication_year`, and `cover_headline` (plus attach the snapped photo as the cover upload) and switch the active form format to `magazine`.

#### Scenario: Snapping cover from SerialDisambiguationModal after scanning 9771507596044

- **WHEN** a user scans `9771507596044` and opens `SerialDisambiguationModal` for `"National Geographic Polska"`, then uses the **"Snap Cover to Auto-Fill Issue"** action with a cover photo
- **THEN** the scanner merges the parent serial metadata from the barcode (`Title`, `Publisher`, `ISSN`, `EAN`) with the extracted cover issue metadata (`issue_number`, `cumulative_issue_number`, `publication_month`, `publication_year`, `indeks`, `ean_addon`, `cover_headline`) and opens `ManualEntryForm` pre-filled with both sets of fields and the snapped cover file ready to save

### Requirement: AI, Vision, and OCR operational readiness in system status and make status
The system SHALL resolve `ALLOW_LLM`, `GEMINI_API_KEY`, `OLLAMA_URL`, and `OLLAMA_VISION_MODEL` through `ConfigService` (with automatic `http://host.docker.internal:11434` fallback when running inside a container where `localhost:11434` is unreachable) and SHALL report AI/Vision/OCR readiness in both `GET /api/system/status` and `scripts/iqoqo-status.sh` (`make status`), emitting warnings when LLM credentials are configured while `ALLOW_LLM` is disabled or when neither Gemini Vision nor Ollama Vision (with an installed vision model) is active.

#### Scenario: Running make status when GEMINI_API_KEY is in DB or Ollama lacks a vision model

- **WHEN** an operator runs `make status` (or queries `GET /api/system/status`)
- **THEN** the status report displays the `AI / Vision & OCR Providers` checks (`ALLOW_LLM`, `Gemini API`, `OpenAI API`, `Ollama Local LLM` reachability + vision/dedupe models, `Vision Cover Extraction` readiness, and `Tesseract OCR` language packs)
- **AND** warns if `OLLAMA_VISION_MODEL` is not pulled on a reachable Ollama host or if cover vision extraction is degraded to Tesseract-only OCR

## Why

Real-world testing of *National Geographic Polska* issues (`ISSN 1507-5966`, GS1 `9771507596044`, `9771507596037`, `9771507596501`) on `preview.iqoqo.cc` with 6 phone camera photos (`/home/sebastiankruk/Downloads/iqoqo/ng-examples/PXL_*.jpg`) exposed five interconnected bugs across external serial lookup, vision/OCR cover extraction, LLM/Vision operational status visibility, and the barcode-to-cover scanner workflow:
1. `data.bn.org.pl/api/institutions/bibs.json` was queried with `params={"issn": issn}`, which Biblioteka Narodowa's API ignores (its parameter is `isbnIssn`), returning the first book in the National Library database (`"Matka Teresa : miłość w czynach"`, `"Wydawnictwo Velar"`) instead of `"National Geographic Polska"`.
2. 50-megapixel phone camera photos (`6144×8160` = `50,135,040` pixels) exceeded Pillow's default `Image.MAX_IMAGE_PIXELS` limit (`50,000,000`), throwing `PIL.Image.DecompressionBombError` during `/vision/extract` and Tesseract fallback.
3. On `preview.iqoqo.cc`, `GEMINI_API_KEY` was encrypted in `InstanceSettings`, but `ALLOW_LLM` was unset in `.env` and `app/utils/vision.py` read `Config.ALLOW_LLM` (`os.environ` only) rather than `ConfigService`, silently skipping both Gemini and Ollama without warning in `make status` (`scripts/iqoqo-status.sh`). Furthermore, inside Docker containers `OLLAMA_URL` defaulted to `http://localhost:11434` instead of `http://host.docker.internal:11434`, and `deploy/Dockerfile` lacked `tesseract-ocr-pol`.
4. When falling back to Tesseract OCR, `_extract_via_tesseract` ran a single full-page pass without top-masthead / bottom-barcode regional or inverted crops, set `Title = lines[0]` (producing garbage first-line OCR titles instead of enriching via `SerialLookupStrategy` when `issn` is detected), and missed OCR-damaged `NR` prefixes (`ne 11(50) LISTOPAD 2003`, `RMo12(63) GRUDZIEN 2004`) and barcode-box EAN-2 add-on markers (`07>`, `11>`, `12>`).
5. In the scanner UI, `ScanPage.handleExtractComplete` dropped `Publisher` and `ean_addon` from `/vision/extract`, and `SerialDisambiguationModal` lacked a 1-tap **"Snap Cover to Auto-Fill Issue"** bridge to combine a scanned `977` barcode's parent serial metadata with cover vision/OCR issue fields.

## What Changes

- **Biblioteka Narodowa (`data.bn.org.pl`) Serial Lookup & MARC Extraction (`app/strategies/serials.py`)**:
  - Query `https://data.bn.org.pl/api/institutions/bibs.json` using `params={"isbnIssn": issn, "kind": "czasopismo", "limit": "10"}`.
  - Verify primary ISSN ownership against MARC `022$a` (or normalized `bib["isbnIssn"]`) so linked/canceled `022$y` references on spin-off periodicals (e.g., *National Geographic Traveler* `2545-3521`) are filtered out.
  - Extract clean serial title from MARC `245$a` + `245$p` (falling back to `222$a` or cleaned top-level `title`) and clean publisher from MARC `260$b` / `264$b`, resolving `1507-5966` to `"National Geographic Polska"`.
- **50MP Camera Photo Handling, Multi-Zone Serial Cover OCR & ISSN Enrichment (`app/api/scanner.py`, `app/utils/vision.py`, `app/utils/issn.py`, `deploy/Dockerfile`)**:
  - Raise Pillow pixel guard safely (`100_000_000` pixels after the 10 MB upload bound check), apply `ImageOps.exif_transpose`, and downscale oversized images (e.g., max `2400px` dimension) before Gemini, Ollama, or Tesseract processing.
  - Add `tesseract-ocr-pol` to `deploy/Dockerfile` and run `pol+eng` when Polish tessdata is available.
  - Enhance `_extract_via_tesseract` with targeted multi-zone crops (top masthead strip normal + inverted for light-on-dark headers like `NR 11(50) LISTOPAD 2003`; bottom barcode corners normal + 90°-rotated for vertical barcode boxes like `ISSN 1507-5966 INDEKS 323357` and `9 771507 596044 07>`).
  - Harden `parse_cover_issue_label` in `app/utils/issn.py` to recognize OCR-garbled `NR` prefixes (`11(50) LISTOPAD 2003`, `12(63) GRUDZIEN 2004`), spaced `9 77...` EAN-13 strings in OCR text, and 2-digit EAN-2 add-on markers (`07>`, `11>`, `12>`).
  - When `issn` (or a `977` barcode) is extracted from cover OCR, enrich `Title` and `Publisher` via `SerialLookupStrategy` so Tesseract fallback never emits garbage first-line OCR text as the serial title, and select a clean cover headline instead of dumping raw OCR lines into `Authors`.
- **ConfigService Vision Wiring, Docker-Aware Ollama Probe & `make status` AI/Vision Readiness (`app/utils/vision.py`, `app/api/system.py`, `scripts/iqoqo-status.sh`)**:
  - Use `ConfigService` in `app/utils/vision.py` for `ALLOW_LLM`, `GEMINI_API_KEY`, `OLLAMA_URL`, and `OLLAMA_VISION_MODEL` (honoring DB `InstanceSettings` overrides and auto-enabling Gemini/Ollama vision when explicitly configured or `ALLOW_LLM` is enabled in DB/env).
  - When `OLLAMA_URL` is unset or points to `localhost:11434` inside a Docker container where `localhost:11434` is unreachable, automatically probe `http://host.docker.internal:11434`.
  - Expose `llm_vision` health in `GET /api/system/status` and add an **`AI / Vision & OCR Providers`** section to `scripts/iqoqo-status.sh` (`make status`) checking:
    - `ALLOW_LLM` gate status (warning if credentials exist while `ALLOW_LLM` is disabled)
    - `Gemini API` (`GEMINI_API_KEY` in DB `InstanceSettings` or `.env`)
    - `OpenAI API` (`OPENAI_API_KEY` in DB `InstanceSettings` or `.env`)
    - `Ollama Local LLM` reachability + installed vision model (`OLLAMA_VISION_MODEL`) and dedupe model (`OLLAMA_DEDUPE_MODEL`)
    - `Vision Cover Extraction` readiness (warning if neither Gemini Vision nor Ollama Vision is active, leaving only Tesseract OCR)
    - `Tesseract OCR` binary + language packs (`eng`, `pol`)
- **Scanner Frontend Pre-Fill & Barcode-to-Cover Bridge (`frontend/app/scan/page.tsx`, `frontend/components/scanner/serial-disambiguation-modal.tsx`, `frontend/messages/{en,pl}.json`)**:
  - Forward `Publisher` and `ean_addon` in `ScanPage.handleExtractComplete` and auto-switch `activeFormat` to `"magazine"` when vision extraction returns serial fields (`issn`, `indeks`, `issue_number`, `cumulative_issue_number`, `ean_addon`).
  - Add a **"Snap Cover to Auto-Fill Issue"** (`CameraCapture` in `vision` mode) button inside `SerialDisambiguationModal` so a user who scans a `977` barcode can immediately snap the cover to auto-populate `Year`, `2-digit EAN-2 Add-on`, `Issue #`, `Cumulative #`, `Month`, `Indeks`, `Cover Headline`, and the cover photo while preserving the barcode's parent serial `Title`, `Publisher`, `ISSN`, and `EAN-13`.

## Capabilities

### New Capabilities
- `serial-bn-lookup-vision-ocr-and-llm-status`: Accurate Biblioteka Narodowa (`isbnIssn` + MARC `245`/`022`) serial lookup, 50MP-safe multi-zone cover OCR & ISSN enrichment, `SerialDisambiguationModal` cover-snap auto-fill bridge, and `make status` / `/api/system/status` AI, Vision (Gemini/Ollama), and Tesseract OCR health checks.

### Modified Capabilities

## Impact

- **Backend & Infrastructure (`app/`, `scripts/`, `deploy/`)**: `app/strategies/serials.py`, `app/utils/issn.py`, `app/utils/vision.py`, `app/api/scanner.py`, `app/api/system.py`, `scripts/iqoqo-status.sh`, `deploy/Dockerfile`.
- **Frontend (`frontend/`)**: `frontend/app/scan/page.tsx`, `frontend/components/scanner/serial-disambiguation-modal.tsx`, `frontend/components/scanner/camera-capture.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests (`tests/`, `frontend/__tests__/`)**: `tests/test_issn_serials.py`, `tests/test_vision.py`, `tests/test_api.py`, `frontend/__tests__/components/scanner/serial-disambiguation-modal.test.tsx`, `frontend/__tests__/app/scan/page.test.tsx`.

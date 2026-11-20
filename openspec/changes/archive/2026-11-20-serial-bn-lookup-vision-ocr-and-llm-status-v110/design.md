## Context

See `proposal.md` for the five real-world root causes uncovered while scanning *National Geographic Polska* issues (`ISSN 1507-5966`, barcodes `9771507596044`, `9771507596037`, `9771507596501`) and 50MP Pixel camera photos (`ng-examples/PXL_*.jpg`) on `preview.iqoqo.cc`.

## Goals / Non-Goals

**Goals:**
- Resolve Polish periodicals cleanly from Biblioteka Narodowa (`data.bn.org.pl`) by querying `isbnIssn` + `kind=czasopismo`, validating MARC `022$a`, and extracting clean MARC `245$a`/`$p` titles and `260$b`/`264$b` publishers.
- Process up to 100MP camera cover images safely in `/api/vision/extract` and `app/utils/vision.py` with EXIF orientation normalization and downscaling.
- Make Tesseract OCR fallback reliable on real glossy magazine covers via multi-zone regional crops (inverted top masthead + bottom/rotated barcode boxes), resilient `NR <issue>(<cumulative>) <MONTH> <YEAR>` & `977` / `ean_addon` regexes, and `SerialLookupStrategy` title/publisher enrichment when `issn` is detected.
- Bridge `SerialDisambiguationModal` (`977` barcode scan) and `CameraCapture` (`vision` mode) so users can snap the cover right from the disambiguation dialog to auto-fill all issue fields (`Year`, `2-digit EAN-2 Add-on`, `Issue #`, `Cumulative #`, `Month`, `Indeks`, `Cover Headline`) while keeping the parent serial metadata and cover photo.
- Unify `ALLOW_LLM`, `GEMINI_API_KEY`, `OLLAMA_URL` (with `host.docker.internal:11434` container fallback), and `OLLAMA_VISION_MODEL` through `ConfigService`, and surface full AI/Vision/OCR readiness in `GET /api/system/status` and `scripts/iqoqo-status.sh` (`make status`).

**Non-Goals:**
- Changing the FRBRoo `F18_Serial_Work` / `Manifestation` database schema introduced in `C131`.
- Requiring paid cloud LLM access for serial cover scanning (local Ollama vision and multi-zone Tesseract + ISSN lookup enrichment remain first-class zero-cost paths).

## Decisions

### 1. Biblioteka Narodowa MARC `022$a` Verification & `245$a`/`$p` Title Extraction
- **Decision**: In `_fetch_biblioteka_narodowa_by_issn(issn: str)`, pass `params={"isbnIssn": issn, "kind": "czasopismo", "limit": "10"}`. For each returned `bib` dictionary:
  1. Inspect `bib.get("marc", {}).get("fields", [])` for tag `"022"` subfields. Require at least one `"022"` field whose primary subfield `"a"` normalizes via `normalize_issn` to `issn` (or, if `marc` is absent in a simplified response, require `normalize_issn(bib.get("isbnIssn")) == issn` and `bib.get("kind") == "czasopismo"`). This rejects both unrelated books when BN ignores unknown parameters and spin-off serials that only cite `issn` in `022$y` (linked/canceled ISSN, such as *National Geographic Traveler* `2545-3521`).
  2. Extract the canonical title from MARC `"245"` subfields `"a"` and `"p"` (stripping trailing ISBD punctuation `. / : ;`, e.g. `"National Geographic."` + `"Polska /"` → `"National Geographic Polska"`), falling back to MARC `"222"` subfield `"a"` (+ `"b"` if needed) or a cleaned top-level `bib["title"]`.
  3. Extract the primary publisher from MARC `"260"` or `"264"` subfield `"b"` (stripping trailing punctuation), falling back to the first clean segment of `bib["publisher"]`.
- **Rationale**: Top-level `bib["title"]` in BN's JSON API concatenates MARC `210` + `222` + `245` + `246` into a 180-character string, whereas `bib["marc"]["fields"]` contains the exact structured MARC subfields.

### 2. 50MP Image Normalization & Multi-Zone Serial Cover OCR
- **Decision**:
  - Set `_MAX_COVER_PIXELS = 100_000_000` (100 MP) in `app/utils/vision.py` and `app/api/scanner.py` (protected by the existing 10 MB byte-size bound) and add a helper `_normalize_cover_image(image_bytes: bytes, max_dim: int = 2400) -> tuple[Image.Image, bytes]` that applies `ImageOps.exif_transpose(img)`, converts to RGB, and downscales images larger than `max_dim` using `Image.Resampling.LANCZOS`.
  - Pass the normalized JPEG bytes to Gemini and Ollama (reducing payload size from 8.7 MB to ~400 KB and preventing timeout/memory spikes) and the normalized `Image.Image` to `_extract_via_tesseract`.
  - In `_extract_via_tesseract`:
    1. Auto-select `lang="pol+eng"` when `"pol"` is present in `pytesseract.get_languages()`, falling back to default `"eng"`. (Also install `tesseract-ocr-pol` in `deploy/Dockerfile`).
    2. Run OCR on the full image plus focused high-signal zones:
       - **Top masthead strip** (`y: 0..14%` of height, both normal autocontrast and inverted autocontrast for white/yellow text on black/blue headers).
       - **Bottom barcode regions** (`y: 72..96%` of height across left and right halves, both normal autocontrast and 90°/270° rotated for vertical barcodes like *NR 1(64) STYCZEŃ 2005*).
    3. Pass the combined OCR text through `parse_cover_issue_label(combined_text)`.
    4. In `parse_cover_issue_label` (`app/utils/issn.py`):
       - Support OCR-garbled or missing `NR` prefixes before `<issue>(<cumulative>)` when `<issue>` is 1–3 digits and `<cumulative>` is 1–4 digits (e.g., `ne 11(50) LISTOPAD 2003`, `Pr 11(80) LISTOPAD 2003`, `RMo12(63) GRUDZIEN 2004`, `NR 7(58)` / `NR 715 8 )`).
       - Detect spaced/OCR-punctuated `977` barcodes (`9\s*['"°.]?\s*77\d{4}\s*['"°.]?\s*\d{5,6}`) to recover `issn` (`1507-5966`) even if the `ISSN` line above the bars was blurred!
       - Detect 2-digit EAN-2 add-on markers printed above the add-on bars (`\b(0[1-9]|1[0-2]|[1-9]\d)\s*>`) to populate `ean_addon` (and fallback `issue_number` when `ean_addon` is `01`..`12`).
    5. When `parsed_serial.get("issn")` is found in `_extract_via_tesseract`, invoke `SerialLookupStrategy().lookup(parsed_serial["issn"])` to populate canonical `Title` (e.g., `"National Geographic Polska"`) and `Publisher`, rather than setting `Title = lines[0]`. Extract the most prominent uppercase/title-case cover headline line for `cover_headline`, and leave `Authors` empty for serials instead of dumping 20 noisy OCR lines into `Authors`.

### 3. `ConfigService` Vision Wiring, Docker Ollama Auto-Fallback & `make status` AI/Vision Check
- **Decision**:
  - In `app/utils/vision.py`:
    - Resolve `allow_llm = ConfigService.get_bool("ALLOW_LLM", Config.ALLOW_LLM)`. In addition, if `GEMINI_API_KEY` is explicitly configured in `InstanceSettings` (DB override) and the user holds `PermissionName.LLM_GENERATE_CLOUD`, or if `OLLAMA_URL` / `OLLAMA_VISION_MODEL` is explicitly configured in `InstanceSettings`, allow vision extraction even if `.env` left `ALLOW_LLM` unset (unless `ALLOW_LLM` was explicitly set to `"false"` in `InstanceSettings`).
    - Resolve `ollama_url` via `ConfigService.get("OLLAMA_URL")` (defaulting to `http://localhost:11434`, and if running in Docker where `localhost:11434` fails connection, automatically falling back to `http://host.docker.internal:11434`).
    - Resolve `ollama_vision_model` via `ConfigService.get("OLLAMA_VISION_MODEL", "llava")`.
  - Add `get_llm_vision_status()` helper in `app/utils/vision.py` and expose `"llm_vision"` in `GET /api/system/status` (`app/api/system.py`) and in `scripts/iqoqo-status.sh` (`make status`) under a dedicated **`AI / Vision & OCR Providers`** header checking:
    1. `ALLOW_LLM` feature flag (`enabled` vs `disabled`, warning if API keys are configured while disabled).
    2. `Gemini API` (`GEMINI_API_KEY` configured in DB or `.env`).
    3. `OpenAI API` (`OPENAI_API_KEY` configured in DB or `.env`).
    4. `Ollama Local LLM` (reachability at configured URL or `host.docker.internal:11434`, checking whether `OLLAMA_VISION_MODEL` and `OLLAMA_DEDUPE_MODEL` are present in `/api/tags`).
    5. `Vision Cover Extraction` summary (passing if Gemini Vision or Ollama Vision model is ready; warning if neither is active and extraction is degraded to Tesseract-only OCR).
    6. `Tesseract OCR` binary and installed language packs (`eng`, `pol`).

### 4. Scanner Frontend Pre-Fill & `SerialDisambiguationModal` "Snap Cover" Bridge
- **Decision**:
  - Update `ExtractedMetadata` in `frontend/components/scanner/camera-capture.tsx` and `handleExtractComplete` in `frontend/app/scan/page.tsx` to include `Publisher?: string` and `ean_addon?: string`.
  - When `handleExtractComplete` receives any serial field (`issn`, `indeks`, `issue_number`, `cumulative_issue_number`, `ean_addon`), automatically set `activeFormat` to `"magazine"` and populate `serialPreFill` with `Publisher`, `ean_addon`, `issn`, `indeks`, `issue_number`, `cumulative_issue_number`, `publication_month`, `publication_year`, `cover_headline`, and `volume`.
  - In `SerialDisambiguationModal` (`frontend/components/scanner/serial-disambiguation-modal.tsx`), add a **"Snap Cover to Auto-Fill Issue"** (`CameraCapture` with `mode="vision"`, `format="magazine"`, `inline`) button next to **"Add New Issue"**. When the user snaps/uploads a cover from inside `SerialDisambiguationModal`, merge the parent serial metadata from the barcode (`Title`, `Publisher`, `issn`, `ean`, `ean_addon` fallback) with the extracted cover issue fields (`issue_number`, `cumulative_issue_number`, `publication_month`, `publication_year`, `indeks`, `ean_addon`, `cover_headline`, plus the snapped cover `File`) and open `ManualEntryForm` pre-filled with the combined record.

## Risks / Trade-offs

- **[Risk] Multi-zone Tesseract OCR adds CPU time on fallback** → **Mitigation**: Only runs when Gemini and Ollama Vision do not return a result; crops are small regions (`<600px` high) so 4 regional passes complete in `<1.2s` inside the background task worker.
- **[Risk] Ollama probe during `make status` could slow down status checks if host is unreachable** → **Mitigation**: Use a strict `2s` connection timeout on `/api/tags`.

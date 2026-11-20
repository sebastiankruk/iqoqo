## 1. Biblioteka Narodowa (`data.bn.org.pl`) Serial Lookup & MARC Extraction

- [x] 1.1 Update `_fetch_biblioteka_narodowa_by_issn` in `app/strategies/serials.py` to query `params={"isbnIssn": issn, "kind": "czasopismo", "limit": "10"}`, verify primary ISSN ownership against MARC `022$a` (or normalized `isbnIssn` when MARC fields are absent), and extract clean MARC `245$a` + `245$p` (or `222$a`) titles and `260$b`/`264$b` publishers; verify with unit tests in `tests/test_issn_serials.py` that `1507-5966` resolves to `"National Geographic Polska"` and rejects `"Matka Teresa : miłość w czynach"` and *National Geographic Traveler* (`022$y`).

## 2. 50MP Photo Guard, Multi-Zone Cover OCR & ISSN Enrichment

- [x] 2.1 Harden `parse_cover_issue_label` in `app/utils/issn.py` to handle OCR-damaged `NR` prefixes before `<issue>(<cumulative>)` (e.g., `ne 11(50) LISTOPAD 2003`, `Pr 11(80) LISTOPAD 2003`, `RMo12(63) GRUDZIEN 2004`), spaced/punctuated `9 77...` barcodes in OCR text, and 2-digit EAN-2 add-on markers (`07>`, `11>`, `12>`); verify with unit tests in `tests/test_issn_serials.py` covering real OCR strings from all 6 *National Geographic Polska* sample photos.
- [x] 2.2 Raise Pillow `Image.MAX_IMAGE_PIXELS` safely (`100_000_000` pixels) in `app/api/scanner.py` and `app/utils/vision.py`, add `_normalize_cover_image` (`ImageOps.exif_transpose` + RGB conversion + max `2400px` resize), add `tesseract-ocr-pol` to `deploy/Dockerfile`, and upgrade `_extract_via_tesseract` in `app/utils/vision.py` with multi-zone regional OCR (top masthead normal + inverted, bottom barcode corners normal + 90°/270° rotated) and `SerialLookupStrategy` title/publisher enrichment when `issn` is detected; verify with unit tests in `tests/test_vision.py`.

## 3. ConfigService Vision Wiring, Docker Ollama Probe & `make status` AI/Vision Health Checks

- [x] 3.1 Update `app/utils/vision.py` to read `ALLOW_LLM`, `GEMINI_API_KEY`, `OLLAMA_URL`, and `OLLAMA_VISION_MODEL` via `ConfigService`, auto-fallback `OLLAMA_URL` from `localhost:11434` to `http://host.docker.internal:11434` inside Docker when `localhost:11434` is unreachable, and implement `get_llm_vision_status()`; verify with unit tests in `tests/test_vision.py`.
- [x] 3.2 Expose `llm_vision` status in `GET /api/system/status` (`app/api/system.py`) and add the **`AI / Vision & OCR Providers`** section to `scripts/iqoqo-status.sh` (`make status`) checking `ALLOW_LLM`, `Gemini API`, `OpenAI API`, `Ollama Local LLM` (reachability + vision/dedupe models), `Vision Cover Extraction` readiness, and `Tesseract OCR` language packs; verify with `tests/test_api.py` and `IQOQO_AI_MODE=1 bash scripts/iqoqo-status.sh --help`.

## 4. Scanner Frontend Pre-Fill & `SerialDisambiguationModal` Cover-Snap Bridge

- [x] 4.1 Update `frontend/components/scanner/camera-capture.tsx` (`ExtractedMetadata`) and `frontend/app/scan/page.tsx` (`handleExtractComplete`) to forward `Publisher` and `ean_addon`, auto-switch `activeFormat` to `"magazine"` when serial fields are extracted, and support merging cover extraction into an active `serialDisambiguation` parent serial; verify with Vitest tests in `frontend/__tests__/app/scan/page.test.tsx`.
- [x] 4.2 Add a **"Snap Cover to Auto-Fill Issue"** (`CameraCapture` in `vision` mode) action to `frontend/components/scanner/serial-disambiguation-modal.tsx` with EN/PL translations in `frontend/messages/{en,pl}.json`; verify with Vitest tests in `frontend/__tests__/components/scanner/serial-disambiguation-modal.test.tsx`.

## 5. Quality Verification & Stacked PR

- [x] 5.1 Update `.context/notes/plan/1.1.x-release-plan.md` with `C135: serial-bn-lookup-vision-ocr-and-llm-status-v110` and verify `openspec validate serial-bn-lookup-vision-ocr-and-llm-status-v110 --strict` passes.
- [x] 5.2 Run `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and `IQOQO_AI_MODE=1 make test-parallel`, commit and push stacked branch `fix/1.1.0/c135-serial-lookup-vision-ocr-status`, open the PR, and verify GitHub Actions CI is green.

# Design: v1.0.1 Release Review Remediation — Security, Rebrickable SSRF/N+1, LEGO FRBR Columns & UX Hardening (`C108c`)

## Context

This change addresses the 3 Critical (`C-01`–`C-03`) and 7 Moderate (`M-01`–`M-07`) findings from `.context/notes/review/1.0.1/principal-full-release-1.0.1-review.md` on `release/1.0.1`.

## Technical Decisions

### 1. Map Attachment URL Sanitization, Bounds & Audit Logging (`C-01`, `M-07`)

- **Backend (`app/api/manifestations.py`)**:
  - Introduce `_validate_map_attachment_url(raw_url: str) -> str`:
    - Strip whitespace and reject strings `> 500` chars or containing control characters (`[\x00-\x1f\x7f]`).
    - Allow internal static paths starting with `/static/gallery/` (and disallow `..` or `//`).
    - For external URLs, parse with `urllib.parse.urlparse`: require `scheme in {"http", "https"}` and a valid non-private hostname via `validate_external_url()` from `app/utils/http_client.py` (rejecting `javascript:`, `data:`, `file:`, `vbscript:`, `blob:`, `localhost`, and RFC1918/link-local addresses).
  - Sanitize and bound text fields: `title` (`1..200` chars), `scale` (`0..100` chars), `projection` (`0..100` chars).
  - Enforce `MAX_MAP_ATTACHMENTS_PER_MANIFESTATION = 20`.
  - Log `EntityAuditLog(entity_type="Manifestation", entity_id=manifestation.id, action="update", user_id=user.id, changes={"map_attachment_added": attachment})` on `POST` and `{"map_attachment_deleted": attachment_id}` on `DELETE`.
- **Frontend (`frontend/components/item/map-viewer-modal.tsx` & `extended-metadata-maps.tsx`)**:
  - In `MapViewerModal`, validate that `imageUrl` starts with `/`, `https://`, or `http://` (and not `//`); otherwise render the fallback empty state and omit `<a href>`.
  - Add keyboard listener when `open` is true: `+`/`=` -> zoom in, `-` -> zoom out, `r`/`R` -> rotate +90°, `0` -> reset view, `ArrowLeft` / `ArrowRight` -> previous/next attachment.
  - In `ExtendedMetadataMaps`, add `scale` and `projection` inputs to the "Add Map Attachment" dialog and render a Delete (`Trash2`) button on each attachment card when `canEdit && manifestationId && att.id` is present.

### 2. Rebrickable Set Number Regex Guard & N+1 Elimination (`C-02`)

- In `app/utils/rebrickable.py`:
  - Define `_VALID_SET_NUM_RE = re.compile(r"^\d{3,7}(?:-\d{1,2})?$")`.
  - In `fetch_rebrickable_set(set_num_or_query)` and `_fetch_minifig_count(set_num, headers)`:
    - Normalize with `normalize_set_number()`, then verify `_VALID_SET_NUM_RE.match(normalized)`. If it does not match, return `None` / `0` immediately without making a path-interpolated HTTP request.
    - URL-encode `safe_set_num = urllib.parse.quote(normalized, safe="")` before constructing `/sets/{safe_set_num}/`.
  - In `_format_rebrickable_set_payload(data, headers, *, fetch_minifigs: bool = True)`:
    - When `fetch_minifigs=False` (used by `search_rebrickable_sets()`), do not call `_fetch_minifig_count()` per candidate; only resolve cached/single theme names and cap `_THEME_CACHE` at `512` entries.

### 3. First-Class LEGO FRBR Columns & `570201` Barcode Routing (`C-03`, `M-02`)

- In `app/core/ingest.py`:
  - Update `ingest_lego_from_barcode()` to populate `Manifestation.format_type = man_meta.get("format") or MediaFormat.STANDARD_SET`, `Manifestation.ean = stored_barcode` (if 13 digits), and `Manifestation.upc = stored_barcode` (if 12 digits), and deduplicate by `Manifestation.ean` / `Manifestation.upc` / `set_number` before creating a new `Work`/`Expression`/`Manifestation`.
  - Update `ingest_from_meta()` so that when `category == MediaCategory.LEGO` or `format in FormatNormalizer.ALL_LEGO_FORMATS`, it sets `Expression.content_type = MediaCategory.LEGO`, preserves `Work.meta["theme"]` / `subtheme`, and copies `set_number`, `piece_count`, `minifig_count`, `theme`, `release_year`, `age_range`, and `instructions_url` into `Manifestation.meta` while setting `Manifestation.ean` / `Manifestation.upc` / `Manifestation.format_type`.
- In `app/api/scanner.py`:
  - Detect `is_lego_gs1 = len(barcode) == 13 and barcode.startswith("570201")` at the start of `lookup_barcode_preview()` so that even if `format_hint == "book"` (the default scanner tab), `570201xxxxxxx` barcodes route through `LegoLookupStrategy` first and normalize as `MediaCategory.LEGO` / `MediaFormat.STANDARD_SET`.
- In `app/core/format_normalizer.py`:
  - Add `UNKNOWN_LEGO`, `UNKNOWN_BOARD_GAME`, `UNKNOWN_PUZZLE`, and `UNKNOWN_AUDIOBOOK` to `_category_to_unknown_placeholder` and `_UNKNOWN_FORMATS`.

### 4. Keyset Pagination, Escalation Bounds, Federation Host Matching & Status/OpenAPI Parity (`M-01`, `M-03`–`M-06`)

- **`M-01`**: Replace `.offset(offset)` with `.where(Manifestation.id > last_id).order_by(Manifestation.id).limit(batch_size)` in `scripts/verify_ai_cover_bindings.py`, and use `[ -t 0 ]` TTY detection in `Makefile` `fix-ai-covers`.
- **`M-03`**: Add `@field_validator("suggested_properties")` on `NewMediaTypeEscalationPayload` (max 20 items, each `1..100` sanitized chars), `@limiter.limit("10 per minute")` on `create_general_escalation_request` and `create_escalation_request`, and `limit`/`offset` SQL pagination on `list_my_escalation_requests` and `list_escalation_queue`.
- **`M-04`**: Query `select(func.distinct(FederationActivity.actor_uri)).where(FederationActivity.direction == "inbound")` and match parsed hostname `urlparse(uri).hostname.lower() == domain_lower` across `get_federation_instances`, `add_federation_instance`, and `update_instance_trust`.
- **`M-05`**: Add `rebrickable` (`REBRICKABLE_API_KEY`) to `GET /api/system/status` (`app/api/system.py`) and `scripts/iqoqo-status.sh`.
- **`M-06`**: Update `Expression.content_type` enum and map attachment / escalation endpoint schemas in `app/api/docs.py`.

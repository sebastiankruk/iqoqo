## Context

See `proposal.md` for motivation and `.context/notes/review/1.1.0/principal-review-release-1.1.0.md` for line-level evidence. All fixes target `release/1.1.0` prior to tagging `v1.1.0` without introducing schema migrations or breaking existing API response shapes.

## Goals / Non-Goals

**Goals:**
- Resolve the `1` Critical (`C129` `friends_only` share exclusion) and `8` Moderate review findings cleanly with regression tests.
- Preserve FRBR 4-tier purity (`Work → Expression → Manifestation → Item`) and zero-downtime compatibility with existing `release/1.1.0` databases.

**Non-Goals:**
- Low-severity polish items deferred to `C137` (`v111-post-release-polish-and-query-hygiene`).
- New Alembic migrations or UI redesigns.

## Decisions

1. **Shared visibility predicate (`app/api/public_items.py` & `app/core/search_service.py`):**
   - Replace `sa.and_(Item.is_hidden.is_(False), Item.visibility.in_(allowed_vis))` with a clause that applies `Item.is_hidden.is_(False)` strictly to `Item.visibility == "public"` while permitting `Item.visibility.in_(non_public_allowed)` directly.
   - Pass `include_hidden=True` to `SearchService.search_items()` when `allowed_vis` includes `friends_only`/`shared`/`private`, since `visibility` already enforces the exact tier boundary.
   - Always set `Vary: Authorization, Cookie` in `_apply_share_cache_headers()`.
2. **Uniform ownership error & sync in `bulk_update_item_visibility` (`app/api/items.py`):**
   - Query `select(Item).where(Item.id.in_(unique_ids), Item.owner_id == user_id)` and return a uniform `404` (`"One or more items not found or inaccessible"`) when `len(items) != len(unique_ids)` so callers cannot distinguish missing vs. foreign IDs.
   - Dispatch existing ActivityPub/FTS update helpers for items whose `public` state changed, mirroring single-item visibility updates.
3. **Graph BFS batching (`app/core/graph_service.py` & `app/api/works.py`):**
   - Use `selectinload` / batched `WHERE id IN (...)` queries per hop for `WorkPart`, `WorkExpansionLink`, `ContainerAggregation`, `WorkContribution`, `ExpressionContribution`, and `ManifestationContribution`, and filter visible `Item` rows in SQL with `.limit(remaining_budget)`.
   - Add `@limiter.limit("60 per minute")` on `GET /api/catalog/graph` and `urllib.parse.quote_plus(contributor.name)` in `_contributor_node_dict()`.
4. **Vision SSRF, Pillow safety, serial gating & timeout (`app/utils/vision.py`, `app/api/admin.py`, `app/api/manifestations.py`):**
   - Introduce a small URL validator for `OLLAMA_URL` allowing `http`/`https` (including localhost/LAN for self-hosted Ollama), stripping userinfo, and blocking link-local/cloud metadata (`169.254.0.0/16`, `fe80::/10`).
   - Pass `allow_probe: bool = True` to `_resolve_ollama_base_url()` so `get_llm_vision_status(probe_ollama=False)` never makes an outbound HTTP call.
   - Catch `Image.DecompressionBombError` alongside `(OSError, ValueError)` in `upload_cover()` and remove per-request `Image.MAX_IMAGE_PIXELS` mutations (already configured globally at `100_000_000` in `app/__init__.py` and `app/utils/images.py`).
   - Gate `_enrich_llm_serial_result()` and `parse_cover_issue_label()` behind explicit serial cues (`issn`, `977`, `indeks`, `issue_number`, `NR/No./Issue`, or `format == "magazine"`).
   - Keep `OLLAMA_VISION_TIMEOUT` configurable with a default aligned to the frontend vision polling ceiling so cold starts succeed without stalling UI polling indefinitely.
5. **Atomic manual serial ingest & `/scan` hydration (`app/core/ingest.py`, `app/api/schemas.py`, `frontend/app/scan/page.tsx`):**
   - Add `commit: bool = True` to `IngestService.ingest_serial_from_meta()` (defaulting to `True` for direct callers, `False` from `add_item_manual()` which commits once after creating `Item`).
   - Add Pydantic bounds to `ItemManualCreateSchema` matching `ManifestationUpdateSchema`.
   - Hydrate `/scan` URL query parameters inside `useEffect` (with default initial state matching SSR) so initial client render matches server HTML.

## Risks / Trade-offs

- **Uniform 404 vs. 403 in `bulk_update_item_visibility`** → Update existing unit test assertions in `tests/test_api_visibility.py` that explicitly asserted `403` vs `404` so security and tests stay aligned.
- **Serial gating in `vision.py`** → Ensure all 6 real *National Geographic Polska* OCR fixtures still trigger serial enrichment via `ISSN` / `977` / `INDEKS` / `NR` cues.
- **Ollama timeout tuning** → Verify timeout ceiling fits comfortably inside `CameraCapture`'s vision polling timeout so fallback to Tesseract still completes before the frontend aborts.

## 1. Backend Normalization Fixes

- [x] 1.1 Update `_normalize_allegro_product` and `_normalize_allegro_offer` in `app/utils/allegro.py` to omit `set_number`, `piece_count`, and `theme` when `None`, and ensure `Kod producenta` does not mark non-LEGO media as LEGO; verify with `pytest tests/test_lego_allegro.py`.
- [x] 1.2 Update `_normalize_preview_meta` in `app/api/scanner.py` to check truthy `meta.get("set_number") or meta.get("set_num")` instead of key existence and preserve explicit non-LEGO `format_hint` values; verify with `pytest tests/test_lego_allegro.py tests/test_scanner_lookup.py`.

## 2. Frontend Metadata Guards & Manifestation Display Projection

- [x] 2.1 Update `CatalogEntry` in `frontend/types/frbr.ts` to declare `display?: DisplayProjection | null` and forward `display={manifestation.display}` in `frontend/components/manifestation/manifestation-detail-client.tsx`; verify with `npm --prefix frontend run typecheck` (or `make lint`).
- [x] 2.2 Tighten `isLego` detection in `frontend/components/item/extended-metadata.tsx` to use `hasMeta(meta, "set_number") && hasMeta(meta, "piece_count")` only when not an explicit non-LEGO format (`isVideo || isAudio || isBoardGame || isPuzzle`), and guard Audio Release Information against zero fields; verify with Vitest.
- [x] 2.3 Remove attribution-only fallthroughs and add strict empty-card guards in `extended-metadata-video.tsx`, `extended-metadata-boardgame.tsx`, `extended-metadata-puzzle.tsx`, `extended-metadata-lego.tsx` (filtering empty strings on `pieceCount`/`minifigCount`/`missingPieces`/`instructionsIncluded`), and `extended-metadata-maps.tsx`; verify with Vitest.

## 3. Regression Tests & Verification

- [x] 3.1 Add backend pytest regression tests in `tests/test_lego_allegro.py` covering non-LEGO Allegro normalization omitting `None` LEGO fields and `_normalize_preview_meta` preserving `"movie"`/`"book"` when `set_number` is `None`.
- [x] 3.2 Add frontend Vitest regression tests in `frontend/__tests__/components/item/extended-metadata.test.tsx` and `extended-metadata-lego.test.tsx` covering empty TMDB/BGG/Puzzle/LEGO/Maps cards and DVD metadata with `null` or `""` LEGO keys.
- [x] 3.3 Run `make format-python`, `make format-js`, `make secret-scan`, `make lint`, and `IQOQO_AI_MODE=1 make test-parallel`, then commit with Conventional Commits and push the stacked branch.

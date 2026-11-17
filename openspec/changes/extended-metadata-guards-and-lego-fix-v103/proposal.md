## Why

On manifestation and item detail pages (observed on the DVD movie *Palimpsest* sourced via Allegro and TMDB), two UX defects degrade catalog trust and push primary actions off-screen: (1) extended metadata cards such as `Video Details` render completely empty boxes containing only provider attribution (`Powered by TMDB`), and (2) non-LEGO items receive a false-positive `LEGO Set Details` card (showing a blank `PIECE COUNT / Pieces` tile) because Allegro emits `"set_number": None` and `"piece_count": None`, which fool both backend format normalization and frontend `!== undefined` checks.

## What Changes

- **Omit absent LEGO fields in Allegro normalization (`app/utils/allegro.py`)**: Only include `set_number`, `piece_count`, and `theme` in `_normalize_allegro_product` and `_normalize_allegro_offer` when non-None, and restrict the `Kod producenta` 4–6 digit heuristic so non-LEGO items are not polluted with LEGO metadata keys.
- **Check truthy LEGO identifiers in scanner preview normalization (`app/api/scanner.py`)**: Change `_normalize_preview_meta` from `"set_number" in meta or "set_num" in meta` to `bool(meta.get("set_number") or meta.get("set_num"))`, and preserve explicit non-LEGO `format_hint` values.
- **Tighten frontend LEGO classification & empty-value rendering (`frontend/components/item/extended-metadata.tsx`, `extended-metadata-lego.tsx`)**: Use `hasMeta(meta, "set_number") && hasMeta(meta, "piece_count")` (rejecting `null` and `""`) only when the format is not explicitly video, audio, board game, or puzzle; reject empty/whitespace strings in `ExtendedMetadataLego` and return `null` when no LEGO metadata, cover, or link is present.
- **Eliminate zero-metadata cards across all format panels (`extended-metadata-video.tsx`, `extended-metadata-boardgame.tsx`, `extended-metadata-puzzle.tsx`, `extended-metadata-maps.tsx`, `extended-metadata.tsx`)**: Return `null` when no displayable metadata fields or cover exist—never render an empty card solely because `Source === "TMDB"`, `BGG`, or `IGDB`, or when `map_scale`/`map_projection`/`map_attachments` are absent and the viewer cannot edit.
- **Pass server-derived `display` projection to `ExtendedMetadata` on Manifestation detail (`frontend/components/manifestation/manifestation-detail-client.tsx`, `frontend/types/frbr.ts`)**: Align manifestation detail with item detail by typing `display?: DisplayProjection | null` on `CatalogEntry` and passing `display={manifestation.display}`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `metadata-display-projection`: Suppress empty extended metadata section cards when zero displayable metadata fields exist, prevent false-positive LEGO section detection from `null`/empty strings or non-LEGO formats, and forward `display` projection in `ManifestationDetailClient`.
- `lego-allegro-retail-catalog-lookup`: Ensure Allegro normalizers omit `None` LEGO keys (`set_number`, `piece_count`, `theme`) and scanner preview normalization checks truthy LEGO identifiers rather than key existence before coercing format to `standard_set`.

## Impact

- Backend: `app/utils/allegro.py`, `app/api/scanner.py`
- Frontend: `frontend/components/item/extended-metadata.tsx`, `frontend/components/item/extended-metadata-video.tsx`, `frontend/components/item/extended-metadata-boardgame.tsx`, `frontend/components/item/extended-metadata-puzzle.tsx`, `frontend/components/item/extended-metadata-lego.tsx`, `frontend/components/item/extended-metadata-maps.tsx`, `frontend/components/manifestation/manifestation-detail-client.tsx`, `frontend/types/frbr.ts`
- Tests: `tests/test_lego_allegro.py`, `tests/test_scanner_lookup.py`, `frontend/__tests__/components/item/extended-metadata.test.tsx`, `frontend/__tests__/components/item/extended-metadata-lego.test.tsx`

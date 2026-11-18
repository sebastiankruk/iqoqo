## Context

See [proposal.md](./proposal.md) for the problem statement observed on `/manifestation/[id]` for the DVD *Palimpsest* (EAN `5902683995046`, Allegro cover + TMDB metadata).

## Goals / Non-Goals

**Goals:**
- Prevent Allegro retail normalization and scanner preview normalization from emitting or reacting to `None` LEGO keys on non-LEGO media.
- Prevent `ExtendedMetadata` from falsely enabling `ExtendedMetadataLego` on non-LEGO items or `null`/`""` fields.
- Ensure every `ExtendedMetadata*` section component returns `null` when zero displayable fields/covers/actions exist.
- Pass `display={manifestation.display}` from `ManifestationDetailClient` to `ExtendedMetadata`.

**Non-Goals:**
- Changing TMDB lookup to make extra `/movie/{id}?append_to_response=credits` API calls (out of scope for this UI/normalizer bugfix; note that when TMDB only returns basic search fields, the empty `Video Details` box is suppressed cleanly).
- Backfilling existing rows in production Postgres via an Alembic migration (frontend guards handle existing persisted `set_number: null, piece_count: null` or `""` records immediately without requiring DB migration).

## Decisions

1. **Frontend guards handle legacy persisted rows immediately**:
   Even after fixing `app/utils/allegro.py` and `app/api/scanner.py` for new ingests, already-ingested manifestations in the database (like *Palimpsest* on `preview.iqoqo.cc`) still carry `"set_number": null` / `""` and `"piece_count": null` / `""` in `Manifestation.meta`. Therefore, `ExtendedMetadata` MUST use `hasMeta(meta, "set_number") && hasMeta(meta, "piece_count")` AND exclude explicit non-LEGO categories (`!isVideo && !isAudio && !isBoardGame && !isPuzzle`), and `ExtendedMetadataLego` MUST filter blank strings and return `null` if no valid LEGO fields exist.
   - *Alternative considered*: Writing a DB data-migration script to strip `set_number: null` from all `Manifestation.meta` JSON blobs. Rejected as unnecessary risk and latency when frontend guards solve both legacy and edge-case rows cleanly.

2. **Allegro normalizer omits `None` LEGO keys & gates `Kod producenta` heuristic**:
   In `app/utils/allegro.py`, `_normalize_allegro_product` and `_normalize_allegro_offer` only add `"set_number"`, `"piece_count"`, and `"theme"` when truthy/non-None (`piece_count` allows `0` only if `is not None`, though positive in practice; `if val is not None`). Wait: in `_extract_allegro_parameters`, `Kod producenta` is a generic Polish retail parameter ("manufacturer code") used on DVDs, electronics, and books, not only LEGO! Keeping `Kod producenta` from turning a DVD into a LEGO set: `LegoLookupStrategy` (`app/strategies/lego.py`) already has `_extract_set_number_from_title` and explicit LEGO context; in `_extract_allegro_parameters`, `Kod producenta` can remain a fallback ONLY if `Numer produktu`/`Numer zestawu` wasn't set, OR better: keep `Kod producenta` extraction in `_extract_allegro_parameters` (so existing `test_lego_allegro.py` tests pass!) and ensure `_normalize_allegro_product` / `_normalize_allegro_offer` omit `None` keys AND `app/api/scanner.py` only coerces to `STANDARD_SET` when `format_hint` is LEGO/unset or `category == "lego"` (or when `set_number` is truthy AND format is not explicitly video/book/music/boardgame/puzzle!). Let's inspect `tests/test_lego_allegro.py` before deciding on `Kod producenta` so we don't break existing unit tests!

3. **Zero-metadata box suppression in `ExtendedMetadata*`**:
   - `ExtendedMetadataVideo`: remove `meta.Source !== "TMDB"` from the early-return guard.
   - `ExtendedMetadataBoardGame`: remove `source !== "BGG" && source !== "IGDB"` from the early-return guard.
   - `ExtendedMetadataPuzzle`: add early-return guard checking all rendered puzzle fields (`pieceCount`, `dimensions`, `manufacturer`, `artist`, `puzzleType`, `coverUrl`) with blank-string filtering.
   - `ExtendedMetadataLego`: normalize empty strings out of all fields and add early-return guard when no field, cover, or `externalUrl` is valid.
   - `ExtendedMetadataMaps`: return `null` when `!hasMapFields && attachments.length === 0 && !(canEdit && manifestationId)`.

## Risks / Trade-offs

- **Existing unit tests expecting `ExtendedMetadataVideo` with only `Source: "TMDB"` or `ExtendedMetadataLego` with minimal fields**: We will inspect and run `vitest` and `pytest` suites to check if any existing test relies on empty attribution-only cards, and update/add tests accordingly.

---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

The `meta['format']` field on manifestations stores physical kind values (DVD, vinyl, board_game, etc.), but external APIs return non-canonical strings (`"video"`, `"audio"`, `"boardgame"`) that are stored verbatim. This breaks the `?format=` filter and the frontend's Physical Kind facet, making 1,580+ items unfilterable by physical kind. Adding user-configurable normalization, honest unknown-format placeholders, and an interactive audit tool fixes data integrity without requiring users to manually inspect every affected record.

## What Changes

- **Read-time format normalization** — Any read of `meta['format']` passes through a normalizer that maps non-canonical values to canonical `MediaFormat` values or to newly-added `unknown_*` placeholder formats, using user-defined mappings from `shared/format_mappings.yaml`
- **Unknown-format placeholders** — Three new valid `MediaFormat` values added to the taxonomy: `unknown_video`, `unknown_audio`, `unknown_text`, displayed as "Unknown Video Format", "Unknown Audio Format", "Unknown Text Format" in the UI
- **User-customizable format mappings** — New `shared/format_mappings.yaml` file (git-tracked) defines how non-canonical strings and NULL values map to canonical formats, supporting content-type-scoped mappings
- **Interactive audit + fix CLI** — `make fix-physical-kinds` runs `scripts/fix_physical_kinds.py`, which audits the DB for all non-canonical and NULL format values, walks the user through each distinct value, and on `--apply` writes the UPDATE statements to fix data
- **Taxonomy generation updates** — `scripts/generate_taxonomy.py` extended to include `unknown_*` formats and any new taxonomy sections needed for format normalization

## Capabilities

### New Capabilities

- `format-normalization`: Read-time normalization of `meta['format']` values through a pluggable normalizer that resolves non-canonical strings to canonical `MediaFormat` values, supports user-defined overrides in `shared/format_mappings.yaml`, and falls back to `unknown_*` placeholder formats per content type
- `format-mapping-cli`: Interactive command-line tool (`make fix-physical-kinds`) that audits the database for non-canonical and NULL format values, presents a table of distinct values with counts and example titles, walks the user through mapping each value to a canonical format, and optionally applies the fixes as SQL UPDATEs

### Modified Capabilities

None — existing specs are not changed. The Physical Kind facet in `faceted-navigation` already handles any values present in the taxonomy; adding `unknown_*` formats is an extension of the taxonomy, not a requirement change.

## Impact

- **Taxonomy YAML** (`shared/taxonomy.yaml`) — adds `unknown_video`, `unknown_audio`, `unknown_text` formats under movie, music, and text categories
- **Core module** (`app/core/format_normalizer.py`) — new module with `normalize_format(raw, content_type) -> canonical` function
- **Generated taxonomy** (`app/core/taxonomy.py`) — regenerated to include new format constants and potentially a `NORMALIZED_FORMAT_LABELS` map
- **Frontend** — Physical Kind facet and format badge renderers must handle `unknown_*` values (display with icon and "Unknown ... Format" label)
- **No API breaking changes** — format values already accepted as free-form strings; existing endpoints continue to work
- **Database** — no schema changes; only in-place UPDATEs to existing `meta` JSONB columns via the CLI tool
- **Test suite** — new unit tests for `format_normalizer.py`, integration tests for the audit CLI

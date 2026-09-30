---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

iqoqo's FRBR model stores physical kind (media format) in `Manifestation.meta['format']`. External APIs frequently return non-canonical strings:

| API         | Returns       | Canonical taxonomy values (under `movie`)         |
|-------------|---------------|---------------------------------------------------|
| TMDB        | `"video"`     | dvd, bluray, 4k_uhd, vcd, vhs, laserdisc          |
| MusicBrainz | `"audio"`     | cd, vinyl, sacd, cassette, minidisc, cd_dvd_combo |
| BGG         | `"boardgame"` | board_game, cards, rpg_manual, miniatures         |
| IGDB        | `"game"`      | (board_game category)                             |

The existing `format_aliases` section in `shared/taxonomy.yaml` maps these to _categories_ (e.g., `"video" → movie`, `"boardgame" → board_game`), but not to specific formats. The `FORMAT_ALIAS_TO_CATEGORY` dict in the generated taxonomy is used during ingestion to set `Expression.content_type`, but the raw non-canonical string still ends up in `meta['format']`.

This is a data-quality problem at both read and write time:

1. **At write**: the ingest pipeline doesn't attempt to infer a specific physical format (it would require additional metadata like runtime, track count, or disc type)
2. **At read**: the `?format=` filter and Physical Kind facet operate on raw `meta['format']` values, so `"video"` is invisible to both

Additionally, 1,580 books have NULL format — OpenLibrary and manual entries rarely populate this field.

## Goals / Non-Goals

**Goals:**

- Ensure every `meta['format']` read returns a canonical `MediaFormat` value (or an `unknown_*` placeholder)
- Provide an interactive CLI for instance admins to audit and fix non-canonical/NULL formats in bulk
- Keep the solution user-customizable — admins can map `"video"` to `dvd` for their collection
- Add honest `unknown_*` placeholder formats to the taxonomy so the UI can display "Unknown Video Format" rather than hiding items with unknown formats
- Zero breaking changes to existing APIs or database schema

**Non-Goals:**

- Auto-detecting physical format from external API metadata (e.g., inferring DVD vs Blu-ray from TMDB attributes). This requires heuristics beyond the scope of this change.
- Refetching metadata from APIs as part of the normalization pipeline. The CLI tool may _delegate_ to `make refetch-metadata` but the normalizer itself is read-only.
- Changing the ingest pipeline to populate canonical format values. This change focuses on the read path and repair tool.
- Handling `content_type` (Expression-level category). This is already handled by `FORMAT_ALIAS_TO_CATEGORY`.

## Decisions

### Decision 1: Read-time normalization layer (not write-time enforcement)

**Choice**: Intercept `meta['format']` at read-time via `FormatNormalizer.normalize()`.

**Rationale**: The ingest pipeline stores raw API responses faithfully. Enforcing canonical values at write-time would risk data loss or require complex heuristics (is this DVD or Blu-ray?). A read-time normalizer is transparent, reversible, and lets users change their minds about mappings without re-ingesting.

**Alternative considered**: Validate and reject non-canonical values at write-time. Rejected because the format _is_ known (user chose "movie" as the category), just not at the physical-kind granularity. Rejecting would force users to guess a physical kind before saving, adding friction.

### Decision 2: `shared/format_mappings.yaml` as the single source of truth for overrides

**Choice**: A standalone YAML file (not embedded in taxonomy.yaml) with the structure:

```yaml
format_normalizations:
  # Exact value match (any content_type)
  audio: cd
  boardgame: board_game
  video: dvd

  # NULL + content_type scoped match
  null:
    music: cd
    movie: dvd
    text: book
```

**Rationale**:

- Separate from taxonomy.yaml because mappings are per-instance configuration, not ontology — different collections may map `"video"` to `dvd` or `bluray`
- YAML supports `null`/`~` as a key, so NULL format can be mapped per content type
- Machine-writable by the CLI tool, human-readable for manual edits
- Git-tracked so it travels with instance data

**Alternative considered**: Store in DB. Rejected — adds migration complexity, harder to inspect/share, harder to version alongside instance config.

### Decision 3: `unknown_*` placeholders as valid MediaFormat values

**Choice**: Add `unknown_video`, `unknown_audio`, `unknown_text` to the taxonomy as concrete `MediaFormat` entries.

**Rationale**:

- The Physical Kind facet renders any `MediaFormat` value that has a label in the taxonomy. Without `unknown_*`, items with unresolved formats would be filtered out of the facet entirely.
- Displaying "Unknown Video Format" is honest — better than hiding items or showing raw `"video"` which is meaningless to users.
- Users can filter by `unknown_video` to find all items needing format cleanup.

**Alternative considered**: Return `None`/omit the format field for unresolved values. Rejected — breaks the `?format=` filter for those items, and the frontend has no way to show an "unknown" badge.

### Decision 4: Interactive CLI approach for the mapping builder

**Choice**: `scripts/fix_physical_kinds.py` with three modes:

1. **Audit mode** (default): Scans `Manifestation.meta['format']`, groups by distinct non-canonical value, prints a table with counts and example titles
2. **Interactive mode** (`--interactive`): Walks the user through each distinct value, asks them to map to a canonical format, writes mappings to `shared/format_mappings.yaml`
3. **Apply mode** (`--apply`): Reads `shared/format_mappings.yaml`, performs DB UPDATEs to fix all matching rows

**Rationale**:

- Safety: audit-first-then-apply pattern prevents accidental data changes
- The CLI uses rich text tables for readability
- Skipping NULL format for books (1,580 items) is explicitly supported — the tool asks per content-type scope
- Delegates to `make refetch-metadata` as a fallback option for NULL values where a refetch might populate the format from a fresh API call

### Decision 5: Resolution order

The normalizer resolves in this priority order:

1. Exact match in `format_normalizations` key → mapped canonical value
2. NULL value + content_type match under `format_normalizations.null.{content_type}` → mapped canonical value
3. Value matches a known `MediaFormat` constant (already canonical) → pass through
4. Fallback to `unknown_{category}` based on `FORMAT_ALIAS_TO_CATEGORY` lookup of the raw value
5. Final fallback: if raw value resolves to `text` category → `unknown_text`; `music` → `unknown_audio`; `movie` → `unknown_video`; `board_game`/`puzzle` → the category's first format

## Risks / Trade-offs

| Risk                                                                                    | Mitigation                                                                                                                                              |
|-----------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `format_mappings.yaml` grows stale as new items are added with new non-canonical values | CLI audit mode can be re-run periodically; new values appear in the audit table                                                                         |
| User maps `"video"` to `dvd` but some items are actually Blu-ray                        | The normalizer is a best-effort read-time transformation. Users should verify their mapping choices. The CLI shows example titles to help users decide. |
| NULL format for 1,580 books — too many to manually assign                               | CLI supports batch mapping (map all NULL+text to `book` with one keypress). Also offers refetch for individual items.                                   |
| `unknown_*` values in the facet may confuse users                                       | Labels use clear, readable names ("Unknown Video Format"), not raw IDs. UI can show a help tooltip.                                                     |
| Mapping file format evolution                                                           | Schema is simple (flat dicts). Backward-compatible by design — new keys can be added without breaking old configs.                                      |
| Performance: normalizer runs on every format read                                       | Normalizer is O(1) dict lookups. No measurable impact on page load.                                                                                     |

## Migration Plan

1. **Taxonomy update** — Add `unknown_*` formats to `shared/taxonomy.yaml` and regenerate `taxonomy.py` and `taxonomy.ts`
2. **Normalizer deployment** — Deploy `app/core/format_normalizer.py` and wire into read paths (manifestation serialization, facet aggregation, search filter)
3. **Default fallback behavior active** — At this point, non-canonical values render as "Unknown Video Format" etc. — no data changes yet, just honest UI
4. **Instance admin runs audit** — `make fix-physical-kinds` shows the audit table
5. **Admin builds mappings** — `make fix-physical-kinds --interactive` to walk through each value
6. **Admin applies fixes** — `make fix-physical-kinds --apply` updates DB; old raw values are overwritten with canonical ones
7. **Rebuild search index** — If FTS index indexes `meta['format']`, a rebuild ensures corrected values are searchable

**Rollback**: `format_mappings.yaml` can be edited or deleted to revert. DB updates are one-way — no automatic rollback. Backup DB before `--apply`.

## Open Questions

- Should the normalizer also normalize `Manifestation.meta['format']` on the _write_ path in future ingest cycles? (Out of scope for this change, but the normalizer's function signature supports it.)
- Should the frontend display a visual distinction (e.g., warning icon) next to `unknown_*` format badges to signal that the physical kind needs verification?
- For `board_game` and `puzzle` categories where the canonical format ID equals the category ID, should `"boardgame"` or `"game"` map directly to `board_game` format or to `unknown_video`? (Decision: map to `board_game` since it's the most common default.)

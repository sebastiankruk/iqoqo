---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Taxonomy — Add unknown placeholder formats

- [x] 1.1 Add `unknown_video` format under `movie` category, `unknown_audio` under `music`, and `unknown_text` under `text` in `shared/taxonomy.yaml`. Each gets a human-readable `label` (e.g., "Unknown Video Format")
- [x] 1.2 Add `unknown_*` to `format_aliases` if needed for resolver fallback (verified: they are already canonical and included in `FORMAT_ALIAS_TO_CATEGORY` via the generator merge logic)
- [x] 1.3 Run `make generate-taxonomy` to regenerate `app/core/taxonomy.py`, `frontend/types/taxonomy.ts`, and `docs/ontology/taxonomy.ttl`
- [x] 1.4 Verify generated `MediaFormat` class includes `UNKNOWN_VIDEO`, `UNKNOWN_AUDIO`, `UNKNOWN_TEXT` constants and that `FORMAT_TO_CATEGORY` maps them correctly

## 2. Core — Format normalizer module

- [x] 2.1 Create `app/core/format_normalizer.py` with `FormatNormalizer` class and `normalize_format(raw: str | None, content_type: str | None) -> str` function
- [x] 2.2 Implement the resolution chain: (1) exact match in user mappings → (2) NULL+content_type match → (3) already canonical pass-through → (4) fallback via `FORMAT_ALIAS_TO_CATEGORY` → (5) ultimate fallback to `unknown_text`
- [x] 2.3 Implement `_load_mappings()` that reads `shared/format_mappings.yaml` (handles `FileNotFoundError` gracefully)
- [x] 2.4 Add validation: log a warning when a user mapping targets a non-existent `MediaFormat` value, and fall back to `unknown_*`
- [x] 2.5 Implement `is_canonical(value: str) -> bool` helper for downstream use (e.g., the CLI audit)

## 3. Backend — Wire normalizer into read paths

- [x] 3.1 Add `normalize_format()` call in manifestation serialization helper: format filter expansion in `app/api/manifestations.py`, `app/api/items.py`, and `app/api/system.py`; facet count normalization in `app/core/data_manager.py`
- [x] 3.2 Update Physical Kind facet aggregation in `app/core/data_manager.py` to normalize format values after `GROUP BY` via `normalize_format_counts()`
- [x] 3.3 Update `?format=` filter in search/collection endpoints via `expand_format_filter()` that includes raw values mapping to the requested canonical format
- [x] 3.4 Ensure the `format` badge/label in all manifestation detail views uses the normalized value (format filter expansion ensures matching; frontend taxonomy provides labels for all canonical formats)

## 4. Frontend — Handle unknown format values

- [x] 4.1 Verify `frontend/types/taxonomy.ts` is regenerated and includes `unknown_video`, `unknown_audio`, `unknown_text` in `MEDIA_FORMATS`
- [x] 4.2 Ensure the Physical Kind facet renders `unknown_*` values with their human-readable labels from the taxonomy (via `t(fmt_${fmt.id}, {defaultValue: fmt.label})` which resolves to taxonomy labels)
- [x] 4.3 Ensure the format badge component gracefully handles `unknown_*` values: added `unknown_video` to isVideo check in `extended-metadata.tsx` and `unknown_audio` to `isAudioMedia()` in `utils.ts`
- [x] 4.4 Optional: Add a subtle visual distinction (italic styling) for `unknown_*` format badges in the sidebar facet to signal that the physical kind needs verification

## 5. CLI tool — Audit, interactive, and apply modes

- [x] 5.1 Create `scripts/fix_physical_kinds.py` with argument parser supporting `--interactive`, `--apply`, `--dry-run`, `--content-type` (filter), and `--limit`
- [x] 5.2 Implement audit mode (default): query DB for non-canonical `meta['format']` values, group by `(format_value, content_type)`, print table with columns: stored value, content type, count, example titles (up to 3)
- [x] 5.3 Include NULL format rows in audit: query manifestations with `meta['format'] IS NULL`, group by content_type, show in the audit table
- [x] 5.4 Implement interactive mode: for each distinct value, prompt user to select a canonical format from the list of valid formats for that content type, show example titles for context, support "skip" option
- [x] 5.5 Implement NULL handling in interactive mode: for each (NULL, content_type) pair, prompt to map to a canonical format with batch option for large counts
- [x] 5.6 Interactive mode: detect already-mapped values and skip with a note; supports resuming by reading existing format_mappings.yaml
- [x] 5.7 Implement mapping persistence: write user selections to `shared/format_mappings.yaml` in the `format_normalizations` structure (exact value matches + null.content_type matches)
- [x] 5.8 Implement apply mode: read `format_mappings.yaml`, build and execute SQL UPDATEs for each mapping rule, report rows affected
- [x] 5.9 Implement `--dry-run` for apply mode: show SQL statements and affected row counts without executing
- [x] 5.10 Validate mapping targets before apply: ensure all target values are valid `MediaFormat` values
- [x] 5.11 Add DB connection support using existing app config (`create_app()` from `app` module)

## 6. Makefile integration

- [x] 6.1 Add `fix-physical-kinds` target to `Makefile` that runs `scripts/fix_physical_kinds.py` with the project's Python environment (`.venv/bin/python`)
- [x] 6.2 Support argument passthrough: `make fix-physical-kinds ARGS="--interactive"` forwards flags to the script
- [x] 6.3 Add `fix-physical-kinds` to the `help` target's output so it appears in `make help`

## 7. Seed mapping file

- [x] 7.1 Create `shared/format_mappings.yaml` with the `format_normalizations:` key and commented-out example mappings showing the structure (exact match, null scoped)
- [x] 7.2 Include sensible defaults as comments: `# video: dvd`, `# audio: cd`, `# null.text: book`, etc., to guide instance admins

## 8. Tests

- [x] 8.1 Unit tests for `format_normalizer.py`: test canonical pass-through, user mapping resolution, NULL+content*type resolution, fallback to unknown*\*, idempotency, invalid mapping target
- [x] 8.2 Unit tests for `format_normalizer.py`: test with empty/missing `format_mappings.yaml`, test with `null` key in YAML
- [x] 8.3 Integration tests for `scripts/fix_physical_kinds.py` audit mode: verify table output format, verify canonical values are excluded, verify NULL grouping
- [x] 8.4 Integration tests for apply mode with `--dry-run`: verify correct SQL is generated without modifying DB; apply mode test verifies actual DB update via SQLite fallback
- [x] 8.5 Frontend test: verify `unknown_*` format badges render with correct label text (validated via backend taxonomy tests that `FORMAT_TO_CATEGORY` maps `unknown_*` correctly)

## 9. Documentation

- [x] 9.1 Add section to `INSTALL.md` describing the `make fix-physical-kinds` workflow: audit → interactive mapping → apply
- [x] 9.2 Document the `shared/format_mappings.yaml` schema with examples (in INSTALL.md and in the file's own comments)
- [x] 9.3 Note that `format_mappings.yaml` is git-tracked and per-instance — different deployments may have different mappings

## Context

In `iqoqo development notes.md`, a bug was recorded: *"some ai generated cover pages are attached to wrong books - possibly after migration #bugs"*. During early flat-to-FRBR migrations and entity merges, cover filenames keyed by legacy `item_<id>` or shifted manifestation IDs remained attached to the wrong `Manifestation.cover_url`.

## Goals / Non-Goals

**Goals:**
- Identify all `Manifestation` rows where an AI-generated cover filename (`_gemini`, `_openai`, `_localsd`) or S3 key does not match the manifestation's `isbn13`, `id`, or historical `EntityAuditLog` provenance.
- Provide a safe `--dry-run` report and an `--apply` repair mode (`make fix-ai-covers`) that unbinds mismatched covers and triggers accurate cover re-resolution.

**Non-Goals:**
- Mutating `Work` (F1) or `Item` (F5) condition records (cover art belongs strictly to `Manifestation` F3).

## Decisions

### Provenance Cross-Check Before Unbinding
* **Decision:** Flag a cover binding as mismatched when `cover_url` references an `item_<N>_*` or `<isbn>_*` prefix where `<isbn>` differs from `Manifestation.isbn13` / `upc` or `<N>` belongs to an `Item` whose `manifestation_id != Manifestation.id`.
* **Rationale:** Deterministically catches ID-shift mismatches from legacy `item_<id>` cover naming without false-positive removal of valid covers.

## Risks / Trade-offs

- **Risk:** Running `--apply` on production without inspecting the diff.
  - **Mitigation:** Default to `--dry-run` and require explicit `--apply` (plus typed database confirmation when `FLASK_ENV=production`).

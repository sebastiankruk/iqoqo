# ai-cover-binding-audit-and-repair Specification

## Purpose

Audit and repair FRBR F3 Manifestations where AI-generated cover files were attached to the wrong book after database migrations.

## Requirements

### Requirement: Mismatched AI Cover Detection & Repair CLI

The system SHALL provide `scripts/verify_ai_cover_bindings.py` (invocable via `make fix-ai-covers`) that detects `Manifestation` rows whose AI-generated `cover_url` (`_gemini`, `_openai`, `_localsd`) references a different ISBN or an `Item` belonging to another `Manifestation`, and unbinds/re-queues them when `--apply` is passed.

#### Scenario: Mismatched AI cover detected and repaired

- **GIVEN** `Manifestation` #100 (ISBN `9780000000100`) has `cover_url="/api/static/covers/9789999999999_gemini.jpg"` or references an `item_<id>` belonging to `Manifestation` #200
- **WHEN** `scripts/verify_ai_cover_bindings.py --apply` is executed
- **THEN** `Manifestation` #100's mismatched `cover_url` is cleared, an `EntityAuditLog` entry is recorded, and valid `Manifestation` covers remain untouched.

### Requirement: Keyset Pagination in `verify_and_repair_ai_covers` and Interactive Production TTY in `make fix-ai-covers` (`M-01`)

`scripts/verify_ai_cover_bindings.py` MUST paginate `Manifestation` rows using keyset pagination (`Manifestation.id > last_id`), and `Makefile` `fix-ai-covers` MUST preserve interactive TTY allocation when prompting for production database confirmation.

#### Scenario: Keyset pagination across batches during `--apply`

- **GIVEN** multiple batches of manifestations with AI-generated cover URLs
- **WHEN** `verify_and_repair_ai_covers(apply=True, batch_size=2)` runs
- **THEN** each batch query MUST filter by `Manifestation.id > last_id` ordered by `Manifestation.id` so every matching row is inspected exactly once.

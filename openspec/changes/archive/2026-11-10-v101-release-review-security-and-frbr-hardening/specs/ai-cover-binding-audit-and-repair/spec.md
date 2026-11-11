# Delta Specification: AI Cover Binding Audit and Repair (`C108c`)

## ADDED Requirements

### Requirement: Keyset Pagination in `verify_and_repair_ai_covers` and Interactive Production TTY in `make fix-ai-covers` (`M-01`)

`scripts/verify_ai_cover_bindings.py` MUST paginate `Manifestation` rows using keyset pagination (`Manifestation.id > last_id`), and `Makefile` `fix-ai-covers` MUST preserve interactive TTY allocation when prompting for production database confirmation.

#### Scenario: Keyset pagination across batches during `--apply`

- **GIVEN** multiple batches of manifestations with AI-generated cover URLs
- **WHEN** `verify_and_repair_ai_covers(apply=True, batch_size=2)` runs
- **THEN** each batch query MUST filter by `Manifestation.id > last_id` ordered by `Manifestation.id` so every matching row is inspected exactly once.

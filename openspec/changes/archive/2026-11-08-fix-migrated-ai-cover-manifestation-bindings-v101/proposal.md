## Why
After database migrations and consolidation across `0.7.x`–`0.9.x`, some AI-generated book cover files (`_gemini.jpg`, `_openai.jpg`, `_localsd.jpg`) became bound to the wrong `Manifestation` (F3) records, causing books to display mismatched cover art.

## What Changes

- **Diagnostic & Repair CLI Script (`scripts/verify_ai_cover_bindings.py`):** Cross-check every `Manifestation` whose `cover_url` or local/S3 asset points to an AI-generated cover (`item_<id>_gemini.jpg`, `<isbn>_gemini.jpg`, etc.) against `Manifestation.id`, `Manifestation.isbn13`, `EntityAuditLog`, and `LLMTelemetry` / `MetadataRefetchLog` records to detect mismatched bindings.
- **Dry-Run & Automated Repair (`--dry-run` / `--apply` + `make fix-ai-covers`):** When a mismatch is detected, unbind the wrong cover from `Manifestation.cover_url`, attempt a clean provider cover lookup (`app/utils/covers.py`), or reset `cover_status` so accurate cover art is fetched/generated for the right `Manifestation`.
- **Operational Safety Guard:** Enforce production confirmation guards on `--apply` mutations per our Operational Script Guards rule.

## Capabilities

### New Capabilities
- `ai-cover-binding-audit-and-repair`: Diagnostic and automated repair tool (`scripts/verify_ai_cover_bindings.py` + `make fix-ai-covers`) for fixing post-migration AI-generated cover mismatches on FRBR F3 Manifestations.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `scripts/verify_ai_cover_bindings.py`
- `Makefile` (`fix-ai-covers` target)
- `tests/scripts/test_verify_ai_cover_bindings.py`

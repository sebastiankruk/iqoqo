## Why

As part of the v0.7.18 pre-release review, 203 moderate issues were identified. To ensure smooth progression into the v0.8.0 Federation milestone, these moderates are being triaged into three strategic phases. This change addresses Phase 1 (Pre-0.8.0): high-leverage, non-FRBR moderates focused on Security, Ops, and API Hardening, along with the completion of the API credentials migration from `.env` to the encrypted `InstanceSettings` DB registry.

## What Changes

- Complete the shift of 16 external API secrets from `.env` to the encrypted DB registry.
- Rate limiting: Add `@limiter.limit` decorators to public endpoints, profile searches, and collection creation to prevent abuse/enumeration.
- Input validation: Validate `avatar_url` to prevent SSRF/XSS vectors.
- XSS prevention: Replace the naive regex XSS filter with a robust parser like `bleach`.
- Ops robustness: Add subprocess timeouts (e.g., `rclone`), harden test-reset endpoints, and bound memory usage on public endpoints.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None.

## Impact

- `app/core/config_service.py`
- `.env.example`
- Admin settings UI
- Various API endpoints across `app/api/` (public, profile, sharing, social, lending, feedback)

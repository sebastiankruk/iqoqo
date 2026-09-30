## Why

The v0.8.1 security code review and performance audit uncovered several moderate-severity issues and one critical UX issue. Fixing these in the v0.8.2 patch release is necessary to maintain security posture (rate limits, malicious URL validation) and resolve performance bottlenecks (N+1 queries, unoptimized cache invalidation) before the system scales.

## What Changes

- **Rate Limits**: Add `@limiter.limit()` decorators to public endpoints (`app/api/public_items.py`, `app/api/public_profile.py`, `app/api/lending.py`, `app/api/roadmap.py`) with 60/min read and 30/min write limits.
- **N+1 Queries**: Optimize SQLAlchemy queries in Admin User List (`app/api/admin.py`) and FRBR Service (`app/core/frbr_service.py`) using `selectinload` and `joinedload`.
- **Public Module Shim**: Remove `_PublicModuleShim` from `app/api/public.py` and update all imports to target specific modules directly.
- **OAuth Avatar Validation**: Add safety validation to OAuth callback avatar URLs in `app/api/auth.py`, falling back to `None` if invalid or non-HTTPS.
- **Bio Length Limit**: Introduce a 500-character length limit validation for user biographies in `app/api/profile.py`.
- **FRBR Editor Caching**: Implement optimistic cache updates via `onMutate`/`onSettled` in `frontend/components/admin/frbr-editor.tsx` and `relation-management-dialog.tsx` to eliminate jarring remounts.

## Capabilities

### New Capabilities
- `security/rate-limiting`: Introduces strict rate limits on public-facing endpoints.
- `security/input-validation`: Formalizes validation for external inputs like OAuth avatar URLs and profile bios.

### Modified Capabilities

## Impact

- **API**: Public endpoints will enforce rate limits. `update_profile` will reject bios over 500 characters with a 400 error.
- **Frontend**: FRBR Editor will feel snappier and avoid unnecessary refetches.
- **Database**: Reduced query load on Admin and FRBR views due to N+1 optimizations.

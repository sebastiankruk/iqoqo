---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

The v0.7.11 release underwent a comprehensive team review (PM, Dev, QA, SRE, Security×2, UX, Ontologist, TechComm) via PR #159. While the release was approved by all reviewers, several actionable findings were raised that must be addressed before the final merge to `main`. These fall into three categories: **security hardening** (URL query-string credential leakage, cookie/session header redaction), **code quality** (inline comma-split query parameter parsing should use a shared utility), and **UX polish** (filter bar scrollbar removal, mobile filter pill glassmorphism, wishlist icon distinction).

## What Changes

- **Telemetry URL sanitization**: Add `sanitize_url()` to `app/core/telemetry.py` that strips sensitive query parameters (`key`, `token`, `secret`, `auth`, `signature`, `credential`) from URLs before they reach OpenObserve spans or application logs. Wire it into `record_outbound_telemetry`.
- **Header redaction expansion**: Extend `sanitize_headers()` to also redact `cookie` and `session` header keys, preventing session token leakage into telemetry.
- **Telemetry sanitization tests**: Add parameterized pytest cases for `sanitize_headers` (covering `X-API-KEY`, `x-amz-security-token`, `Authorization`, `Cookie`, `Set-Cookie`) and `sanitize_url` (covering `?api_key=`, `?signature=`, presigned URL patterns).
- **Query parameter parsing utility**: Extract the repeated `[c.strip() for c in param.split(",") if c.strip()]` pattern from `items.py`, `manifestations.py`, `system.py` into a shared helper (`parse_csv_param`) in `app/api/filters.py`, centralizing validation and preventing malformed input drift.
- **Filter bar scrollbar removal**: Strip the visible horizontal scrollbar from the active filter chip row in `filter-bar.tsx` using `[scrollbar-width:none]` and `[&::-webkit-scrollbar]:hidden` for a premium feel.
- **Mobile filter pill glassmorphism**: Restyle the floating filter pill in `collection/page.tsx` with `bg-black/80 backdrop-blur-md border-white/10` to demote it as a secondary CTA below the primary Add/Scan action.
- **Wishlist "View" icon distinction**: Change the "View Wishlist Item" icon from `BookmarkPlus` (which implies adding) to `Eye` (which implies navigating/viewing) in `add-to-collection-dropdown.tsx` to reduce cognitive friction.

## Capabilities

### New Capabilities

_None — all changes are hardening/polish of existing capabilities._

### Modified Capabilities

- `external-api-telemetry`: Add URL query-string sanitization requirement and expand header redaction scope to include cookie/session headers.
- `faceted-navigation`: Remove visible scrollbar from the active filter chip row; restyle mobile filter trigger with glassmorphism.

## Impact

- **Backend**: `app/core/telemetry.py`, `app/api/filters.py`, `app/api/items.py`, `app/api/manifestations.py`, `app/api/system.py`
- **Frontend**: `frontend/components/collection/filter-bar.tsx`, `frontend/app/collection/page.tsx`, `frontend/components/collection/add-to-collection-dropdown.tsx`
- **Tests**: New pytest cases in `tests/test_telemetry.py`; existing Vitest/Playwright tests may need minor assertion updates.
- **No database migrations required** — `MetadataRefetchLog` migration already exists (`0c3eaee0322b`).
- **No breaking API changes**.

---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Telemetry Security Hardening

- [x] 1.1 Add `sanitize_url()` function to `app/core/telemetry.py` — parse URL with `urlparse`, iterate `parse_qsl` params, redact values where key contains `key|token|secret|auth|signature|credential`, reconstruct with `urlunparse`. Return `***REDACTED_URL_PARSE_ERROR***` on parse failure.
- [x] 1.2 Refactor `sanitize_headers()` in `app/core/telemetry.py` — replace chained `or` conditions with a `set` of sensitive keywords: `{"authorization", "key", "token", "secret", "cookie", "session"}`. Use `any(kw in key_lower for kw in sensitive_keywords)`.
- [x] 1.3 Wire `sanitize_url` into `record_outbound_telemetry()` — call `sanitize_url(url)` before setting `http.url` span attribute and before writing to structured log. Both the span and the log must receive the sanitized URL, never the raw URL.
- [x] 1.4 Add `from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse` imports to `app/core/telemetry.py`.

## 2. Telemetry Test Coverage

- [x] 2.1 Create `tests/test_telemetry_sanitization.py` with parameterized pytest cases for `sanitize_headers` — test vectors: `Authorization`, `X-API-KEY`, `x-amz-security-token`, `Cookie`, `Set-Cookie`, `X-Session-ID` (all must be redacted), plus `User-Agent`, `Accept`, `Content-Type` (must be preserved).
- [x] 2.2 Add parameterized pytest cases for `sanitize_url` — test vectors: `https://api.example.com?api_key=SECRET&page=1` (redact api_key, preserve page), `https://s3.amazonaws.com/bucket?X-Amz-Signature=abc&X-Amz-Credential=def` (redact both), `https://example.com/path` (no query, return unchanged), empty string (return empty), malformed URL (return sentinel).
- [x] 2.3 Add integration test for `record_outbound_telemetry` — verify that the returned sanitized headers dict has redacted values, and that the function does not raise exceptions when OTel is not available.

## 3. Query Parameter Parsing Utility

- [x] 3.1 Add `parse_csv_param(value: str | None) -> list[str] | None` to `app/api/filters.py` — if value is None or empty, return None; otherwise split by comma, strip whitespace, filter empties, return list or None if result is empty.
- [x] 3.2 Replace inline parsing in `app/api/items.py` (line ~268) — change `category_list = [c.strip() for c in category_filter.split(",") if c.strip()] if category_filter else None` to `category_list = parse_csv_param(category_filter)`. Do same for any `format_list`, `genre_list`, `status_list` etc. in the same file.
- [x] 3.3 Replace inline parsing in `app/api/manifestations.py` (line ~46) — same pattern replacement as 3.2.
- [x] 3.4 Replace inline parsing in `app/api/system.py` (line ~142) — same pattern replacement as 3.2.
- [x] 3.5 Add import `from app.api.filters import parse_csv_param` to each modified file.

## 4. Frontend UX Polish

- [x] 4.1 Update filter chip row in `frontend/components/collection/filter-bar.tsx` (line ~136) — replace `overflow-x-auto whitespace-nowrap pb-1 custom-scrollbar` with `overflow-x-auto whitespace-nowrap pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden`.
- [x] 4.2 Restyle mobile filter pill in `frontend/app/collection/page.tsx` (lines ~1001-1015) — change button className from `bg-foreground text-background px-5 py-2.5 shadow-lg` to `bg-black/80 backdrop-blur-md border border-white/10 text-zinc-300 px-5 py-2.5 shadow-2xl hover:bg-black hover:text-white`. Change badge from `bg-primary text-primary-foreground` to `bg-white text-[10px] font-bold text-black`.
- [x] 4.3 Update "View Wishlist Item" icon in `frontend/components/collection/add-to-collection-dropdown.tsx` — add `Eye` to the lucide-react import (line ~19), replace `<BookmarkPlus className="h-4 w-4 shrink-0 text-primary" />` on line ~136 (the "View Wishlist Item" branch) with `<Eye className="h-4 w-4 shrink-0 text-primary" />`. Keep `BookmarkPlus` for the "Add to Wishlist" branch on line ~145.

## 5. Linting, Formatting, and Verification

- [x] 5.1 Run `make format-python` after all Python changes.
- [x] 5.2 Run `make format-js` after all frontend changes.
- [x] 5.3 Run `make lint` and fix any issues.
- [x] 5.4 Run `make test` to verify all existing and new tests pass.
- [x] 5.5 Update `docs/CHANGELOG.md` with the finalization fixes under v0.7.11.

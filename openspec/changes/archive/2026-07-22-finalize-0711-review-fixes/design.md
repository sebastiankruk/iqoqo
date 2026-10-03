---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

Release v0.7.11 underwent a comprehensive multi-persona team review (PM, Dev, QA, SRE, Security×2, UX, Ontologist, TechComm) against PR #159. All reviewers approved the release with specific hardening requests. This change collects the actionable findings into a single finalization pass before the merge to `main`.

The current `app/core/telemetry.py` already implements `sanitize_headers()` and `record_outbound_telemetry()` but is missing URL query-string sanitization and cookie/session header redaction. The frontend filter bar and mobile filter pill work correctly but need UX polish. Query parameter parsing is duplicated across three API modules.

## Goals / Non-Goals

**Goals:**

- Eliminate credential leakage risk from telemetry URL logging (Security Review #1 — High severity)
- Expand header redaction to cover `cookie` and `session` headers (Security Review #2 — Medium severity)
- Add comprehensive pytest coverage for telemetry sanitization (QA Review — Item 3)
- Centralize comma-separated query parameter parsing into a shared utility (QA Review — Item 1)
- Apply glassmorphism to the mobile filter pill to demote it below the primary Add/Scan CTA (UX Review — Item 1)
- Remove visible scrollbar from the filter chip row for a premium aesthetic (UX Review — Item 2)
- Change "View Wishlist Item" icon from `BookmarkPlus` to `Eye` for navigational clarity (UX Review — Item 3)

**Non-Goals:**

- SSRF prevention wrapper for `requests.get` calls (Security Review #2 — deferred to v0.7.12 Custodian Workflows)
- Redis caching layer for faceted stats endpoint (Security Review #1 — deferred to v0.8.0 scaling)
- Allegro User-Agent `/dev` environment leak fix (PM Review — separate OpenSpec change `capture-allegro-user-agent-telemetry` already in progress)
- Alembic migration for `MetadataRefetchLog` (QA Review — already exists: `0c3eaee0322b`)
- YAML validation CI step for `format_mappings.yaml` (SRE Review — deferred to v0.7.12)
- Load testing of nested facet subqueries (QA Review — deferred to pre-v0.8.0 performance audit)

## Decisions

### D1: URL sanitization via `urllib.parse` decomposition

**Decision:** Implement `sanitize_url()` in `app/core/telemetry.py` using `urlparse` → `parse_qsl` → redact → `urlencode` → `urlunparse`.

**Rationale:** This approach parses URLs structurally rather than using regex, which correctly handles edge cases (encoded parameters, multiple `?` characters, empty values). The Security Review #1 provided a reference implementation using exactly this approach.

**Alternatives considered:**

- Regex-based replacement: Fragile, misses URL-encoded parameter names.
- Strip entire query string: Loses legitimate debugging context (e.g., `?page=1&limit=20`).

### D2: Set-based sensitive keyword matching for headers

**Decision:** Replace the chained `or` conditions in `sanitize_headers()` with a `set` of sensitive keywords and use `any()` comprehension. Add `cookie` and `session` to the set.

**Rationale:** The set-based approach is both more readable and easier to extend. Adding `cookie` and `session` prevents session hijacking via telemetry datastore compromise (Security Review #2).

### D3: Shared `parse_csv_param` utility in `filters.py`

**Decision:** Add a `parse_csv_param(value: str | None) -> list[str] | None` function to `app/api/filters.py` and replace the three inline list comprehensions in `items.py`, `manifestations.py`, and `system.py`.

**Rationale:** QA correctly identified this as a schema validation gap. While a full Marshmallow/Pydantic migration is out of scope for this finalization pass, centralizing the parsing logic ensures consistent validation (strip, empty-check) and provides a single point to add length limits or character validation later.

### D4: CSS-only scrollbar removal (no gradient mask)

**Decision:** Use `[scrollbar-width:none]` (Firefox) + `[&::-webkit-scrollbar]:hidden` (Chrome/Safari) on the filter chip row. Skip the gradient mask suggested by UX for now.

**Rationale:** The gradient mask requires a `mask-image` CSS property that interacts poorly with Tailwind's dark mode system. The scrollbar removal alone achieves the "premium" feel requested. Gradient mask can be added in a future UX polish pass.

### D5: `Eye` icon from lucide-react for "View Wishlist Item"

**Decision:** Import `Eye` from `lucide-react` and use it for the "View Wishlist Item" button, keeping `BookmarkPlus` for "Add to Wishlist".

**Rationale:** UX Review correctly identified that using the same icon for both "View" (navigation) and "Add" (mutation) actions creates cognitive friction. `Eye` universally signals "view/inspect".

## Risks / Trade-offs

- **Overly aggressive URL redaction** → Parameters like `api_version` or `token_type` (which aren't secrets) may get false-positive redacted. Mitigation: The keyword list (`key`, `token`, `secret`, `auth`, `signature`, `credential`) is conservative and targets actual secret patterns. `api_version` won't match.
- **Filter bar horizontal scroll discoverability** → Removing the scrollbar on desktop may confuse users who don't know to use trackpad gestures. Mitigation: Filter chips are dismissible with X buttons and a "Clear all" action exists, reducing the need to scroll.
- **parse_csv_param does not enforce enum validation** → The centralized parser strips and splits but doesn't validate against allowed enum values. Mitigation: The existing backend filter functions (`apply_category_filter`, etc.) already reject unknown values silently by producing no SQL matches.

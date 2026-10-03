## Context

PR #254 (`release/0.7.15` → `main`) implements dashboard scoping, scanner UX improvements, a new feedback mechanism, and dependency bumps. Seven specialist reviews (Devel, Ontologist, QA, SRE, Security, TechComm, UX) identified 8 blocking issues that must be patched before merge. All fixes are surgical — no architectural changes, no new tables, no new dependencies.

The existing `app/api/feedback.py` endpoint already has rate limiting on `POST` but lacks it on `GET`/`PATCH`. The scanner overlay in `bottom-sheet.tsx` has no cancel affordance. Nginx proxy configuration has a 1MB default body size while Flask accepts 10MB uploads. Test suite uses CSS class selectors instead of stable test IDs.

## Goals / Non-Goals

**Goals:**

- Close all 8 blocking security, UX, and test-robustness issues identified in v0.7.15 reviews.
- Keep changes minimal and surgical to avoid re-review scope.
- Maintain existing API contracts — no breaking changes.

**Non-Goals:**

- Normalizing `FeedbackComment` into a separate table (deferred to v0.7.16).
- Moving `feedback_items` to `social` schema (deferred to v0.7.16).
- Resolving ephemeral storage for screenshots (deferred to v0.7.16).
- Dashboard button density UX redesign (deferred to v0.7.16).
- Ownership facet query performance optimization (deferred to v0.8.0).

## Decisions

### 1. Feedback API Rate Limiting Strategy
**Decision:** Add `@limiter.limit("60 per minute")` to `GET /api/feedback` and `GET /api/feedback/<id>`, and `@limiter.limit("30 per minute")` to `PATCH /api/feedback/<id>`.
**Rationale:** These limits match the existing pattern used on other read-heavy endpoints in `app/api/works.py` and `app/api/items.py`. The `POST` endpoint already has `5 per hour` — the GET/PATCH limits are deliberately more permissive since they're used for polling the ticket list and updating status, but tight enough to prevent automated scraping.
**Alternative:** Per-IP sliding window — rejected as overkill for an authenticated-only endpoint.

### 2. Pagination Parameter Clamping
**Decision:** Use `page = max(1, ...)` and `per_page = max(1, min(..., 100))` inline instead of a Pydantic schema.
**Rationale:** The QA review flagged that PATCH lacks schema validation, but recommended deferring full Pydantic migration to v0.7.16. Inline clamping is the minimal fix to prevent negative OFFSET/LIMIT SQL errors now.

### 3. Upload File Count Cap
**Decision:** Hard limit of 5 screenshots per feedback ticket, enforced before the processing loop.
**Rationale:** Prevents storage DoS. 5 is generous enough for bug reports (typically 1-3 screenshots) without enabling abuse. The limit is validated server-side before any disk I/O occurs.

### 4. Closed Ticket Comment Guard
**Decision:** Return HTTP 400 if `item.status == "closed"` and a non-empty comment is provided.
**Rationale:** Prevents infinite JSONB array growth on archived tickets. Admins who need to reopen can first change status, then comment.

### 5. Scanner Escape Hatch Button
**Decision:** Add a text-style "Skip and enter manually" link inside the existing z-30 overlay, calling the existing `onShowManualForm(lastSearchedBarcode)` callback.
**Rationale:** The UX Review specifically flagged the "trapped user" scenario during 10-15 second API lookups. A low-contrast text link avoids competing with the primary loading state while providing an escape route. The existing manual form handler already accepts a pre-filled barcode.

### 6. Nginx Body Size Alignment
**Decision:** Set `client_max_body_size 50M` at the server block level in `deploy/nginx.conf`.
**Rationale:** Backend validates individual files at 10MB × 5 max = 50MB theoretical max payload. Setting 50M at Nginx ensures legitimate requests always reach Flask while still preventing unbounded uploads.

### 7. Test ID Migration for Stats Cards
**Decision:** Add `data-testid="stats-scroll-container"` to the flex-nowrap div in `stats-cards.tsx`; update tests to use `screen.getByTestId()`.
**Rationale:** CSS class selectors in tests are fragile and anti-pattern per QA review. `data-testid` attributes are stable across Tailwind version upgrades and class refactors.

### 8. OpenSpec Purpose Text Cleanup
**Decision:** Write descriptive Purpose statements for `scanner-error-fallback` and `scanner-visual-waiting` spec files.
**Rationale:** TechComm review flagged "TBD" placeholder text that was auto-generated during change archiving. These specs are referenced by other teams and need clear purpose documentation.

## Risks / Trade-offs

- **[Low] JSONB race condition persists** — The comment read-modify-write pattern in `update_feedback()` still has a theoretical race condition under concurrent admin edits. → Mitigation: Deferred to v0.7.16 where full `FeedbackComment` normalization is planned. Current volume is too low to trigger in practice.
- **[Low] Nginx config divergence** — Production may have custom Nginx configs that don't use `deploy/nginx.conf`. → Mitigation: Document the required `client_max_body_size` change in CHANGELOG.md deployment notes.
- **[Low] i18n gap in scanner strings** — The new "Skip and enter manually" text is hardcoded in English. → Mitigation: Deferred to v0.7.16 i18n cleanup batch.

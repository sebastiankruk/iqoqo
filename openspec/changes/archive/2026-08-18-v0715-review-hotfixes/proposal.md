## Why

PR #254 (release/0.7.15) was reviewed by seven specialist personas (Devel, Ontologist, QA, SRE, Security, TechComm, UX). Eight blocking issues were identified that must be resolved before merging to `main`. These span feedback API security hardening, scanner UX escape hatches, infrastructure payload mismatches, test anti-patterns, and documentation gaps. Fixing them now prevents shipping known DoS vectors, UX traps, and CI fragility into production.

## What Changes

- **Feedback API hardening:** Add missing rate limiters to `GET` and `PATCH` feedback endpoints; clamp pagination parameters to prevent negative `OFFSET`/`LIMIT` SQL errors; cap uploaded screenshot count to 5; block comment appends on closed tickets.
- **Scanner UX escape hatch:** Add a "Skip and enter manually" cancel button inside the loading overlay so users are not trapped during 10-15 second API lookups.
- **Nginx payload alignment:** Set `client_max_body_size 50M` in `deploy/nginx.conf` to match the backend's 10MB per-file upload limit.
- **Test robustness:** Replace raw CSS class selectors in `stats-cards.test.tsx` with `data-testid`-based queries to survive Tailwind refactors.
- **OpenSpec placeholder cleanup:** Replace "TBD" Purpose sections in scanner spec files with descriptive statements.
- **Feedback attachment UX:** Change `aspect-video` + `object-cover` to fixed-height `object-contain` for feedback screenshot thumbnails to prevent cropping vertical mobile screenshots.

## Capabilities

### New Capabilities

None — all changes modify existing capabilities.

### Modified Capabilities

- `feedback-mechanism`: Add rate limiting to GET/PATCH endpoints, cap file upload count, clamp pagination, block comments on closed tickets.
- `scanner-visual-waiting`: Add user-accessible cancel/skip button inside the loading overlay.
- `scanner-error-fallback`: Update OpenSpec purpose text from placeholder to descriptive statement.
- `dashboard-scope-toggles`: Add `data-testid` attribute to scrolling container for robust test targeting.

## Impact

- **Backend:** `app/api/feedback.py` — rate limiter decorators, upload cap, pagination clamping, closed-ticket guard.
- **Frontend:** `frontend/components/scanner/bottom-sheet.tsx` — cancel button in overlay. `frontend/components/dashboard/stats-cards.tsx` — `data-testid` attribute. `frontend/components/feedback/feedback-detail-modal.tsx` — attachment thumbnail styling.
- **Tests:** `frontend/__tests__/components/dashboard/stats-cards.test.tsx` — switch from CSS selector to `getByTestId`.
- **Infrastructure:** `deploy/nginx.conf` — `client_max_body_size` directive.
- **Docs:** `openspec/specs/scanner-error-fallback/spec.md`, `openspec/specs/scanner-visual-waiting/spec.md` — purpose sections.

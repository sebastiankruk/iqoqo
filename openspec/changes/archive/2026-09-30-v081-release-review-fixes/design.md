## Context
Addressing critical issues flagged during v0.8.1 release code review. These are targeted bugfixes and security cleanups before merging the release branch.

## Goals / Non-Goals

**Goals:**
- Fix security issues (XSS in profile).
- Prevent data loss in migrations.
- Remove technical debt (negative ID hack, dead code).
- Implement efficient SQL pagination in wishlist API.

**Non-Goals:**
- New features or large-scale refactoring outside of these specific CRITICAL findings.

## Decisions

- **CRIT-1: Account Deletion** - Return 501 from `app/api/profile.py` delete endpoint. Disable UI button with tooltip.
- **CRIT-2: XSS Mitigation** - Apply `bleach.clean(value, tags=[], attributes={}, protocols=[], strip=True)` to `bio` and `display_name` in `update_profile()`.
- **CRIT-3: Negative-ID Hack** - Remove all negative ID logic from `app/api/items.py`. Redirect frontend negative ID usage to the wishlist API.
- **CRIT-4: SQL Pagination** - Update `app/api/wishlist.py` to use SQL `LIMIT` and `OFFSET` instead of `.all()` and in-memory slicing. Push filtering to SQL JOINs.
- **CRIT-5: Roadmap Migration** - Assign a sentinel `work_id` (first Work in DB) to orphan roadmap items in `migrations/versions/v0_8_1_frbr_relation_management.py`.
- **CRIT-6: SQLite Security Migration** - In `migrations/versions/v0_8_1_security_constraints.py`, check if the user has items in SQLite path, disabling instead of deleting.
- **CRIT-8: Dead Code** - Delete `frontend/components/admin/frbr/contributor-editor.tsx` and its test file.

## Risks / Trade-offs

- [Risk] Unintended side effects from negative ID removal -> Mitigation: Ensure frontend usage of wishlist API is fully tested and verified.
- [Risk] Sentinel work assignment creates bad data -> Mitigation: This is a fallback to avoid data loss; orphan items are already anomalous.
